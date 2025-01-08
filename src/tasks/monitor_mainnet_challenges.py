import logging
from datetime import datetime

from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.config import NEW_POSITIONS_URL, NEW_POSITIONS_TOKEN
from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.challenge import Challenge
from src.services.api_service import call_main_net
from src.services.email_service import send_mail
from src.services.s3_services import send_certificate_email
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import push_to_redis_queue

logger = logging.getLogger(__name__)


def get_monitored_challenges(db: Session, challenge="test", status="In Challenge"):
    try:
        logger.info("Fetching monitored challenges from database")
        result = db.execute(
            select(Challenge).where(
                and_(
                    Challenge.status == status,
                    Challenge.active == "1",
                    Challenge.challenge == challenge,
                )
            )
        )
        challenges = result.scalars().all()
        logger.info(f"Retrieved {len(challenges)} monitored challenges")
        return challenges
    except Exception as e:
        push_to_redis_queue(data=f"**Monitor {challenge.title()}net Challenges** Database Error - {e}",
                            queue_name=ERROR_QUEUE_NAME)
        logger.error(f"An error occurred while fetching {challenge}net monitored challenges: {e}")
        return []


def update_challenge(db: Session, challenge, data):
    logger.info(f"Updating monitored challenge: {challenge.trader_id} - {challenge.hot_key}")

    for key, value in data.items():
        setattr(challenge, key, value)

    db.commit()
    db.refresh(challenge)


@celery_app.task(name='src.tasks.monitor_mainnet_challenges.monitor_mainnet_challenges')
def monitor_mainnet_challenges():
    logger.info("Starting monitor mainnet challenges task")
    try:
        response = call_main_net(url=NEW_POSITIONS_URL, token=NEW_POSITIONS_TOKEN)
        if not response:
            return
        success = response["challengeperiod"]["success"]
        eliminations = {}
        for elimination in response["eliminations"]:
            eliminations[elimination["hotkey"]] = elimination

        with TaskSessionLocal_() as db:
            for challenge in get_monitored_challenges(db, challenge="main"):
                hot_key = challenge.hot_key
                elimination = eliminations.get(hot_key)
                name = challenge.user.name
                email = challenge.user.email
                changed = False

                if success.get(hot_key):
                    changed = True
                    c_data = {
                        "status": "Passed",
                        "active": "0",
                        "pass_the_main_net_challenge": datetime.utcnow(),
                    }
                    if challenge.phase == 1:
                        template_name = "ChallengePassedPhase1Step1.html"
                        subject = "Congratulations on Completing Phase 1!"
                    else:
                        template_name = "ChallengePassedPhase2.html"
                        subject = "Congratulations on Completing Phase 2!"
                    attachment = send_certificate_email(email, name, challenge, True)
                elif elimination:
                    changed = True
                    c_response = challenge.response or {}
                    c_response["failed_response"] = elimination
                    c_data = {
                        "status": "Failed",
                        "active": "0",
                        "response": c_response,
                        "draw_down": elimination.get("dd"),
                    }
                    if challenge.phase == 1:
                        template_name = "ChallengeFailedPhase1.html"
                        subject = "Phase 1 Challenge Failed"
                    else:
                        template_name = "ChallengeFailedPhase2.html"
                        subject = "Phase 2 Challenge Failed"
                    attachment = None

                if changed:
                    update_challenge(db, challenge, c_data)
                    send_mail(
                        email,
                        subject=subject,
                        template_name=template_name,
                        context={'name': name},
                        attachment=attachment,
                    )

    except Exception as e:
        push_to_redis_queue(data=f"**Monitor Mainnet Challenges** - {e}", queue_name=ERROR_QUEUE_NAME)
        logger.error(f"Error in monitor_mainnet_challenges task mainnet - {e}")
