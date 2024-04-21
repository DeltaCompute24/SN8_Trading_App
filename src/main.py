import argparse
import asyncio
from .monitor import TradeMonitor

def parse_arguments():
    parser = argparse.ArgumentParser(description="Trade Monitor CLI")
    parser.add_argument('--summary_interval', type=int, default=60, help='Summary log interval in seconds')
    parser.add_argument('--check_interval', type=int, default=5, help='Price check interval in seconds')
    parser.add_argument('--take_profit', type=float, default=2.0, help='Take profit level in percentage')
    parser.add_argument('--stop_loss', type=float, default=9.5, help='Stop loss level in percentage')
    parser.add_argument('--test_mode', action='store_true', help='Enable test mode to simulate trades')
    parser.add_argument('--trader_id', type=int, required=True, help='Trader ID to construct the SIGNAL API URL')
    parser.add_argument('--autotrade', action='store_true', help='Enable auto-trading mode based on forecasts')
    return parser.parse_args()

def main():
    args = parse_arguments()
    monitor = TradeMonitor(args)
    asyncio.run(monitor.run())

if __name__ == "__main__":
    main()