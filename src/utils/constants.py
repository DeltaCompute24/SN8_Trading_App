forex_pairs = [
    # forex
    'AUDCAD', 'AUDUSD', 'AUDJPY', 'AUDNZD',
    'CADCHF', 'CADJPY', 'CHFJPY',
    'EURCAD', 'EURUSD', 'EURCHF', 'EURGBP', 'EURJPY', 'EURNZD',
    'NZDCAD', 'NZDJPY', 'NZDUSD',
    'GBPUSD', 'GBPJPY',
    'USDCAD', 'USDCHF', 'USDJPY', 'USDMXN',
    # "Commodities" (Bundle with Forex for now)
    'XAUUSD', 'XAGUSD',
]

stocks_pairs = [
    'NVDA', 'AAPL', 'TSLA', 'AMZN', 'MSFT', 'GOOG', 'META',
]

crypto_pairs = [
    'BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD', 'DOGEUSD',
]

indices_pairs = [
    'SPX', 'DJI', 'NDX', 'VIX', 'FTSE', 'GDAXI',
]

# ----------------------------- REDIS CONSTANTS --------------------------------
REDIS_LIVE_PRICES_TABLE = 'live_prices'
POSITIONS_TABLE = 'positions'
OPERATION_QUEUE_NAME = 'db_operations_queue'
ERROR_QUEUE_NAME = 'errors'
TOURNAMENT = 'tournament_score'

# -------------------- Assets Minimum and Maximum Leverages -------------------------
CRYPTO_MIN_LEVERAGE = 0.01
CRYPTO_MAX_LEVERAGE = 0.5

FOREX_MIN_LEVERAGE = 0.1
FOREX_MAX_LEVERAGE = 5

INDICES_MIN_LEVERAGE = 0.1
INDICES_MAX_LEVERAGE = 5

STOCKS_MIN_LEVERAGE = 0.1
STOCKS_MAX_LEVERAGE = 5
