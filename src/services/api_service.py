import requests

from src.config import CHECKPOINT_URL, MAIN_NET

ambassadors = {
    "5CRwSWfJWnMat1wtUvLTLUJ3ekTTgn1XDC8jVko2H9CmnYC1": 4040,
    "5ERQp6a5Cd5MsTNnmXQsfrrRoiFvXy6ojE734Z4NxTmaEiiZ": 4041,
    "5DUdBHPKqwB3Pv85suEZxSyf8EVfcV9V4iPyZaEAMfvzBkp6": 4042,
    "5FKqNPgDrZCwo4GgMAjTo77L4KRTNcQgpzMWASvDGPRJGZRP": 4043,
    "5Ew171L2s9RX2wZXbPwS1kcmhyAjzEXSG5W9551bcRqsL3Pg": 4070,
    "5ERNiynJejVeK6BtHXyyBJNB6RXNzwERhgHjcK7jbNT4n9xQ": 4071,
    "5DthKaDbqEauMm25rKmKQCjJYvbshR84NzhAVT4zLq4Dz4qK": 4072,
    "5Fc39mqXCJrkwVLTZCduUgkmkUv7Rsz2kgtkHQVMQo8ZTn5U": 4063,
    "5GCDZ6Vum2vj1YgKtw7Kv2fVXTPmV1pxoHh1YrsxqBvf9SRa": 4064,
    "5GTL7WXa4JM2yEUjFoCy2PZVLioNs1HzAGLKhuCDzzoeQCTR": 4065,
}


def call_main_net():
    url = "https://request.wildsage.io/miner-positions"

    headers = {
        'Content-Type': 'application/json',
        'x-taoshi-consumer-request-key': 'req_3ZR8ckpEyNZR3HjP9x8rXHj1'
    }

    response = requests.request(method="GET", url=url, headers=headers)
    if response.status_code != 200:
        return

    return response.json()


def get_position(trader_id, trade_pair):
    data = call_main_net()
    if not data:
        return

    for hot_key, content in data.items():
        p_trade_id = ambassadors.get(hot_key, "")
        if not p_trade_id or p_trade_id != trader_id:
            continue

        positions = content["positions"]
        for position in positions:
            if position["is_closed_position"] is True:
                continue

            p_trade_pair = position.get("trade_pair", [])[0]
            if p_trade_pair != trade_pair:
                continue
            return position


def get_testing_position(trader_id, trade_pair):
    response = requests.get(CHECKPOINT_URL)
    if response.status_code != 200:
        return

    data = response.json()["positions"]

    for hot_key, _data in data.items():
        p_trade_id = ambassadors.get(hot_key, "")
        if not p_trade_id or p_trade_id != trader_id:
            continue

        positions = _data.get("positions") or []
        for position in positions:
            if position["is_closed_position"] is True:
                continue

            p_trade_pair = position.get("trade_pair", [])[0]
            if p_trade_pair != trade_pair:
                continue
            return position


def get_profit_and_current_price(trader_id, trade_pair):
    if MAIN_NET:
        position = get_position(trader_id, trade_pair)
    else:
        position = get_testing_position(trader_id, trade_pair)
    if position and position["orders"]:
        return position["orders"][-1]["price"], position["return_at_close"], position["current_return"]
    return 0.0, 0.0, 0.0
