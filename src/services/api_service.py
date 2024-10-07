import requests

from src.config import CHECKPOINT_URL
from src.services.user_service import get_challenge


def call_main_net():
    url = "https://request.wildsage.io/miner-positions"

    headers = {
        'Content-Type': 'application/json',
        'x-taoshi-consumer-request-key': 'req_3ZR8ckpEyNZR3HjP9x8rXHj1'
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


def get_position(trader_id, trade_pair, main=True):
    if main:
        data = call_main_net()
    else:
        data = call_checkpoint_api()

    if not data:
        return

    for hot_key, content in data.items():
        challenge = get_challenge(hot_key)
        if not challenge or challenge.trader_id != trader_id:
            continue

        positions = content["positions"]
        for position in positions:
            if position["is_closed_position"] is True:
                continue

            p_trade_pair = position.get("trade_pair", [])[0]
            if p_trade_pair != trade_pair:
                continue
            return position


def get_profit_and_current_price(trader_id, trade_pair, main=True):
    position = get_position(trader_id, trade_pair, main)

    if position and position["orders"]:
        price, taoshi_profit_loss, taoshi_profit_loss_without_fee = position["orders"][-1]["price"], position[
            "return_at_close"], position["current_return"]
        profit_loss = (taoshi_profit_loss * 100) - 100
        profit_loss_without_fee = (taoshi_profit_loss_without_fee * 100) - 100
        position_uuid = position["position_uuid"]
        hot_key = position["miner_hotkey"]
        return price, profit_loss, profit_loss_without_fee, taoshi_profit_loss, taoshi_profit_loss_without_fee, position_uuid, hot_key
    return 0.0, 0.0, 0.0, 0.0, 0.0, "", ""
