import logging
from datetime import datetime

import requests
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.config import CHECKPOINT_URL, REGISTRATION_API_URL
from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.challenge import Challenge
from src.services.email_service import send_mail

logger = logging.getLogger(__name__)


def get_monitored_challenges(db: Session):
    try:
        logger.info("Fetching monitored challenges from database")
        result = db.execute(
            select(Challenge).where(
                and_(
                    Challenge.status == "In Challenge",
                    Challenge.active == "1",
                    Challenge.challenge == "test"
                )
            )
        )
        challenges = result.scalars().all()
        logger.info(f"Retrieved {len(challenges)} monitored challenges")
        return challenges
    except Exception as e:
        logger.error(f"An error occurred while fetching monitored challenges: {e}")
        return []


def update_challenge(db: Session, challenge, data):
    logger.info(f"Updating monitored challenge: {challenge.trader_id} - {challenge.hot_key}")

    for key, value in data.items():
        setattr(challenge, key, value)

    db.commit()
    db.refresh(challenge)


@celery_app.task(name='src.tasks.monitor_challenges.monitor_challenges')
def monitor_challenges():
    logger.info("Starting monitor_challenges task")

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
            p_content = positions.get(hot_key)
            l_content = perf_ledgers.get(hot_key)
            if not (p_content or l_content):
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

            if profit_sum >= 2:  # 2%
                # new_object = {"id": challenge.id, "pass_the_challenge": datetime.utcnow(), "status": "Passed"}
                network = "main" if challenge.challenge == "test" else "test"
                payload = {
                    "hot_key": challenge.hot_key,
                    # "name": f"{username}_{challenge.id}",
                    "network": network,
                }
                response = requests.post(REGISTRATION_API_URL, json=payload)

                c_data = {
                    **c_data,
                    "status": "Passed",
                    "pass_the_challenge": datetime.utcnow(),
                }

                content = "Congratulations! You have entered to Phase 2 from Phase 1!"
                if response.status_code == 200:
                    c_response = challenge.response
                    c_response["main_net_response"] = response.json()
                    c_data = {
                        **c_data,
                        "challenge": network,
                        "trader_id": data.get("trader_id"),
                        "hot_key": data.get("hot_key"),
                        "response": c_response,
                    }
                    content = f"{content} Your testnet key is also converted to hot_key!"
                subject = "Challenge Passed"
                update_challenge(db, challenge, c_data)
            elif draw_down <= -5:  # 5%
                c_data = {
                    **c_data,
                    "status": "Failed",
                }
                subject = "Challenge Failed"
                content = "Unfortunately! You have Failed!"
                update_challenge(db, challenge, c_data)

            email = challenge.user.email
            if not email:
                continue
            send_mail(email, subject, content)

    logger.info("Finished monitor_challenges task")
