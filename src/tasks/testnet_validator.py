import asyncio
import logging
from datetime import datetime

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.services.api_service import testnet_websocket
from src.services.email_service import send_mail
from src.tasks.monitor_mainnet_challenges import get_monitored_challenges, update_challenge
from src.tasks.monitor_miner_positions import populate_redis_positions
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import push_to_redis_queue

logger = logging.getLogger(__name__)


def monitor_testnet_challenges(positions, perf_ledgers):
    try:
        with TaskSessionLocal_() as db:
            for challenge in get_monitored_challenges(db):
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
                    #     c_response = challenge.response or {}
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

                    subject = "Congratulations on Completing Phase 1!"
                    template_name = "ChallengePassedPhase1Step2.html"
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
    test_net_data = asyncio.run(testnet_websocket(monitor=True))

    if not test_net_data:
        push_to_redis_queue(
            data=f"**Testnet Listener** => Testnet Validator Checkpoint returns with status code other than 200",
            queue_name=ERROR_QUEUE_NAME
        )
        return

    positions = test_net_data["positions"]
    perf_ledgers = test_net_data["perf_ledgers"]
    populate_redis_positions(positions, _type="Testnet")
    monitor_testnet_challenges(positions, perf_ledgers)
