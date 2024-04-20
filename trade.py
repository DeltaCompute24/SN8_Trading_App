import asyncio
import aiohttp
import json
import os
import websockets
import argparse
import logging
from datetime import datetime
from dotenv import load_dotenv
from termcolor import colored
from colorama import init

# Initialize colorama for colored terminal output
init()

# Load environment variables
load_dotenv()

API_KEY = os.getenv('POLYGON_API_KEY')
SIGNAL_API_KEY = os.getenv('SIGNAL_API_KEY')
SIGNAL_API_BASE_URL = os.getenv('SIGNAL_API_BASE_URL')
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class TradeMonitor:
    def __init__(self, args):
        self.trade_pair = input("Enter the trade pair (e.g., BTCUSD): ")
        self.order_type = input("Enter the order type (LONG/SHORT): ").upper()
        self.leverage = float(input("Enter the leverage (0.001 to 200): "))
        self.asset_type = input("Enter the asset type (forex, crypto): ").lower()
        self.summary_interval = args.summary_interval
        self.check_interval = args.check_interval
        self.take_profit_level = args.take_profit
        self.stop_loss_level = args.stop_loss
        self.test_mode = args.test_mode
        self.entry_price = None
        self.current_price = None
        self.trade_open_time = None  # Store the time when trade is opened
        self.last_summary_time = datetime.now()  # Correctly initialize last_summary_time
        self.websocket_url = f"wss://socket.polygon.io/{self.asset_type}"
        self.is_trade_open = False
        self.trader_id = args.trader_id
        self.signal_api_url = SIGNAL_API_BASE_URL.format(id=self.trader_id)

    async def connect_to_websocket(self):
        logging.info(colored("Connecting to WebSocket...", "cyan"))
        async with websockets.connect(self.websocket_url) as websocket:
            await self.authenticate(websocket)
            await self.subscribe_to_pair(websocket)
            await self.monitor_trade(websocket)

    async def authenticate(self, websocket):
        await websocket.send(json.dumps({"action": "auth", "params": API_KEY}))
        response = await websocket.recv()
        logging.info(colored("Authenticated successfully", "green"))

    async def subscribe_to_pair(self, websocket):
        formatted_pair = self.format_pair(self.trade_pair)
        event_code = self.get_event_code()
        params = f"{event_code}.{formatted_pair}"
        await websocket.send(json.dumps({"action": "subscribe", "params": params}))
        response = await websocket.recv()
        logging.info(colored(f"Subscribed to {params}. Server response: {response}", "green"))

    def get_event_code(self):
        return "CAS" if self.asset_type == "forex" else "XAS"

    def format_pair(self, pair):
        separator = '/' if self.asset_type == "forex" else '-'
        base = pair[:-3]
        quote = pair[-3:]
        return f"{base}{separator}{quote}"

    async def monitor_trade(self, websocket):
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                event_code = self.get_event_code()

                if isinstance(data, list) and data[0].get('ev') == event_code:
                    self.current_price = float(data[0]['c'])
                    if self.entry_price is None:
                        self.entry_price = self.current_price
                        self.trade_open_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Capture the exact time trade was opened
                        self.is_trade_open = True
                        logging.info(colored(f"Trade opened at price: {self.entry_price}", "magenta"))

                    if (datetime.now() - self.last_summary_time).total_seconds() >= self.summary_interval:
                        self.log_summary()

                    await self.evaluate_trade_conditions()

                    if not self.is_trade_open:
                        break

                await asyncio.sleep(self.check_interval)
            except (websockets.exceptions.ConnectionClosed, json.JSONDecodeError):
                logging.error(colored("Connection closed unexpectedly. Reconnecting...", "red"))
                await self.connect_to_websocket()

    def log_summary(self):
        profit_loss_percent = self.calculate_profit_loss()
        profit_loss_value = self.calculate_absolute_profit_loss()
        fee = self.calculate_fee()

        # Color settings for profit/loss
        profit_color = "green" if profit_loss_percent >= 0 else "red"

        # Construct the summary layout
        summary_lines = [
            colored("============= Trade Summary =============", "cyan", attrs=['bold']),
            colored(f"Trade Open Time : {self.trade_open_time}", "yellow"),
            colored(f"Trade Pair      : {self.trade_pair}", "yellow"),
            colored(f"Asset Type      : {self.asset_type.capitalize()}", "yellow"),
            colored(f"Order Type      : {self.order_type}", "magenta"),
            colored(f"Leverage        : {self.leverage:.2f}x", "magenta"),
            colored(f"Entry Price     : {self.entry_price:.2f}", "blue"),
            colored(f"Current Price   : {self.current_price:.2f}", "blue"),
            colored(f"Profit/Loss     : {profit_loss_percent:.2f}% ({profit_loss_value:.2f})", profit_color),
            colored(f"Fee Deducted    : {fee:.6f}", "red"),
            colored(f"Take Profit     : {self.take_profit_level:.2f}%", "green"),
            colored(f"Stop Loss       : {self.stop_loss_level:.2f}%", "red"),
            colored("========================================", "cyan", attrs=['bold'])
        ]

        logging.info("\n".join(summary_lines))
        self.last_summary_time = datetime.now()

    def calculate_profit_loss(self):
        fee = self.calculate_fee()
        if self.order_type == "LONG":
            price_difference = (self.current_price - self.entry_price) * self.leverage
        elif self.order_type == "SHORT":
            price_difference = (self.entry_price - self.current_price) * self.leverage
        net_profit = price_difference - fee
        profit_loss_percent = (net_profit / (self.entry_price * self.leverage)) * 100
        return profit_loss_percent

    def calculate_absolute_profit_loss(self):
        fee = self.calculate_fee()
        if self.order_type == "LONG":
            price_difference = (self.current_price - self.entry_price) * self.leverage
        elif self.order_type == "SHORT":
            price_difference = (self.entry_price - self.current_price) * self.leverage
        net_profit = price_difference - fee
        return net_profit

    def calculate_fee(self):
        """ Calculate the trading fee based on asset type and leverage """
        return (0.00007 * self.leverage) if self.asset_type == 'forex' else (0.002 * self.leverage)

    async def evaluate_trade_conditions(self):
        profit_loss = self.calculate_profit_loss()
        if profit_loss >= self.take_profit_level or profit_loss <= -self.stop_loss_level:
            if not self.test_mode:
                await self.exit_trade()
            logging.info(colored(f"Exiting trade at {self.current_price} with profit/loss: {profit_loss:.2f}%", "magenta"))
            self.is_trade_open = False

    async def exit_trade(self):
        params = {
            "api_key": SIGNAL_API_KEY,
            "trade_pair": self.trade_pair,
            "order_type": "FLAT",
            "leverage": str(self.leverage)
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(SIGNAL_API_BASE_URL, json=params) as response:
                response_text = await response.text()
                logging.info(colored(f"Exit trade signal sent. Response: {response_text}", "green"))


def parse_arguments():
    parser = argparse.ArgumentParser(description='Trade Monitor CLI')
    parser.add_argument('--summary_interval', type=int, default=60, help='Summary log interval in seconds')
    parser.add_argument('--check_interval', type=int, default=5, help='Price check interval in seconds')
    parser.add_argument('--take_profit', type=float, default=2.0, help='Take profit level in percentage')
    parser.add_argument('--stop_loss', type=float, default=9.5, help='Stop loss level in percentage')
    parser.add_argument('--test_mode', action='store_true', help='Enable test mode to simulate trades')
    parser.add_argument('--trader_id', type=int, required=True, help='Trader ID to construct the SIGNAL API URL')
    return parser.parse_args()

def main():
    args = parse_arguments()
    monitor = TradeMonitor(args)
    asyncio.run(monitor.connect_to_websocket())

if __name__ == "__main__":
    main()
