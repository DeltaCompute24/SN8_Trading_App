import aiohttp
from throttler import Throttler

from src.config import SIGNAL_API_KEY, SIGNAL_API_BASE_URL
from src.utils.logging import setup_logging

# Set the rate limit: max 10 requests per second
throttler = Throttler(rate_limit=10, period=1.0)

logger = setup_logging()


class WebSocketManager:

    async def submit_trade(self, trader_id, trade_pair, order_type, leverage):
        signal_api_url = SIGNAL_API_BASE_URL.format(id=trader_id)
        params = {
            "api_key": SIGNAL_API_KEY,
            "trade_pair": trade_pair,
            "order_type": order_type,
            "leverage": leverage
        }
        print("SIGNAL API REQUEST", params)
        async with aiohttp.ClientSession() as session:
            async with throttler:
                async with session.post(signal_api_url, json=params) as response:
                    print("SIGNAL API RESPONSE", response)
                    response_text = await response.text()
                    print("SIGNAL API RESPONSE TEXT", response_text)
                    logger.info(f"Submit trade signal sent. Response: {response_text}")
                    return response.status == 200


websocket_manager = WebSocketManager()
