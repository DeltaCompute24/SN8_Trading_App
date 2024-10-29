forex_pairs = [
    {"value": "NZDUSD", "label": "NZDUSD", "asset_type": "forex", "platform": "FX"},
    {"value": "NZDCAD", "label": "NZDCAD", "asset_type": "forex", "platform": "FX"},
    {"value": "EURCAD", "label": "EURCAD", "asset_type": "forex", "platform": "FX"},
    {"value": "EURUSD", "label": "EURUSD", "asset_type": "forex", "platform": "FX"},
    {"value": "EURJPY", "label": "EURJPY", "asset_type": "forex", "platform": "FX"},
    {"value": "AUDJPY", "label": "AUDJPY", "asset_type": "forex", "platform": "FX"},
    {"value": "AUDUSD", "label": "AUDUSD", "asset_type": "forex", "platform": "FX"},
    {"value": "AUDCAD", "label": "AUDCAD", "asset_type": "forex", "platform": "FX"},
    {"value": "EURNZD", "label": "EURNZD", "asset_type": "forex", "platform": "FX"},
    {"value": "AUDNZD", "label": "AUDNZD", "asset_type": "forex", "platform": "FX"},
    {"value": "USDCAD", "label": "USDCAD", "asset_type": "forex", "platform": "FX"},
    {"value": "EURGBP", "label": "EURGBP", "asset_type": "forex", "platform": "FX"},
    {"value": "USDJPY", "label": "USDJPY", "asset_type": "forex", "platform": "FX"},
    {"value": "EURCHF", "label": "EURCHF", "asset_type": "forex", "platform": "FX"},
    {"value": "GBPUSD", "label": "GBPUSD", "asset_type": "forex", "platform": "FX"},
    {"value": "CADJPY", "label": "CADJPY", "asset_type": "forex", "platform": "FX"},
    {"value": "NZDJPY", "label": "NZDJPY", "asset_type": "forex", "platform": "FX"},
    {"value": "USDCHF", "label": "USDCHF", "asset_type": "forex", "platform": "FX"},
    {"value": "GBPJPY", "label": "GBPJPY", "asset_type": "forex", "platform": "FX"},
    {"value": "CHFJPY", "label": "CHFJPY", "asset_type": "forex", "platform": "FX"},
    {"value": "CADCHF", "label": "CADCHF", "asset_type": "forex", "platform": "FX"},
    {"value": "USDMXN", "label": "USDMXN", "asset_type": "forex", "platform": "FX"},
]

crypto_pairs = [
    {"value": "BTCUSD", "label": "BTCUSD", "asset_type": "crypto", "platform": "CR"},
    {"value": "ETHUSD", "label": "ETHUSD", "asset_type": "crypto", "platform": "CR"},
]

indices_pairs = [
    {"value": "NDX", "label": "NDX", "asset_type": "indices", "platform": "IN"},
    {"value": "VIX", "label": "VIX", "asset_type": "indices", "platform": "IN"},
    {"value": "GDAXI", "label": "GDAXI", "asset_type": "indices", "platform": "IN"},
]

# ----------------------------- REDIS CONSTANTS --------------------------------
REDIS_LIVE_PRICES_TABLE = 'live_prices'
POSITIONS_TABLE = 'positions'
OPERATION_QUEUE_NAME = "db_operations_queue"
CHALLENGE_QUEUE_NAME = "challenges_queue"

# ----------------------------- MAINNET API CONSTANTS -----------------------------
MAIN_POSITIONS_URL = "https://request.wildsage.io/miner-positions"
MAIN_POSITIONS_TOKEN = "req_3ZR8ckpEyNZR3HjP9x8rXHj1"
MAIN_STATISTICS_URL = "https://request.wildsage.io/statistics"
MAIN_STATISTICS_TOKEN = "req_3ZY8hrPfrzMfkzZHNr9QNQw5"
