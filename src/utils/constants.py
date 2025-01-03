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
ERROR_QUEUE_NAME = 'errors'
