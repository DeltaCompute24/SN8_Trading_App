import requests

from src.config import CHECKPOINT_URL

ambassadors = {
    "5CRwSWfJWnMat1wtUvLTLUJ3ekTTgn1XDC8jVko2H9CmnYC1": 4040,
    "5EHtvpzc9zMeYeB4yiAgyBLMaVbeF5SS72B2vKNwWMcsESXM": 4041,
    "5Hj7FM5YwWurQCG5YYhuw47vQvqBPD2pYzMYLsH3iuyBQBkQ": 4042,
    "5CuAFv865cNFWKnawrdEY1fV318cLubh9pabAPjjYHLJxWzN": 4043,
    "5Fc39mqXCJrkwVLTZCduUgkmkUv7Rsz2kgtkHQVMQo8ZTn5U": 4063,
    "5GCDZ6Vum2vj1YgKtw7Kv2fVXTPmV1pxoHh1YrsxqBvf9SRa": 4064,
    "5GTL7WXa4JM2yEUjFoCy2PZVLioNs1HzAGLKhuCDzzoeQCTR": 4065,
}


def get_profit_loss(trader_id, trade_pair):
    response = requests.get(CHECKPOINT_URL)
    if response.status_code != 200:
        return 0.00

    data = response.json()["positions"]

    for hot_key, _data in data.items():
        p_trade_id = ambassadors.get(hot_key, "")
        if not p_trade_id or p_trade_id != trader_id:
            continue

        positions = _data.get("positions") or []
        for position in positions:
            p_trade_pair = position.get("trade_pair", [])[0]
            if p_trade_pair != trade_pair:
                continue

            return position["current_return"]
    return 0.00
