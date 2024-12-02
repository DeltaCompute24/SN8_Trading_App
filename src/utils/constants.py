forex_pairs = [
    'NZDUSD', 'NZDCAD', 'EURCAD', 'EURUSD', 'EURJPY', 'AUDJPY', 'AUDUSD', 'AUDCAD', 'EURNZD', 'AUDNZD',
    'USDCAD', 'EURGBP', 'USDJPY', 'EURCHF', 'GBPUSD', 'CADJPY', 'NZDJPY', 'USDCHF', 'GBPJPY', 'CHFJPY',
    'CADCHF', 'USDMXN',
]

crypto_pairs = [
    'BTCUSD', 'ETHUSD',
]

indices_pairs = [
    'GDAXI', 'NDX', 'VIX', 'SPX', 'DJI', 'FTSE',
]

# ----------------------------- REDIS CONSTANTS --------------------------------
REDIS_LIVE_PRICES_TABLE = 'live_prices'
POSITIONS_TABLE = 'positions'
OPERATION_QUEUE_NAME = "db_operations_queue"
ERROR_QUEUE_NAME = "errors"
TESTNET_TABLE = "testnet"

# -------------------- Assets Minimum and Maximum Leverages -------------------------
CRYPTO_MIN_LEVERAGE = 0.01
CRYPTO_MAX_LEVERAGE = 0.5
FOREX_MIN_LEVERAGE = 0.1
FOREX_MAX_LEVERAGE = 5
INDICES_MIN_LEVERAGE = 0.1
INDICES_MAX_LEVERAGE = 5
