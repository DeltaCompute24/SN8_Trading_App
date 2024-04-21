import json
import asyncio
import aiohttp
import websockets
from datetime import datetime
from .config import API_KEY, SIGNAL_API_KEY, SIGNAL_API_BASE_URL, FORECAST_API_URL
from .utils import colored, setup_logging
from .forecast_client import ForecastClient

logger = setup_logging()


class TradeMonitor:
    def __init__(self, args):
        self.setup_from_args(args)
        self.forecast_client = ForecastClient(FORECAST_API_URL)

    def setup_from_args(self, args):
        self.trade_pair = "BTCUSD" if args.autotrade else input("Enter the trade pair (e.g., BTCUSD): ")
        self.order_type = None if args.autotrade else input("Enter the order type (LONG/SHORT): ").upper()
        self.leverage = None if args.autotrade else float(input("Enter the leverage (0.001 to 200): "))
        self.asset_type = "crypto" if args.autotrade else input("Enter the asset type (forex, crypto): ").lower()
        self.summary_interval = args.summary_interval
        self.check_interval = args.check_interval
        self.take_profit_level = args.take_profit
        self.stop_loss_level = args.stop_loss
        self.test_mode = args.test_mode
        self.autotrade = args.autotrade
        self.websocket_url = f"wss://socket.polygon.io/{self.asset_type}"
        self.signal_api_url = SIGNAL_API_BASE_URL.format(id=args.trader_id)
        self.entry_price = None
        self.current_price = None
        self.trade_open_time = None
        self.is_trade_open = False
        self.last_summary_time = datetime.now()

    async def run(self):
        await self.connect_to_websocket()

    async def autotrade_forecast(self):
        predictions = await self.forecast_client.fetch_predictions()
        if predictions:
            self.analyze_forecast_for_trading(predictions)
            if not self.test_mode:
                await self.submit_trade()

    def analyze_forecast_for_trading(self, predictions):
        current_price = self.current_price   # Assuming the current price is the first prediction close price
        potential_trades = []

        # Calculate potential for LONG trade
        max_forecast = max(p['close'] for p in predictions)
        percent_increase = ((max_forecast - current_price) / current_price) * 100
        if percent_increase >= 2:  # Only consider trades that meet a minimum threshold
            long_leverage = self.calculate_dynamic_leverage(current_price, max_forecast)
            potential_trades.append(('LONG', max_forecast, long_leverage, percent_increase))

        # Calculate potential for SHORT trade
        min_forecast = min(p['close'] for p in predictions)
        percent_decrease = ((current_price - min_forecast) / current_price) * 100
        if percent_decrease >= 2:  # Only consider trades that meet a minimum threshold
            short_leverage = self.calculate_dynamic_leverage(current_price, min_forecast)
            potential_trades.append(('SHORT', min_forecast, short_leverage, percent_decrease))

        # Decide the best trade to take based on potential profit
        if potential_trades:
            # Sort trades based on the absolute potential percent change, descending order
            best_trade = max(potential_trades, key=lambda x: x[3])
            self.order_type, _, self.leverage, best_percent_change = best_trade
            self.entry_price = current_price
            self.is_trade_open = True
            logger.info(colored(f"Auto-trading setup: {self.order_type} at {self.entry_price} with leverage {self.leverage}x; Expected change: {best_percent_change:.2f}%", "green"))
            
    
    def calculate_dynamic_leverage(self, current_price, target_price):
        # Example calculation: This should be adapted to your risk management strategy
        price_change_percent = abs(target_price - current_price) / current_price
        risk_factor = 0.01  # Risk factor determines how aggressive the leverage should be (this is an example value)
        dynamic_leverage = min(100, max(1, price_change_percent / risk_factor * 100))  # Leverage capped between 1x and 100x
        return dynamic_leverage

    async def connect_to_websocket(self):
        logger.info(colored("Connecting to WebSocket...", "cyan"))
        async with websockets.connect(self.websocket_url) as websocket:
            await self.authenticate(websocket)
            await self.subscribe_to_pair(websocket)
            await self.monitor_trade(websocket)


    async def authenticate(self, websocket):
        await websocket.send(json.dumps({"action": "auth", "params": API_KEY}))
        response = await websocket.recv()
        logger.info(colored("Authenticated successfully", "green"))

    async def subscribe_to_pair(self, websocket):
        formatted_pair = self.format_pair(self.trade_pair)
        event_code = self.get_event_code()
        params = f"{event_code}.{formatted_pair}"
        await websocket.send(json.dumps({"action": "subscribe", "params": params}))
        response = await websocket.recv()
        logger.info(colored(f"Subscribed to {params}. Server response: {response}", "green"))

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

                    if self.autotrade:
                        await self.autotrade_forecast()

                    if self.entry_price is None :
                        self.entry_price = self.current_price

                    if self.leverage is not None and self.order_type is not None :
                        self.trade_open_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.is_trade_open = True
                        logger.info(colored(f"Trade opened at price: {self.entry_price}", "magenta"))

                        if (datetime.now() - self.last_summary_time).total_seconds() >= self.summary_interval:
                            self.log_summary()

                        await self.evaluate_trade_conditions()

                    if not self.is_trade_open:
                        break

                await asyncio.sleep(self.check_interval)
            except (websockets.exceptions.ConnectionClosed, json.JSONDecodeError):
                logger.error(colored("Connection closed unexpectedly. Reconnecting...", "red"))
                await self.connect_to_websocket()

    def log_summary(self):
        profit_loss_percent = self.calculate_profit_loss()
        profit_loss_value = self.calculate_absolute_profit_loss()
        fee = self.calculate_fee()

        profit_color = "green" if profit_loss_percent >= 0 else "red"
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
        logger.info("\n".join(summary_lines))
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
        return (0.00007 * self.leverage) if self.asset_type == 'forex' else (0.002 * self.leverage)

    async def evaluate_trade_conditions(self):
        profit_loss = self.calculate_profit_loss()
        if profit_loss >= self.take_profit_level or profit_loss <= -self.stop_loss_level:
            if not self.test_mode:
                await self.exit_trade()
            logger.info(colored(f"Exiting trade at {self.current_price} with profit/loss: {profit_loss:.2f}%", "magenta"))
            self.is_trade_open = False

    async def exit_trade(self):
        params = {
            "api_key": SIGNAL_API_KEY,
            "trade_pair": self.trade_pair,
            "order_type": "FLAT",
            "leverage": self.leverage
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.signal_api_url, json=params) as response:
                response_text = await response.text()
                logger.info(colored(f"Exit trade signal sent. Response: {response_text}", "green"))

    async def submit_trade(self):
        params = {
            "api_key": SIGNAL_API_KEY,
            "trade_pair": self.trade_pair,
            "order_type": self.order_type,
            "leverage": self.leverage
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.signal_api_url, json=params) as response:
                response_text = await response.text()
                logger.info(colored(f"Submit trade signal sent. Response: {response_text}", "green"))
