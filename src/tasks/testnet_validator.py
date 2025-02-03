import logging
from datetime import datetime , timedelta
from enum import Enum
import traceback
import requests
from .vali_config import DeltaValiConfig
from src.config import SWITCH_TO_MAINNET_URL
from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.services.api_service import testnet_websocket
from src.services.email_service import send_mail, send_support_email
from src.tasks.monitor_mainnet_challenges import get_monitored_challenges, update_challenge
from src.tasks.monitor_miner_positions import populate_redis_positions
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
        close_time = datetime.fromtimestamp(position.get("close_ms") / 1000)
        if close_time > cutoff_time:
            one_day_realized_returns += profit_loss
        
        
        total_realized_returns += profit_loss
    
    logger.info(f"Ran Criteria Checks : total {total_realized_returns} , one day {one_day_realized_returns}")

    
    if total_realized_returns < TOTAL_REALIZED_RETURNS_LIMIT: return False,0
    
    if one_day_realized_returns > (ONE_DAY_REALIZED_RETURNS_LIMIT_RATIO * total_realized_returns ) : return False,0
    
    return True, total_realized_returns


def is_miner_passing_all_screening_criterias(test_net_positions : list[Dict]):
    """
     test_net_positions : specific positions of the challenge
     perf_ledgers : specific information of the challenge
    """
    return check_all_returns_passing_criteria(test_net_positions)


def pass_miner_to_main_net(challenge : Challenge, total_profits : float):
    email = challenge.user.email
    network = "main"
    payload = {
        "name": challenge.challenge_name,
        "trader_id": challenge.trader_id,
    }
    
    logger.info(f"Switch to Mainnet called : Miner Passed")
    _response = requests.post(SWITCH_TO_MAINNET_URL, json=payload)
    
    data = _response.json()
  
    if _response.status_code == 200:
        c_response = challenge.response or {}
        c_response["main_net_response"] = data
        passing_details = {
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

def fail_miner_in_delta(db , challenge: Challenge ,total_profits : float):
    logger.info(f"{challenge.hot_key}  last status update : Fail")
    name = challenge.user.name
    email = challenge.user.email
    challenge_details = {
         "profit_loss" : total_profits,
        "status": "Failed",
        "active": "0",
    }
    context = {
                "name": name,
                "trader_id": challenge.trader_id,
            }
    subject = "Phase 1 Challenge Failed"
    template_name = "ChallengeFailedPhase1.html"

    update_challenge(db, challenge, challenge_details)
    send_mail(email, subject=subject, template_name=template_name, context=context)
    
    logger.info(f"{challenge.hot_key}  last status update : Miner Failed Success")


def pass_miner_in_delta(db , challenge: Challenge ,total_profits : float ):

    challenge_details = pass_miner_to_main_net(challenge, total_profits  )
    name = challenge.user.name
    email = challenge.user.email
    
    if not challenge_details: return
    subject = "Congratulations on Completing Phase 1!"
    template_name = "ChallengePassedPhase1Step2.html"
    context = {
        "name": name,
        "trader_id": challenge_details["trader_id"],
    }
    
    update_challenge(db, challenge, challenge_details)
    send_mail(email, subject=subject, template_name=template_name, context=context)

def is_miner_eliminated(eliminations : list, hot_key : str) -> bool:
    
    for miner in eliminations:
        if miner.get("hotkey") == hot_key:
            return True
    
    return False

def monitor_testnet_challenges(test_net_positions, perf_ledgers , eliminations , challenge_period):
    try:
        with TaskSessionLocal_() as db:
            for challenge in get_monitored_challenges(db):
                logger.info(f"Checking Pass/Fail testnet challenge : {challenge.trader_id}")
             
                hot_key = challenge.hot_key
                
                #check testnet positions structure
                p_content = test_net_positions.get(hot_key)
                l_content = perf_ledgers.get(hot_key)
                is_eliminated = is_miner_eliminated(eliminations , hot_key)
                logger.info(f"{challenge.hot_key}  Running Checks")

                
                if l_content and is_eliminated:
                    #Miner Already Failed in TestNet, So Fail in Delta 
                    logger.info(f"{challenge.hot_key}  checking if Eliminated")

                    fail_miner_in_delta(db, challenge , 0)
                
                elif l_content:
                    #Checking Miners Most Recent Drawdown
                    logger.info(f"{challenge.hot_key} checking mdd in ledgers")
                    cps = l_content.get('cps',[])
                    most_recent_drawdown = cps[0]['mdd'] if cps else 0
                    if most_recent_drawdown > 5:
                        fail_miner_in_delta(db, challenge , 0)
                    
                elif p_content and (hot_key in challenge_period.get("success") or hot_key in challenge_period.get("testing")) :
                    logger.info(f"{challenge.hot_key}  last status update : Testing or Success")
                    positions = p_content.get("positions")
                    is_passing,  total_profits = is_miner_passing_all_screening_criterias(positions)
                    if not is_passing : continue
                    # Miner was In Challenge in TestNet but Passes Delta Criteria
                    logger.info(f"{challenge.hot_key}  last status update : pass")
                    pass_miner_in_delta(db , challenge ,total_profits  )
                

                

        logger.info("Finished monitor_challenges task")
    except Exception as e:
        stack_trace = ''.join(traceback.format_exception(type(e), e, e.__traceback__))

        logger.error(f"Error in Pass/Fail TestNet task - {stack_trace}")


@celery_app.task(name='src.tasks.testnet_validator.testnet_validator')
def testnet_validator():
    """
        perf ledgers object have only eliminated hotkeys.
        positions have all hot keys - eliminated or successful
        Some hotkeys in positions wont exist in perfs because they are still in challenge
        
        
    """
    logger.info("Starting monitor testnet validator task")
    test_net_data = testnet_websocket(monitor=True)

    if not test_net_data:
        return

    positions = test_net_data.get("positions")
    perf_ledgers = test_net_data.get("perf_ledgers")
    eliminations = test_net_data.get("eliminations")
    challenge_period = test_net_data.get("challengeperiod")
    populate_redis_positions(positions, _type="Testnet")
    monitor_testnet_challenges(positions, perf_ledgers , eliminations , challenge_period)
