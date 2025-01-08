import logging
from datetime import datetime

import requests

from src.config import SWITCH_TO_MAINNET_URL
from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.services.api_service import testnet_websocket
from src.services.email_service import send_mail, send_support_email
from src.tasks.monitor_mainnet_challenges import get_monitored_challenges, update_challenge
from src.tasks.monitor_miner_positions import populate_redis_positions
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import push_to_redis_queue

logger = logging.getLogger(__name__)


def get_profit_sum_and_draw_down(challenge, positions, perf_ledgers):
    hot_key = challenge.hot_key
    p_content = positions.get(hot_key)
    l_content = perf_ledgers.get(hot_key)
    if not p_content or not l_content:
        return {}

    profit_sum = 0
    for position in p_content["positions"]:
        profit_loss = (position["return_at_close"] * 100) - 100
        if position["is_closed_position"] is True:
            profit_sum += profit_loss

    return {
        "draw_down": (l_content["cps"][-1]["mdd"] * 100) - 100,
        "profit_sum": profit_sum,
    }


def monitor_testnet_challenges(positions, perf_ledgers):
    try:
        with TaskSessionLocal_() as db:
            for challenge in get_monitored_challenges(db):
                logger.info(f"Monitor first testnet Challenge!")
                name = challenge.user.name
                email = challenge.user.email

                c_data = get_profit_sum_and_draw_down(challenge, positions, perf_ledgers)
                if not c_data:
                    continue
                profit_sum = c_data["profit_sum"]
                draw_down = c_data["draw_down"]
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
        push_to_redis_queue(data=f"**Monitor Testnet Challenges** Testnet Monitoring - {e}",
                            queue_name=ERROR_QUEUE_NAME)
        logger.error(f"Error in monitor_challenges task testnet - {e}")


@celery_app.task(name='src.tasks.testnet_validator.testnet_validator')
def testnet_validator():
    logger.info("Starting monitor testnet validator task")
    test_net_data = testnet_websocket(monitor=True)

    if not test_net_data:
        return

    positions = test_net_data["positions"]
    perf_ledgers = test_net_data["perf_ledgers"]
    populate_redis_positions(positions, _type="Testnet")
    monitor_testnet_challenges(positions, perf_ledgers)
