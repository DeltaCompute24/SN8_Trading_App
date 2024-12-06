import logging
from datetime import timedelta, datetime

from celery import shared_task
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models import Tournament, Challenge
from src.services.email_service import send_mail
from src.utils.redis_manager import push_to_redis_queue

logger = logging.getLogger(__name__)


# Helper function to get tournament registrants (challenges) for sending reminders
def get_tournament_registrants(tournament_id: int, db: Session):
    try:
        logger.info(f"Fetching registrants for tournament {tournament_id}")
        challenges = db.query(Challenge).filter(Challenge.tournament_id == tournament_id).all()
        logger.info(f"Found {len(challenges)} registrants for tournament {tournament_id}")
        return challenges
    except Exception as e:
        logger.error(f"Error fetching tournament registrants: {e}")
        push_to_redis_queue(data=f"Tournament Notification Error - {e}", queue_name="error_queue")
        return []


@shared_task(name="src.tasks.tournament_notifications.send_registration_reminder")
def send_registration_reminder():
    """Send reminder email to registrants 1 day after registration."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        one_day_ago = now - timedelta(days=1)

        # Fetch tournament registrants who registered 24 hours ago and haven't been emailed yet
        challenges = db.query(Challenge).filter(
            Challenge.created_at <= one_day_ago,
            # Challenge.reminder_email_sent == False,
            Challenge.status == "Tournament"
        ).all()

        for challenge in challenges:
            user = challenge.user

            # Send email
            subject = "Reminder: Join Our Tournament Discord"
            context = {
                "header": "Don't Miss Out!",
                "body": f"Hi {user.name},\n\nDon't forget to join our Discord channel for the latest updates and discussions about the tournament!",
                "footer": "We can't wait to see you there!"
            }

            send_mail(user.email, subject=subject, context=context)
            logger.info(f"Sent registration reminder to {user.name} ({user.email})")

            # Update the reminder_email_sent flag
            # challenge.reminder_email_sent = True
            db.add(challenge)

        db.commit()

    except Exception as e:
        logger.error(f"Error in send_registration_reminder task: {e}")
        push_to_redis_queue(data=f"Registration Reminder Error - {e}", queue_name="error_queue")
    finally:
        db.close()


@shared_task(name="src.tasks.tournament_notifications.send_tournament_start_email")
def send_tournament_start_email():
    """Send an email when the tournament officially starts."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        # Fetch tournaments that have just started
        tournaments = db.query(Tournament).filter(
            Tournament.start_time <= now,
            Tournament.end_time >= now
        ).all()

        for tournament in tournaments:
            challenges = get_tournament_registrants(tournament.id, db)
            for challenge in challenges:
                user = challenge.user

                subject = "Tournament is Live!"
                context = {
                    "header": "The Tournament is Live!",
                    "body": f"Hi {user.name},\n\nThe {tournament.name} tournament has officially started. Head over to the platform and make your move!",
                    "footer": "Good luck and have fun!"
                }

                send_mail(user.email, subject=subject, context=context)

                logger.info(f"Sent tournament start email to {user.name} ({user.email}) for tournament {tournament.name}")

    except Exception as e:
        logger.error(f"Error in send_tournament_start_email task: {e}")
        push_to_redis_queue(data=f"Tournament Start Email Error - {e}", queue_name="error_queue")
    finally:
        db.close()


@shared_task(name="src.tasks.tournament_notifications.send_tournament_start_reminder")
def send_tournament_start_reminder():
    """Send an email reminder 24 hours prior to tournament start."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        tournament_start_time = now + timedelta(days=1)

        # Fetch tournaments starting in 1 day
        tournaments = db.query(Tournament).filter(
            Tournament.start_time == tournament_start_time
        ).all()

        for tournament in tournaments:
            challenges = get_tournament_registrants(tournament.id, db)
            for challenge in challenges:
                user = challenge.user

                subject = "Tournament Starts in 1 Day!"
                context = {
                    "header": "Get Ready for the Action!",
                    "body": f"Hi {user.name},\n\nThe {tournament.name} tournament starts in just 1 day. Make sure you're ready to participate!",
                    "footer": "See you in the tournament!"
                }

                send_mail(user.email, subject=subject, context=context)

                logger.info(f"Sent tournament start reminder to {user.name} ({user.email}) for tournament {tournament.name}")

    except Exception as e:
        logger.error(f"Error in send_tournament_start_reminder task: {e}")
        push_to_redis_queue(data=f"Tournament Start Reminder Error - {e}", queue_name="error_queue")
    finally:
        db.close()
