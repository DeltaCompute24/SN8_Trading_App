import logging
from datetime import datetime , timedelta
from enum import Enum
import requests
from vali_config import DeltaValiConfig
from src.config import SWITCH_TO_MAINNET_URL
from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.services.api_service import testnet_websocket
from src.services.email_service import send_mail, send_support_email
from src.tasks.monitor_mainnet_challenges import get_monitored_challenges, update_challenge
from src.tasks.monitor_miner_positions import populate_redis_positions
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import push_to_redis_queue
from src.models.challenge import Challenge
from typing import Tuple, List, Dict
logger = logging.getLogger(__name__)

REALIZED_RETURNS_LIMIT = DeltaValiConfig.CHALLENGE_PERIOD_MAX_POSITIONAL_RETURNS_RATIO * 100
TOTAL_REALIZED_RETURNS_LIMIT = DeltaValiConfig.CHALLENGE_PERIOD_MAX_REALIZED_RETURNS_RATIO * 100
ONE_DAY_REALIZED_RETURNS_LIMIT_RATIO = DeltaValiConfig.CHALLENGE_PERIOD_MAX_REALIZED_RETURNS_RATIO_ONE_DAY


class ChallengeStatus(str, Enum):
    PASSED = 'pass'
    FAILED = 'failed'
    IN_CHALLENGE = 'in-challenge'


def check_all_returns_passing_criteria( positions : list) -> Tuple[bool, float]:
     
    total_realized_returns = 0
    one_day_realized_returns = 0
    
    cutoff_time = datetime.utcnow() - timedelta(days=DeltaValiConfig.REALIZED_RETURNS_WINDOW)
    
    for position in positions:
        if not position["is_closed_position"]: continue
        profit_loss = (position["return_at_close"] * 100) - 100
        if profit_loss >= REALIZED_RETURNS_LIMIT : return False,0
        
        if position['close_time'] > cutoff_time:
            one_day_realized_returns += profit_loss
        
        
        total_realized_returns += profit_loss
    
    if total_realized_returns < TOTAL_REALIZED_RETURNS_LIMIT: return False,0
    
    if one_day_realized_returns > (ONE_DAY_REALIZED_RETURNS_LIMIT_RATIO * total_realized_returns ) : return False,0
    
    return True, total_realized_returns


def is_miner_passing_all_screening_criterias(test_net_positions : list[Dict]):
    """
     test_net_positions : specific positions of the challenge
     perf_ledgers : specific information of the challenge
    """
    return check_all_returns_passing_criteria(test_net_positions)


def pass_miner_to_main_net(challenge : Challenge, draw_down : float, total_profits : float):
    email = challenge.user.email
    network = "main"
    payload = {
        "name": challenge.challenge_name,
        "trader_id": challenge.trader_id,
    }
    _response = requests.post(SWITCH_TO_MAINNET_URL, json=payload)
    data = _response.json()
    if _response.status_code == 200:
        c_response = challenge.response or {}
        c_response["main_net_response"] = data
        passing_details = {
            "draw_down" : draw_down,
            "profit_sum" : total_profits,
            "status": "Passed",
            "pass_the_challenge": datetime.utcnow(),
            "phase": 2,
            "challenge": network,
            "active": "1",
            "trader_id": data.get("trader_id"),
            "response": c_response,
            "register_on_main_net": datetime.utcnow(),
        }
        return passing_details

    send_support_email(
        subject=f"Switch from testnet to mainnet API call failed with status code: {_response.status_code}",
        content=f"User {email} passed step {challenge.step} and phase {challenge.phase} "
                f"but switch_to_mainnet Failed. Response from switch_to_mainnet api => {data}",
    )
    return {}



def monitor_testnet_challenges(test_net_positions, perf_ledgers):
    try:
        with TaskSessionLocal_() as db:
            for challenge in get_monitored_challenges(db):
                logger.info(f"Checking Pass/Fail testnet challenge : {challenge.trader_id}")
                name = challenge.user.name
                email = challenge.user.email
                status = ChallengeStatus.IN_CHALLENGE
                hot_key = challenge.hot_key
                
                #check testnet positions structure
                p_content = test_net_positions.get(hot_key)
                l_content = perf_ledgers.get(hot_key)
                if not p_content or not l_content:
                    continue
                draw_down = (l_content["cps"][-1]["mdd"] * 100) - 100
                is_passing,  total_profits = is_miner_passing_all_screening_criterias(p_content)
                is_failing = draw_down <= -DeltaValiConfig.CHALLENGE_PERIOD_MAX_DRAWDOWN  # 5%
                challenge_details = {
                    "draw_down" : draw_down,
                    "profit_loss" : total_profits
                }
                
                context = {
                        "name": name,
                        "trader_id": challenge.trader_id,
                    }
                subject = ""
                template_name = ""
                
                if is_passing:
                    status = ChallengeStatus.PASSED
                    challenge_details = pass_miner_to_main_net(challenge , draw_down, total_profits  )
                    if challenge_details:
                        subject = "Congratulations on Completing Phase 1!"
                        template_name = "ChallengePassedPhase1Step2.html"
                        context = {
                            "name": name,
                            "trader_id": challenge_details["trader_id"],
                        }

                elif is_failing: 
                    status = ChallengeStatus.FAILED
                    challenge_details = {
                        **challenge_details,
                        "status": "Failed",
                        "active": "0",
                    }
                    subject = "Phase 1 Challenge Failed"
                    template_name = "ChallengeFailedPhase1.html"
                    

                if status != ChallengeStatus.IN_CHALLENGE:
                    update_challenge(db, challenge, challenge_details)
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
