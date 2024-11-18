import requests

from src.config import CHECKPOINT_URL, POSITIONS_URL, POSITIONS_TOKEN
from src.services.user_service import get_hot_key


def call_main_net(url=POSITIONS_URL, token=POSITIONS_TOKEN):
    headers = {
        'Content-Type': 'application/json',
        'x-taoshi-consumer-request-key': token,
    }

    response = requests.request(method="GET", url=url, headers=headers)
    if response.status_code != 200:
        return {}
    return response.json()


def call_checkpoint_api():
    response = requests.get(CHECKPOINT_URL)
    if response.status_code != 200:
        return {}

    return response.json()["positions"]


def get_position(trader_id, trade_pair, main=True, position_uuid=None):
    if main:
        data = call_main_net()
    else:
        data = call_checkpoint_api()

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
            position["orders"]), position["average_entry_price"]
    return 0.0, 0.0, 0.0, 0.0, 0.0, "", "", 0, 0
