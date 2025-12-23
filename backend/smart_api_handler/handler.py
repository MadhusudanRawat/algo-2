import os
import configparser
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
import pyotp
from logzero import logger
import requests
import json
import queue
import datetime
import threading

class SmartApiHandler:
    def __init__(self):
        self.live_data_q = queue.Queue()
        self.active_subscriptions = set()
        self.websocket_open_event = threading.Event()

        # Read credentials from environment variables
        self.api_key = os.getenv("SMART_API_KEY")
        self.client_code = os.getenv("SMART_API_CLIENT_CODE")
        self.password = os.getenv("SMART_API_PASSWORD")
        self.totp_token = os.getenv("SMART_API_TOTP_TOKEN")

        if not all([self.api_key, self.client_code, self.password, self.totp_token]):
            raise ValueError("One or more SmartAPI environment variables are not set.")

        self.smartApi = SmartConnect(self.api_key)
        self.session = self._login()

        self.sws = None
        self.websocket_thread = None

    def _login(self):
        try:
            token = self.totp_token
            totp = pyotp.TOTP(token).now()
        except Exception as e:
            logger.error(f"Invalid Token: The provided token is not valid. {e}")
            raise e

        data = self.smartApi.generateSession(self.client_code, self.password, totp)

        if not data.get('status'):
            logger.error(data)
            return None
        else:
            self.authToken = data['data']['jwtToken']
            self.refreshToken = data['data']['refreshToken']
            self.feedToken = self.smartApi.getfeedToken()
            logger.info("Login successful.")
            return data['data']

    # ... (the rest of the file is the same, but I will include it for completeness)
    def _fetch_scrips(self):
        if self._scrips is None or (datetime.datetime.now() - self._scrips_cache_time) > datetime.timedelta(hours=1):
            try:
                url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
                response = requests.get(url)
                response.raise_for_status()
                self._scrips = response.json()
                self._scrips_cache_time = datetime.datetime.now()
                logger.info("Scrip master file fetched and cached.")
            except Exception as e:
                logger.error(f"Failed to fetch or parse scrip master: {e}")
                return None
        return self._scrips

    def start_websocket(self):
        if self.sws and self.websocket_thread and self.websocket_thread.is_alive():
            logger.info("WebSocket is already running.")
            return

        self.sws = SmartWebSocketV2(self.authToken, self.api_key, self.client_code, self.feedToken)

        def on_data(wsapp, message):
            self.live_data_q.put(message)

        def on_open(wsapp):
            logger.info("WebSocket connection opened.")
            self.websocket_open_event.set() # Signal that the connection is open

        def on_error(wsapp, error):
            logger.error(f"WebSocket error: {error}")

        def on_close(wsapp):
            logger.info("WebSocket connection closed.")

        self.sws.on_open = on_open
        self.sws.on_data = on_data
        self.sws.on_error = on_error
        self.sws.on_close = on_close

        # Run WebSocket in a separate thread to avoid blocking
        self.websocket_thread = threading.Thread(target=self.sws.connect)
        self.websocket_thread.daemon = True
        self.websocket_thread.start()
        logger.info("WebSocket connection thread started.")

    def subscribe_to_symbols(self, symbol_tokens):
        # Wait for the WebSocket to be open before subscribing
        is_open = self.websocket_open_event.wait(timeout=5) # 5-second timeout
        if not is_open:
            logger.error("WebSocket connection did not open in time. Cannot subscribe.")
            return

        new_tokens_to_subscribe = [token for token in symbol_tokens if token not in self.active_subscriptions]

        if not new_tokens_to_subscribe:
            logger.info("All requested symbols are already subscribed.")
            return

        correlation_id = "abc123" # A unique ID for the subscription
        mode = 1 # 1 for LTP
        token_list = [{"exchangeType": 2, "tokens": new_tokens_to_subscribe}] # 2 for NFO

        self.sws.subscribe(correlation_id, mode, token_list)
        self.active_subscriptions.update(new_tokens_to_subscribe)
        logger.info(f"Subscribed to {len(new_tokens_to_subscribe)} new symbols.")

    def get_websocket_message(self):
        try:
            return self.live_data_q.get(block=False)
        except queue.Empty:
            return None

    def get_option_chain(self, symbol, expiry_date):
        """
        Constructs the option chain with static data and returns a list of tokens
        to be used for WebSocket subscription.
        """
        scrips = self._fetch_scrips()
        if not scrips:
            return None, []

        oi_data = self.get_oi_data(symbol, expiry_date)
        greeks_data = self.get_option_greeks(symbol, expiry_date)

        oi_lookup = {item['strikePrice']: item.get('totalOpenInterest', 0) for item in oi_data.get('data', [])} if oi_data and oi_data.get('status') else {}
        iv_lookup = {item['strikePrice']: item.get('impliedVolatility', 0) for item in greeks_data.get('data', [])} if greeks_data and greeks_data.get('status') else {}

        option_chain = {'calls': [], 'puts': []}
        tokens = []
        expiry_date_str = expiry_date.upper()

        for scrip in scrips:
            if scrip.get('instrumenttype') == 'OPTIDX' and scrip.get('name') == symbol and scrip.get('expiry', '').upper() == expiry_date_str:
                try:
                    strike_price = float(scrip.get('strike'))
                    token = scrip.get('token')
                    if not token: continue
                except (ValueError, TypeError):
                    continue

                tokens.append(token)
                option_details = {
                    'symbol': scrip.get('symbol'),
                    'token': token,
                    'strike': strike_price,
                    'type': 'call' if scrip.get('optiontype') == 'CE' else 'put',
                    'ltp': 0, # LTP will be updated by the WebSocket feed
                    'oi': oi_lookup.get(strike_price, 0),
                    'iv': iv_lookup.get(strike_price, 0),
                }

                if scrip.get('optiontype') == 'CE':
                    option_chain['calls'].append(option_details)
                elif scrip.get('optiontype') == 'PE':
                    option_chain['puts'].append(option_details)

        return option_chain, tokens

    def get_option_greeks(self, symbol, expiry_date):
        try:
            params = {"name": symbol, "expirydate": expiry_date}
            return self.smartApi.optionGreek(params)
        except Exception as e:
            logger.exception(f"Failed to get option greeks: {e}")
            return None

    def get_oi_data(self, symbol, expiry_date):
        try:
            params = {"name": symbol, "expirydate": expiry_date}
            return self.smartApi.getOIBreakdown(params)
        except Exception as e:
            logger.exception(f"Failed to get OI data: {e}")
            return None

    def get_candle_data(self, historic_param):
        try:
            return self.smartApi.getCandleData(historic_param)
        except Exception as e:
            logger.exception(f"Failed to get candle data: {e}")
            return None

    def get_todays_historical_data(self, symbol, interval):
        symbol_token = self.get_symbol_token(symbol)
        if not symbol_token:
            return None

        to_date = datetime.datetime.now()
        from_date = to_date.replace(hour=9, minute=15, second=0, microsecond=0)

        historic_param = {
            "exchange": "NSE",
            "symboltoken": symbol_token,
            "interval": interval,
            "fromdate": from_date.strftime('%Y-%m-%d %H:%M'),
            "todate": to_date.strftime('%Y-%m-%d %H:%M')
        }
        return self.get_candle_data(historic_param)


    def place_order(self, order_params):
        try:
            orderid = self.smartApi.placeOrder(order_params)
            logger.info(f"PlaceOrder : {orderid}")
            return orderid
        except Exception as e:
            logger.exception(f"Order placement failed: {e}")
            return None

    def get_symbol_token(self, symbol):
        scrips = self._fetch_scrips()
        if not scrips:
            return None

        for scrip in scrips:
            if scrip.get('name') == symbol and scrip.get('instrumenttype') == 'AMXIDX':
                return scrip.get('token')
        return None

    def get_ltp(self, exchange, symbol_token):
        try:
            ltp_data = self.smartApi.ltpData(exchange, " ", symbol_token)
            return ltp_data['data']['ltp']
        except Exception as e:
            logger.exception(f"Failed to get LTP data: {e}")
            return None

    def cancel_order(self, order_id, variety):
        try:
            self.smartApi.cancelOrder(order_id, variety)
            logger.info(f"Canceled order: {order_id}")
        except Exception as e:
            logger.exception(f"Failed to cancel order: {e}")

    def get_order_book(self):
        try:
            return self.smartApi.orderBook()
        except Exception as e:
            logger.exception(f"Failed to get order book: {e}")
            return None
