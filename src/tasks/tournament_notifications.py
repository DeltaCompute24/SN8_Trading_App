import logging
from datetime import timedelta

from celery import shared_task

from src.database_tasks import TaskSessionLocal_
from src.models import Tournament, Challenge
from src.services.email_service import send_mail
from src.services.user_service import convert_time_to_est
from src.utils.redis_manager import push_to_redis_queue

logger = logging.getLogger(__name__)


@shared_task(name="src.tasks.tournament_notifications.send_discord_reminder")
def send_discord_reminder():
    """Send an email on registration to join discord"""
    db = TaskSessionLocal_()
    try:
        now = convert_time_to_est()  # 6
        six_hours_ago_start = now - timedelta(hours=6)  # 12

        # Fetch challenges created exactly 6 hours ago and status is "Tournament"
        challenges = db.query(Challenge).filter(
            Challenge.created_at >= six_hours_ago_start,
            Challenge.created_at < now,
            Challenge.status == "Tournament",
            Challenge.active == "1",
        ).all()

        for challenge in challenges:
            user = challenge.user

            subject = "Reminder: Join Our Discord!"
            context = {
                "name": user.name,
            }
            send_mail(
                receiver=user.email,
                subject=subject,
                template_name='RegistrationReminder.html',
                context=context,
            )
            logger.info(f"Sent registration reminder to {user.name} ({user.email})")

    except Exception as e:
        logger.error(f"Error in send_discord_reminder task: {e}")
        push_to_redis_queue(data=f"Registration Reminder Error - {e}", queue_name="error_queue")
    finally:
        db.close()


@shared_task(name="src.tasks.tournament_notifications.send_tournament_start_email")
def send_tournament_start_email():
    """Send an email when the tournament officially starts."""
    db = TaskSessionLocal_()
    try:
        now = convert_time_to_est()
        one_minute_later = now + timedelta(minutes=1)
        one_day_later = now + timedelta(days=1)
        logger.info(f"Checking for tournaments that start between {now} and {one_minute_later}")

        # Fetch tournaments that are starting within the next 1 minute
        tournaments = db.query(Tournament).filter(
            Tournament.end_time > now  # Ensures the tournament is still ongoing
        ).all()

        for tournament in tournaments:
            for challenge in tournament.challenges:
                user = challenge.user
                start = ""

                if tournament.start_time == one_minute_later:
                    # Send email using the tournament start email template
                    start = "Before 1 minute"
                    subject = "The Tournament Has Started!"
                    template_name = 'TournamentStartEmail.html'
                    context = {
                        "name": user.name,
                        "tournament_name": tournament.name
                    }
                elif tournament.start_time == one_day_later:
                    start = "Before 1 day"
                    subject = "Tournament Starts in 24 Hours!"
                    context = {
                        "name": user.name,
                        "tournament_name": tournament.name
                    }
                    template_name = 'TournamentStartReminder.html'
                if start:
                    send_mail(
                        receiver=user.email,
                        subject=subject,
                        template_name=template_name,
                        context=context
                    )
                    logger.info(f"Sent tournament start email to {user.email} for tournament {tournament.name} {start}")

    except Exception as e:
        logger.error(f"Error in tournament reminder email task: {e}")
        push_to_redis_queue(data=f"Tournament Reminder Email Error - {e}", queue_name="error_queue")
    finally:
        db.close()
