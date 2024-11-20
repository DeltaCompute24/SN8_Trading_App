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

# ----------------------------- MAINNET API CONSTANTS -----------------------------
MAIN_POSITIONS_URL = "https://request.wildsage.io/miner-positions"
MAIN_POSITIONS_TOKEN = "req_3ZR8ckpEyNZR3HjP9x8rXHj1"
MAIN_STATISTICS_URL = "https://request.wildsage.io/statistics"
MAIN_STATISTICS_TOKEN = "req_3ZY8hrPfrzMfkzZHNr9QNQw5"
NEW_MAIN_POSITIONS_URL = "http://165.227.89.220:8888/download?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzIyMTQ0MzUsImlhdCI6MTcyOTYyMjQzNX0.-5Wk48T5tl7C-ULkrkyRfzSS77SV-3lk5dWPn5VjtbE"

# -------------------- Assets Minimum and Maximum Leverages -------------------------
CRYPTO_MIN_LEVERAGE = 0.01
CRYPTO_MAX_LEVERAGE = 0.5
FOREX_MIN_LEVERAGE = 0.1
FOREX_MAX_LEVERAGE = 5
INDICES_MIN_LEVERAGE = 0.1
INDICES_MAX_LEVERAGE = 5
