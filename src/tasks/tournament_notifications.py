import asyncio
import logging
from datetime import datetime
from datetime import timedelta

import pytz
from sqlalchemy.sql import and_

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models import Tournament, Challenge
from src.models.transaction import Transaction
from src.services.api_service import testnet_websocket
from src.services.email_service import send_mail
from src.services.tournament_service import update_tournament_object
from src.services.user_service import bulk_update_challenges
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import push_to_redis_queue
from src.utils.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


@celery_app.task(name="src.tasks.tournament_notifications.send_discord_reminder")
def send_discord_reminder():
    """Send an email on registration to join discord"""
    db = TaskSessionLocal_()
    try:
        now = datetime.now(pytz.utc).replace(second=0, microsecond=0)
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
                context = {"name": challenge.user.name}
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
        now = datetime.now(pytz.utc).replace(second=0, microsecond=0)
        one_minute_later = now + timedelta(minutes=1)
        one_day_later = now + timedelta(days=1)
        logger.info(f"Checking for tournaments that start between {now} and {one_minute_later}")

        # Fetch tournaments that are starting within the next 1 minute
        tournaments = db.query(Tournament).filter(
            Tournament.end_time > now  # Ensures the tournament is still ongoing
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
        now = datetime.now(pytz.utc).replace(second=0, microsecond=0)
        tournaments = db.query(Tournament).filter(
            Tournament.end_time == (now - timedelta(hours=1))  # Ensures the tournament is still ongoing
        ).all()

        if not tournaments:
            return

        for tournament in tournaments:
            challenges = tournament.challenges
            for challenge in challenges:
                transactions = db.query(Transaction).filter(
                    and_(
                        Transaction.trader_id == challenge.trader_id,
                        Transaction.status != "CLOSED",
                    )
                ).all()  # PENDING, OPEN

                for position in transactions:
                    if position.status == "OPEN":  # taoshi
                        asyncio.run(websocket_manager.submit_trade(position.trader_id, position.trade_pair, "FLAT", 1))
                    position.status = "CLOSED"
                    position.close_time = datetime.now(pytz.utc)
                    position.old_status = position.status
                    position.operation_type = "tournament_closed"
                    position.modified_by = "system"
            calculate_tournament_results(tournament, challenges)
        db.commit()

    except Exception as e:
        logger.error(f"Error in tournament reminder email task: {e}")
        push_to_redis_queue(data=f"Tournament Reminder Email Error - {e}", queue_name="error_queue")
    finally:
        db.close()


def calculate_tournament_results(tournament, challenges):
    db = TaskSessionLocal_()
    try:
        test_net_data = testnet_websocket(monitor=True)
        if not test_net_data:
            push_to_redis_queue(
                data=f"**Testnet Listener** => Testnet Validator Checkpoint returns with status code other than 200",
                queue_name=ERROR_QUEUE_NAME
            )
            return

        positions = test_net_data["positions"]
        perf_ledgers = test_net_data["perf_ledgers"]
        logger.info(f"")
        attendees_score = {}
        max_score = float('-inf')
        challenges_data = []
        for challenge in challenges:
            hot_key = challenge.hot_key
            p_content = positions.get(hot_key)
            l_content = perf_ledgers.get(hot_key)
            if not p_content or not l_content:
                continue

            profit_sum = 0
            for position in p_content["positions"]:
                profit_loss = (position["return_at_close"] * 100) - 100
                if position["is_closed_position"] is True:
                    profit_sum += profit_loss

            max_draw_down = (l_content["cps"][-1]["mdd"] * 100) - 100
            score = profit_sum / (max_draw_down if max_draw_down != 0 else 1)
            challenges_data.append({
                "draw_down": max_draw_down,
                "profit_sum": profit_sum,
                "active": "0",
                "score": score,
            })
            # calculate max score
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
            if challenge.score == max_score:  # winner
                subject = ""
                context = {}
                template_name = ""
            else: # not winner
                subject = ""
                context = {}
                template_name = ""
            send_mail(
                challenge.user.email,
                subject=subject,
                context=context,
                template_name=template_name
            )

        logger.info("Finished monitor_challenges task")
    except Exception as e:
        logger.error(f"Error in tournament reminder email task: {e}")
        push_to_redis_queue(data=f"Tournament Reminder Email Error - {e}", queue_name="error_queue")
    finally:
        db.close()
