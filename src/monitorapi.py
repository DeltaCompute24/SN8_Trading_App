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
        # Directly assign arguments without input prompts
        self.trade_pair = args.get('trade_pair', 'BTCUSD')  # Default to 'BTCUSD' if not provided
        self.order_type = args.get('order_type', 'LONG').upper()
        self.leverage = args.get('leverage', 1.0)  # Default leverage if not provided
        self.asset_type = args.get('asset_type', 'crypto').lower()
        self.summary_interval = args.get('summary_interval', 1)
        self.check_interval = args.get('check_interval', 1)
        self.take_profit_level = args.get('take_profit', 0)
        self.stop_loss_level = args.get('stop_loss', 0)
        self.test_mode = args.get('test_mode', False)
        self.autotrade = args.get('autotrade', False)
        self.trader_id = args.get('trader_id', 'default_id')
        self.websocket_url = f"wss://socket.polygon.io/{self.asset_type}"
        self.signal_api_url = SIGNAL_API_BASE_URL.format(id= self.trader_id)
        self.entry_price = None
        self.current_price = None
        self.trade_open_time = None
        self.is_trade_open = False
        self.last_summary_time = datetime.now()


    async def run(self):
        await self.connect_to_websocket()
        logger.info("Starting trade monitor...")
        while True:
            if not self.is_trade_open and self.autotrade:
                trade_opportunity_found = await self.autotrade_forecast()
                if not trade_opportunity_found:
                    logger.info("No trade opportunities found. Waiting for 60 seconds before fetching new forecast...")
                    await asyncio.sleep(60)  # Wait for 60 seconds before fetching new forecast
            elif self.is_trade_open:
                await self.monitor_trade_conditions()

    async def autotrade_forecast(self):
        predictions = await self.forecast_client.fetch_predictions()
        trade_opportunity_found = False
        if predictions:
            trade_opportunity_found = self.analyze_forecast_for_trading(predictions)
            if trade_opportunity_found:
                if not self.test_mode:
                    await self.submit_trade()
        if not trade_opportunity_found:
            logger.info("No trade opportunities found. Waiting for 60 seconds before fetching new forecast...")
            await asyncio.sleep(60)  # Wait for 60 seconds before fetching new forecast
            self.should_wait = False
        return trade_opportunity_found


    async def connect_to_websocket(self):
        logger.info("Establishing WebSocket connection...")
        async with websockets.connect(self.websocket_url) as websocket:
            logger.info("WebSocket connection established.")
            logger.info("Authenticating user...")
            await self.authenticate(websocket)
            logger.info("User authenticated successfully.")
            logger.info("Subscribing to trade pair...")
            await self.subscribe_to_pair(websocket)
            logger.info("Trade pair subscription successful.")

    async def fetch_and_analyze_forecast(self):
        logger.info("Fetching forecast data...")
        predictions = await self.forecast_client.fetch_predictions()
        if predictions:
            logger.info("Forecast data fetched successfully. Analyzing for trade opportunities...")
            trade_opportunity_found = self.analyze_forecast_for_trading(predictions)
            if trade_opportunity_found:
                logger.info("Trade opportunity found. Opening trade...")
                if not self.test_mode:
                    await self.submit_trade()
                return True
            else:
                logger.info("No trade opportunities found in current forecast.")
        else:
            logger.warning("No forecast data available.")
        return False

    async def monitor_trade_conditions(self):
        while self.is_trade_open:
            await asyncio.sleep(self.check_interval)  # Check conditions at the interval
            # Implement trade condition checks such as profit-taking or stop-loss
            self.evaluate_trade_conditions()

    
    def analyze_forecast_for_trading(self, predictions):
        logger.debug("Analyzing forecast for trading opportunities...")
        current_price = self.current_price
        potential_trades = []
        # Analysis logic
        # Calculate potential trades based on the fetched predictions
        for prediction in predictions:
            close_price = prediction['close']
            percent_change = ((close_price - current_price) / current_price) * 100

            if abs(percent_change) >= 2:  # Considering trades above a threshold
                leverage = self.calculate_dynamic_leverage(current_price, close_price)
                trade_type = 'LONG' if percent_change > 0 else 'SHORT'
                potential_trades.append((trade_type, close_price, leverage, percent_change))

        # Selecting the best trade if any
        if potential_trades:
            best_trade = max(potential_trades, key=lambda x: abs(x[3]))
            self.order_type, self.entry_price, self.leverage, best_percent_change = best_trade
            self.is_trade_open = True
            self.trade_open_time = datetime.now()
            # Save trade parameters to a dictionary for consistent access
            self.trade_parameters = {
                'order_type': self.order_type,
                'entry_price': self.entry_price,
                'leverage': self.leverage,
                'open_time': self.trade_open_time
            }
            logger.info(f"Found trade opportunity: {self.trade_parameters}")
            return True
        logger.info("No trade opportunities found.")
        return False

    def calculate_dynamic_leverage(self, current_price, target_price):
        logger.debug("Calculating dynamic leverage...")
        # Example calculation: This should be adapted to your risk management strategy
        price_change_percent = abs(target_price - current_price) / current_price
        risk_factor = 0.05  # Risk factor determines how aggressive the leverage should be (this is an example value)
        dynamic_leverage = min(200, max(1, price_change_percent / risk_factor * 200))  # Leverage capped between 1x and 100x
        logger.debug(f"Calculated dynamic leverage: {dynamic_leverage}x")
        return dynamic_leverage

    async def authenticate(self, websocket):
        logger.info("Sending authentication request...")
        await websocket.send(json.dumps({"action": "auth", "params": API_KEY}))
        response = await websocket.recv()
        logger.info("Authentication successful.")

    async def subscribe_to_pair(self, websocket):
        logger.info("Sending subscription request for trade pair...")
        formatted_pair = self.format_pair(self.trade_pair)
        event_code = self.get_event_code()
        params = f"{event_code}.{formatted_pair}"
        await websocket.send(json.dumps({"action": "subscribe", "params": params}))
        response = await websocket.recv()
        logger.info(f"Subscription successful for {params}. Server response: {response}")

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

                    if self.autotrade and not self.is_trade_open:
                        await self.autotrade_forecast()

                    if self.entry_price is None :
                        self.entry_price = self.current_price
                        logger.info(colored(f"Trade opened at price: {self.entry_price}", "magenta"))

                    if self.leverage is not None and self.order_type is not None :
                        self.trade_open_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.is_trade_open = True

                        if (datetime.now() - self.last_summary_time).total_seconds() >= self.summary_interval:
                            self.log_summary()

                        await self.evaluate_trade_conditions()

                    if not self.is_trade_open:
                        break

                await asyncio.sleep(self.check_interval)
            except (websockets.exceptions.ConnectionClosed, json.JSONDecodeError):
                logger.error(colored("Connection closed unexpectedly. Reconnecting...", "red"))
                await self.connect_to_websocket()

    def log_summary(self, initial=False):
        if initial:
            logger.info(f"Trade setup: {self.trade_parameters['order_type']} at {self.trade_parameters['entry_price']} with leverage {self.trade_parameters['leverage']}x.")
        else:
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

    async def run(self):
        logger.info("Starting trade monitor...")
        await self.connect_to_websocket()
        while True:
            if not self.is_trade_open and self.autotrade:
                logger.info("Fetching and analyzing forecast...")
                await self.fetch_and_analyze_forecast()
            else:
                logger.info("Monitoring trade conditions...")
                await self.monitor_trade_conditions()

    async def connect_to_websocket(self):
        logger.info(colored("Connecting to WebSocket...", "cyan"))
        async with websockets.connect(self.websocket_url) as websocket:
            logger.info("Authenticating...")
            await self.authenticate(websocket)
            logger.info("Subscribing to pair...")
            await self.subscribe_to_pair(websocket)
            logger.info("Starting trade monitor...")
            await self.monitor_trade(websocket)

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
