import logging
from datetime import timedelta, datetime
import requests
from src.config import SWITCH_TO_MAINNET_URL
from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models import Tournament, Challenge
from src.services.api_service import testnet_websocket
from src.services.email_service import send_mail, send_support_email
from src.tasks.monitor_mainnet_challenges import get_monitored_challenges, update_challenge
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import push_to_redis_queue
import pytz

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


@celery_app.task(name="src.tasks.tournament_notifications.send_tournament_results")
def send_tournament_results():
    test_net_data = testnet_websocket(monitor=True)

    if not test_net_data:
        push_to_redis_queue(
            data=f"**Testnet Listener** => Testnet Validator Checkpoint returns with status code other than 200",
            queue_name=ERROR_QUEUE_NAME
        )
        return

    positions = test_net_data["positions"]
    perf_ledgers = test_net_data["perf_ledgers"]
    db = TaskSessionLocal_()
    try:
        for challenge in get_monitored_challenges(db, status="Tournament"):
            logger.info(f"Monitor first testnet Challenge!")
            hot_key = challenge.hot_key
            name = challenge.user.name
            email = challenge.user.email

            p_content = positions.get(hot_key)
            l_content = perf_ledgers.get(hot_key)
            if not p_content or not l_content:
                continue

            profit_sum = 0
            for position in p_content["positions"]:
                profit_loss = (position["return_at_close"] * 100) - 100
                if position["is_closed_position"] is True:
                    profit_sum += profit_loss

            draw_down = (l_content["cps"][-1]["mdd"] * 100) - 100
            c_data = {
                "draw_down": draw_down,
                "profit_sum": profit_sum,
            }
            changed = False
            context = {
                "name": name,
                "trader_id": challenge.trader_id,
            }

            if profit_sum >= 2:  # 2%
                changed = True
                network = "main"
                payload = {
                    "name": challenge.challenge_name,
                    "trader_id": challenge.trader_id,
                }
                subject = "Congratulations on Completing Phase 1!"
                template_name = "ChallengePassedPhase1Step2.html"

                c_data = {
                    **c_data,
                    "status": "Passed",
                    "pass_the_challenge": datetime.utcnow(),
                    "phase": 2,
                }

                if email != "dev@delta-mining.com":
                    _response = requests.post(SWITCH_TO_MAINNET_URL, json=payload)
                    data = _response.json()
                    if _response.status_code == 200:
                        c_response = challenge.response or {}
                        c_response["main_net_response"] = data
                        c_data = {
                            **c_data,
                            "challenge": network,
                            "status": "In Challenge",
                            "active": "1",
                            "trader_id": data.get("trader_id"),
                            "response": c_response,
                            "register_on_main_net": datetime.utcnow(),
                        }
                        context["trader_id"] = data.get("trader_id")
                    else:
                        send_support_email(
                            subject=f"Switch from testnet to mainnet API call failed with status code: {_response.status_code}",
                            content=f"User {email} passed step {challenge.step} and phase {challenge.phase} "
                                    f"but switch_to_mainnet Failed. Response from switch_to_mainnet api => {data}",
                        )
                else:
                    c_data = {
                        **c_data,
                        "challenge": network,
                        "status": "In Challenge",
                        "active": "1",
                        "register_on_main_net": datetime.utcnow(),
                    }
            elif draw_down <= -5:  # 5%
                changed = True
                c_data = {
                    **c_data,
                    "status": "Failed",
                    "active": "0",
                }
                subject = "Phase 1 Challenge Failed"
                template_name = "ChallengeFailedPhase1.html"

            if changed:
                update_challenge(db, challenge, c_data)
                send_mail(email, subject=subject, template_name=template_name, context=context)

        logger.info("Finished monitor_challenges task")
    except Exception as e:
        logger.error(f"Error in tournament reminder email task: {e}")
        push_to_redis_queue(data=f"Tournament Reminder Email Error - {e}", queue_name="error_queue")
    finally:
        db.close()
