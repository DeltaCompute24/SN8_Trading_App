import logging
from datetime import datetime
from tempfile import template

import requests
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.config import CHECKPOINT_URL, STATISTICS_URL, STATISTICS_TOKEN
from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.challenge import Challenge
from src.services.api_service import call_main_net
from src.services.email_service import send_mail
from src.services.s3_services import send_certificate_email
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import push_to_redis_queue

logger = logging.getLogger(__name__)


def get_monitored_challenges(db: Session, challenge="test"):
    try:
        logger.info("Fetching monitored challenges from database")
        result = db.execute(
            select(Challenge).where(
                and_(
                    Challenge.status == "In Challenge",
                    Challenge.active == "1",
                    Challenge.challenge == challenge,
                )
            )
        )
        challenges = result.scalars().all()
        logger.info(f"Retrieved {len(challenges)} monitored challenges")
        return challenges
    except Exception as e:
        push_to_redis_queue(data=f"**Monitor Challenges** Database Error - {e}", queue_name=ERROR_QUEUE_NAME)
        logger.error(f"An error occurred while fetching monitored challenges: {e}")
        return []


def update_challenge(db: Session, challenge, data):
    logger.info(f"Updating monitored challenge: {challenge.trader_id} - {challenge.hot_key}")

    for key, value in data.items():
        setattr(challenge, key, value)

    db.commit()
    db.refresh(challenge)


def monitor_testnet():
    try:
        response = requests.get(CHECKPOINT_URL)
        if response.status_code != 200:
            return

        data = response.json()

        if not data:
            return

        positions = data["positions"]
        perf_ledgers = data["perf_ledgers"]

        with TaskSessionLocal_() as db:
            for challenge in get_monitored_challenges(db):
                logger.info(f"Monitor first Challenge!")
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
                context = {'name': name}

                if profit_sum >= 2:  # 2%
                    changed = True
                    network = "main" if challenge.challenge == "test" else "test"
                    payload = {
                        "name": challenge.challenge_name,
                        "trader_id": challenge.trader_id,
                    }
                    # _response = requests.post(SWITCH_TO_MAINNET_URL, json=payload)

                    c_data = {
                        **c_data,
                        "status": "Passed",
                        "pass_the_challenge": datetime.utcnow(),
                        "phase": 2,
                    }

                    # if _response.status_code == 200:
                    #     c_response = challenge.response
                    #     c_response["main_net_response"] = _response.json()
                    #     c_data = {
                    #         **c_data,
                    #         "challenge": network,
                    #         "status": "In Challenge",
                    #         "active": "1",
                    #         "trader_id": data.get("trader_id"),
                    #         "response": c_response,
                    #         "register_on_main_net": datetime.utcnow(),
                    #     }
                    #     content = f"{content} Your testnet key is also converted to hot_key!"
                    #     send_certificate_email(email, name, challenge)

                    subject = "Congratulations on Completing Phase 1!"
                    template_name = "ChallengePassedPhase1Step2.html"
                    update_challenge(db, challenge, c_data)
                elif draw_down <= -5:  # 5%
                    changed = True
                    c_data = {
                        **c_data,
                        "status": "Failed",
                        "active": "0",
                    }
                    subject = "Phase 1Challenge Failed"
                    update_challenge(db, challenge, c_data)
                    template_name = "ChallengeFailedPhase1.html"

                if email and changed:
                    send_mail(email, subject=subject, template_name=template_name, context=context)

        logger.info("Finished monitor_challenges task")
    except Exception as e:
        push_to_redis_queue(data=f"**Monitor Challenges** Testnet Monitoring - {e}", queue_name=ERROR_QUEUE_NAME)
        logger.error(f"Error in monitor_challenges task testnet - {e}")


def monitor_mainnet():
    try:
        response = call_main_net(url=STATISTICS_URL, token=STATISTICS_TOKEN)
        if not response:
            return
        data = {}
        for item in response["data"]:
            data[item["hotkey"]] = item["challengeperiod"]["status"]

        with TaskSessionLocal_() as db:
            for challenge in get_monitored_challenges(db, challenge="main"):
                hot_key = challenge.hot_key
                status = data.get(hot_key)

                if not status or status != "success":
                    continue

                c_data = {
                    "status": "Passed",
                    "active": "0",
                    "pass_the_main_net_challenge": datetime.utcnow(),
                }
                update_challenge(db, challenge, c_data)
                if challenge.phase == 1:
                    template_name = "ChallengePassedPhase1Step1.html"
                    subject = "Congratulations on Completing Phase 1!"
                else:
                    template_name = "ChallengePassedPhase2.html"
                    subject = "Congratulations on Completing Phase 2!"
                send_mail(
                    challenge.user.email,
                    subject=subject,
                    template_name=template_name,
                    context={'name': challenge.user.name, 'date': datetime.utcnow()}
                )

    except Exception as e:
        push_to_redis_queue(data=f"**Monitor Challenges** Mainnet Monitoring - {e}", queue_name=ERROR_QUEUE_NAME)
        logger.error(f"Error in monitor_challenges task mainnet - {e}")


@celery_app.task(name='src.tasks.monitor_challenges.monitor_challenges')
def monitor_challenges():
    logger.info("Starting monitor_challenges task")
    # testnet challenges
    monitor_testnet()
    # mainnet challenges
    monitor_mainnet()
