import asyncio
import logging

from sqlalchemy.future import select

from src.core.celery_app import celery_app
from src.database_tasks import get_task_db
from src.models.transaction import Transaction
from src.utils.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

from redis import asyncio as aioredis
from src.config import REDIS_URL

redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

current_subscriptions = set()
subscription_tasks = {}


@celery_app.task(name='src.tasks.subscription_manager.manage_subscriptions')
def manage_subscriptions():
    logger.info("Starting manage_subscriptions")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(manage_subscriptions_async())


async def manage_subscriptions_async():
    logger.info("Starting manage_subscriptions_async")
    trade_pairs = await get_unique_trade_pairs()
    if trade_pairs:
        logger.info(f"Current monitored trade pairs: {trade_pairs}")
        await manage_trade_pair_subscriptions(trade_pairs)
    else:
        await redis_client.delete("current_prices")
        logger.info("No trade pairs to monitor.")
    logger.info("Finished manage_subscriptions_async")


async def get_unique_trade_pairs():
    logger.info("Fetching unique trade pairs from database")
    async with get_task_db() as db:
        # need to create a const list of trade pairs and retreive them form here as we are monitoring all those trade pairs/
        result = await db.execute(
            select(Transaction.trade_pair, Transaction.asset_type).where(Transaction.status != "CLOSED").distinct())
        trade_pairs = [(row.trade_pair, row.asset_type) for row in result.all()]
        logger.info(f"Retrieved trade pairs: {trade_pairs}")
        return trade_pairs


async def manage_trade_pair_subscriptions(trade_pairs):
    global current_subscriptions, subscription_tasks
    active_trade_pairs = set(trade_pairs)

    new_pairs = active_trade_pairs - current_subscriptions
    removed_pairs = current_subscriptions - active_trade_pairs

    # Log the new and removed pairs
    logger.info(f"New trade pairs to subscribe: {new_pairs}")
    logger.info(f"Trade pairs to unsubscribe: {removed_pairs}")

    # Unsubscribe from removed pairs
    for pair in removed_pairs:
        logger.info(f"Unsubscribing from trade pair: {pair}")
        await websocket_manager.unsubscribe(pair[0])
        await redis_client.hdel("current_prices", pair[0])
        current_subscriptions.remove(pair)
        task = subscription_tasks.pop(pair, None)
        if task:
            task.cancel()
            logger.info(f"Cancelled task for trade pair: {pair}")

    # Subscribe to new pairs
    for pair in new_pairs:
        asset_type = pair[1]
        trade_pair = pair[0]
        logger.info(f"Subscribing to new trade pair: {pair}")
        if not websocket_manager.websocket or websocket_manager.websocket.closed:
            await websocket_manager.connect(asset_type)
        await websocket_manager.subscribe(trade_pair)
        current_subscriptions.add(pair)
        task = asyncio.create_task(websocket_manager.listen_for_price(trade_pair, asset_type))
        subscription_tasks[pair] = task
        logger.info(f"Started task for trade pair: {pair}")

    # Ensure active subscriptions are being listened to
    for pair in active_trade_pairs:
        if pair not in subscription_tasks:
            logger.info(f"Ensuring active subscription for trade pair: {pair}")
            task = asyncio.create_task(websocket_manager.listen_for_price(pair[0], pair[1]))
            subscription_tasks[pair] = task
    logger.error(f"Current Prices Dict: {redis_client.hgetall('current_prices')}")
    logger.error(f"Current Prices: {websocket_manager.current_prices}")
    logger.info(f"Active subscriptions: {current_subscriptions}")


@celery_app.task(bind=True, name='src.tasks.subscription_manager.trade_pair_worker')
def trade_pair_worker(self, trade_pair):
    logger.info(f"Starting trade_pair_worker for {trade_pair}")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(trade_pair_worker_async(trade_pair))


async def trade_pair_worker_async(trade_pair):
    asset_type, pair = trade_pair
    logger.info(f"Starting trade_pair_worker_async for {trade_pair}")
    await websocket_manager.connect(asset_type)
    await websocket_manager.subscribe(pair)
    await websocket_manager.listen_for_price(pair, asset_type)
    logger.info(f"Finished trade_pair_worker_async for {trade_pair}")
