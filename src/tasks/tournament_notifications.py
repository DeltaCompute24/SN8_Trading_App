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
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        six_hours_ago_start = now - timedelta(hours=6)
        six_hours_ago_end = now - timedelta(hours=5, seconds=59)

        # Fetch challenges created exactly 6 hours ago and status is "Tournament"
        challenges = db.query(Challenge).filter(
            Challenge.created_at >= six_hours_ago_start,
            Challenge.created_at <= six_hours_ago_end,
            Challenge.status == "Tournament"
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
                context=context
            )
            logger.info(f"Sent registration reminder to {user.name} ({user.email})")

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
        one_minute_later = now + timedelta(minutes=1)
        logger.info(f"Checking for tournaments that start between {now} and {one_minute_later}")

        # Fetch tournaments that are starting within the next 1 minute
        tournaments = db.query(Tournament).filter(
            Tournament.start_time >= now,
            Tournament.start_time < one_minute_later,
            Tournament.end_time > now  # Ensures the tournament is still ongoing
        ).all()

        for tournament in tournaments:
            challenges = get_tournament_registrants(tournament.id, db)
            for challenge in challenges:
                user = challenge.user

                # Send email using the tournament start email template
                subject = "The Tournament Has Started!"
                context = {
                    "name": user.name,
                    "tournament_name": tournament.name
                }

                send_mail(
                    receiver=user.email,
                    subject=subject,
                    template_name='TournamentStartEmail.html',
                    context=context
                )

                logger.info(
                    f"Sent tournament start email to {user.name} ({user.email}) for tournament {tournament.name}")

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
        reminder_time_start = now + timedelta(days=1)
        reminder_time_end = reminder_time_start + timedelta(minutes=1)  # Covers up to 24 hours + 59 seconds

        logger.info(
            f"Checking for tournaments starting between {reminder_time_start} and {reminder_time_end} for reminders")

        # Fetch tournaments starting exactly 24 hours from now (within the range)
        tournaments = db.query(Tournament).filter(
            Tournament.start_time >= reminder_time_start,
            Tournament.start_time < reminder_time_end
        ).all()

        for tournament in tournaments:
            challenges = get_tournament_registrants(tournament.id, db)
            for challenge in challenges:
                user = challenge.user

                # Send email using the tournament start reminder template
                subject = "Tournament Starts in 24 Hours!"
                context = {
                    "name": user.name,
                    "tournament_name": tournament.name
                }

                send_mail(
                    receiver=user.email,
                    subject=subject,
                    template_name='TournamentStartReminder.html',
                    context=context
                )

                logger.info(
                    f"Sent tournament start reminder to {user.name} ({user.email}) for tournament {tournament.name}")

    except Exception as e:
        logger.error(f"Error in send_tournament_start_reminder task: {e}")
        push_to_redis_queue(data=f"Tournament Start Reminder Error - {e}", queue_name="error_queue")
    finally:
        db.close()
