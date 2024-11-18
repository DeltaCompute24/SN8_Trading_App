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
CHALLENGE_QUEUE_NAME = "challenges_queue"

# ----------------------------- MAINNET API CONSTANTS -----------------------------
MAIN_POSITIONS_URL = "https://request.wildsage.io/miner-positions"
MAIN_POSITIONS_TOKEN = "req_3ZR8ckpEyNZR3HjP9x8rXHj1"
MAIN_STATISTICS_URL = "https://request.wildsage.io/statistics"
MAIN_STATISTICS_TOKEN = "req_3ZY8hrPfrzMfkzZHNr9QNQw5"
NEW_MAIN_POSITIONS_URL = "http://165.227.89.220:8888/download?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzIyMTQ0MzUsImlhdCI6MTcyOTYyMjQzNX0.-5Wk48T5tl7C-ULkrkyRfzSS77SV-3lk5dWPn5VjtbE"
