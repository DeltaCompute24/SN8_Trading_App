import aiohttp
import asyncio
from .utils import setup_logging, colored

logger = setup_logging()

class ForecastClient:
    def __init__(self, url):
        self.url = url

    async def fetch_predictions(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(colored("Forecast data fetched successfully", "green"))
                    return data['predictions']
                else:
                    logger.error(colored(f"Failed to fetch forecast data: HTTP {response.status}", "red"))
                    return None
