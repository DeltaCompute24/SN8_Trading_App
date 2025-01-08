import asyncio
import logging
from datetime import datetime
from datetime import timedelta

import pytz
from sqlalchemy.sql import or_, and_

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models import Tournament, Challenge
from src.models.transaction import Transaction
from src.services.api_service import testnet_websocket
from src.services.email_service import send_mail
from src.services.tournament_service import update_tournament_object
from src.services.user_service import bulk_update_challenges
from src.tasks.testnet_validator import get_profit_sum_and_draw_down
from src.utils.constants import ERROR_QUEUE_NAME, TOURNAMENT
from src.utils.redis_manager import push_to_redis_queue, set_hash_value
from src.utils.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


@celery_app.task(name="src.tasks.tournament_notifications.send_discord_reminder")
def send_discord_reminder():
    """Send an email on registration to join discord"""
    db = TaskSessionLocal_()
    try:
        now = datetime.now(pytz.utc).replace(second=0, microsecond=0).replace(tzinfo=None)
        six_hours_ago_start = now - timedelta(hours=6)  # 12

        # Fetch challenges created exactly 6 hours ago and status is "Tournament"
        challenges = db.query(Challenge).filter(
            Challenge.created_at >= six_hours_ago_start,
            Challenge.created_at < now,
            Challenge.status == "Tournament",
            Challenge.active == "1",
        ).all()

        for challenge in challenges:
            if challenge.user:
                subject = "Reminder: Join Our Discord!"
                context = {
                    "name": challenge.user.name,
                    "tournament_name": challenge.tournament.name,
                }
                send_mail(
                    receiver=challenge.user.email,
                    subject=subject,
                    template_name='RegistrationReminder.html',
                    context=context,
                )
                logger.info(f"Sent registration reminder to {challenge.user.name} ({challenge.user.email})")

    except Exception as e:
        logger.error(f"Error in send_discord_reminder task: {e}")
        push_to_redis_queue(data=f"Registration Reminder Error - {e}", queue_name="error_queue")
    finally:
        db.close()


@celery_app.task(name="src.tasks.tournament_notifications.send_tournament_start_email")
def send_tournament_start_email():
    """Send an email when the tournament officially starts."""
    db = TaskSessionLocal_()
    try:
        now = datetime.now(pytz.utc).replace(second=0, microsecond=0).replace(tzinfo=None)
        one_minute_later = now + timedelta(minutes=1)
        one_day_later = now + timedelta(days=1)
        logger.info(f"Checking for tournaments that start between {now} and {one_minute_later}")

        # Fetch tournaments that are starting within the next 1 minute
        tournaments = db.query(Tournament).filter(
            Tournament.end_time > now,  # Ensures the tournament is still ongoing
            Tournament.active == True,
        ).all()

        for tournament in tournaments:
            for challenge in tournament.challenges:
                if challenge.user:
                    if tournament.start_time == one_minute_later:
                        # Start notification
                        subject = "The Tournament Has Started!"
                        template_name = 'TournamentStartEmail.html'
                    elif tournament.start_time == one_day_later:
                        # 24-hour reminder
                        subject = "Tournament Starts in 24 Hours!"
                        template_name = 'TournamentStartReminder.html'
                    else:
                        continue

                    context = {"name": challenge.user.name, "tournament_name": tournament.name}
                    send_mail(
                        receiver=challenge.user.email,
                        subject=subject,
                        template_name=template_name,
                        context=context
                    )
                    logger.info(
                        f"Sent tournament email '{subject}' to {challenge.user.email} for tournament {tournament.name}")

    except Exception as e:
        logger.error(f"Error in tournament reminder email task: {e}")
        push_to_redis_queue(data=f"Tournament Reminder Email Error - {e}", queue_name="error_queue")
    finally:
        db.close()


@celery_app.task(name="src.tasks.tournament_notifications.monitor_tournaments")
def monitor_tournaments():
    db = TaskSessionLocal_()
    try:
        now = datetime.now(pytz.utc).replace(second=0, microsecond=0).replace(tzinfo=None)
        tournaments = db.query(Tournament).filter(
            Tournament.end_time == (now - timedelta(hours=1)),  # get tournaments that ended one hour ago
            Tournament.active == True,
        ).all()

        if not tournaments:
            return

        for tournament in tournaments:
            challenges = tournament.challenges
            for challenge in challenges:
                transactions = db.query(Transaction).filter(
                    and_(
                        Transaction.trader_id == challenge.trader_id,
                        or_(
                            Transaction.status == "OPEN",
                            Transaction.status == "PENDING",
                        )
                    )
                ).all()  # PENDING, OPEN

                for position in transactions:
                    if position.status == "OPEN":  # taoshi
                        asyncio.run(websocket_manager.submit_trade(position.trader_id, position.trade_pair, "FLAT", 1))
                    position.status = "CLOSED"
                    position.close_time = datetime.now(pytz.utc).replace(tzinfo=None)
                    position.old_status = position.status
                    position.operation_type = "tournament_closed"
                    position.modified_by = "system"
            db.commit()
            calculate_tournament_results(db, tournament, challenges)

    except Exception as e:
        logger.error(f"Error in Monitor Tournaments task: {e}")
        push_to_redis_queue(data=f"Monitor Tournaments Email Error - {e}", queue_name="error_queue")
    finally:
        db.close()


def calculate_score(challenge, positions, perf_ledgers):
    data = get_profit_sum_and_draw_down(challenge, positions, perf_ledgers)
    if not data:
        return {}
    profit_sum = data["profit_sum"]
    max_draw_down = data["draw_down"]
    score = profit_sum / max_draw_down
    return {
        "draw_down": max_draw_down,
        "profit_sum": profit_sum,
        "score": score,
    }


def calculate_tournament_results(db, tournament, challenges):
    try:
        test_net_data = testnet_websocket(monitor=True)
        if not test_net_data:
            return

        positions = test_net_data["positions"]
        perf_ledgers = test_net_data["perf_ledgers"]
        logger.info(f"")
        attendees_score = {}
        max_score = float('-inf')
        challenges_data = []
        for challenge in challenges:
            data = calculate_score(challenge, positions, perf_ledgers)
            if not data:
                continue
            data["active"] = "0"
            data["id"] = challenge.id
            challenges_data.append(data)
            # calculate max score
            score = data["score"]
            if score > max_score:
                max_score = score
            # store attendees score
            if score not in attendees_score:
                attendees_score[score] = []
            attendees_score[score].append(challenge.trader_id)

        # bulk update challenge
        bulk_update_challenges(db, challenges_data)

        # tournament update
        update_tournament_object(
            db,
            tournament,
            data={
                "winners": attendees_score[max_score],
                "winning_score": max_score,
            },
        )

        # send emails to attendees
        for challenge in challenges:
            if challenge.score == max_score:  # Winner
                subject = "Congratulations, You're a Winner!"
                template_name = "TournamentWinner.html"
            else:  # Not Winner
                subject = "Thank You for Participating"
                template_name = "TournamentLosser.html"

            send_mail(
                receiver=challenge.user.email,
                subject=subject,
                context={"name": challenge.user.name, "tournament_name": tournament.name},
                template_name=template_name
            )

        logger.info("Finished monitor_challenges task")
    except Exception as e:
        logger.error(f"Error in Calculate Tournament Results Task: {e}")
        push_to_redis_queue(data=f"Calculate Tournament Results Error - {e}", queue_name="error_queue")


@celery_app.task(name="src.tasks.tournament_notifications.calculate_participants_score")
def calculate_participants_score():
    db = TaskSessionLocal_()
    try:
        now = datetime.now(pytz.utc).replace(second=0, microsecond=0).replace(tzinfo=None)
        tournaments = db.query(Tournament).filter(
            and_(
                Tournament.start_time <= now,
                Tournament.end_time >= now,
                Tournament.active == True,
            )
        ).all()

        if not tournaments:
            return
        test_net_data = testnet_websocket(monitor=True)
        if not test_net_data:
            return
        positions = test_net_data["positions"]
        perf_ledgers = test_net_data["perf_ledgers"]
        scores_list = []

        for tournament in tournaments:
            challenges = tournament.challenges
            tournament_list = []
            for challenge in challenges:
                transactions = db.query(Transaction).filter(
                    and_(
                        Transaction.trader_id == challenge.trader_id,
                        Transaction.status != "PENDING",
                    )
                ).count()

                data = calculate_score(challenge, positions, perf_ledgers)
                if not data:
                    continue
                data["position_count"] = transactions
                data["trader_id"] = challenge.trader_id
                data["user_name"] = challenge.user.name
                tournament_list.append(data)
            # Sort the list by 'score' in descending order
            sorted_data = sorted(tournament_list, key=lambda x: x["score"], reverse=True)

            # Add the rank attribute
            for idx, item in enumerate(sorted_data, start=1):
                item["rank"] = idx
            scores_list.append({
                "tournament": tournament.name,
                "data": sorted_data,
            })
        set_hash_value(key="0", value=scores_list, hash_name=TOURNAMENT)

    except Exception as e:
        logger.error(f"Error in Calculate Participants Score task: {e}")
        push_to_redis_queue(data=f" Calculate Participants Score Error - {e}", queue_name="error_queue")
    finally:
        db.close()
