import requests

from src.config import POSITIONS_URL, POSITIONS_TOKEN, TESTNET_CHECKPOINT_URL
from src.services.user_service import get_hot_key
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import push_to_redis_queue


def call_main_net(url=POSITIONS_URL, token=POSITIONS_TOKEN):
    headers = {
        'Content-Type': 'application/json',
        'x-taoshi-consumer-request-key': token,
    }

    response = requests.request(method="GET", url=url, headers=headers)
    if response.status_code != 200:
        return {}
    return response.json()


def testnet_websocket(monitor=False):
    try:
        response = requests.request(method="GET", url=TESTNET_CHECKPOINT_URL)
        if response.status_code != 200:
            push_to_redis_queue(
                data=f"**Testnet API Call** => Testnet Validator Checkpoint returns with status code other than 200, response => {response}",
                queue_name=ERROR_QUEUE_NAME
            )
            return {}
        testnet_data = response.json()
        if monitor:
            return testnet_data
        return testnet_data["positions"]
    except Exception as e:
        print(f"Error: {e}")
        push_to_redis_queue(
            data=f"**Testnet API Call** => Testnet Validator Checkpoint returns with status code other than 200, ERROR => {e}",
            queue_name=ERROR_QUEUE_NAME
        )
        return {}


def get_position(trader_id, trade_pair, main=True, position_uuid=None):
    if main:
        data = call_main_net()
    else:
        data = testnet_websocket()

    if not data:
        return

    hot_key = get_hot_key(trader_id)
    content = data.get(hot_key)
    if not content:
        return

    positions = content["positions"]
    for position in positions:
        if position_uuid and position["position_uuid"] == position_uuid:
            return position

        if position["is_closed_position"] is True:
            continue

        p_trade_pair = position.get("trade_pair", [])[0]
        if p_trade_pair != trade_pair:
            continue
        return position


def get_profit_and_current_price(trader_id, trade_pair, main=True, position_uuid=None):
    position = get_position(trader_id, trade_pair, main, position_uuid=position_uuid)

    if position and position["orders"]:
        price, taoshi_profit_loss, taoshi_profit_loss_without_fee = position["orders"][-1]["price"], position[
            "return_at_close"], position["current_return"]
        profit_loss = (taoshi_profit_loss * 100) - 100
        profit_loss_without_fee = (taoshi_profit_loss_without_fee * 100) - 100
        position_uuid = position["position_uuid"]
        hot_key = position["miner_hotkey"]
        return price, profit_loss, profit_loss_without_fee, taoshi_profit_loss, taoshi_profit_loss_without_fee, position_uuid, hot_key, len(
            position["orders"]), position["average_entry_price"], position["is_closed_position"]
    return 0.0, 0.0, 0.0, 0.0, 0.0, "", "", 0, 0, False
