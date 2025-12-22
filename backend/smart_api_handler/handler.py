import configparser
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
import pyotp
from logzero import logger
import requests
import json
import queue
import datetime

class SmartApiHandler:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self._scrips = None
        self._scrips_cache_time = None
        self.live_data_q = queue.Queue()

        api_key = self.config['SMART_API']['API_KEY']
        self.client_code = self.config['SMART_API']['CLIENT_CODE']
        self.password = self.config['SMART_API']['PASSWORD']
        self.totp_token = self.config['SMART_API']['TOTP_TOKEN']

        self.smartApi = SmartConnect(api_key)
        self.session = self._login()

        self.sws = None

    def _login(self):
        try:
            token = self.totp_token
            totp = pyotp.TOTP(token).now()
        except Exception as e:
            logger.error(f"Invalid Token: The provided token is not valid. {e}")
            raise e

        data = self.smartApi.generateSession(self.client_code, self.password, totp)

        if not data['status']:
            logger.error(data)
            return None
        else:
            self.authToken = data['data']['jwtToken']
            self.refreshToken = data['data']['refreshToken']
            self.feedToken = self.smartApi.getfeedToken()
            return data['data']

    def _fetch_scrips(self):
        if self._scrips is None or (datetime.datetime.now() - self._scrips_cache_time) > datetime.timedelta(hours=1):
            try:
                url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
                response = requests.get(url)
                self._scrips = response.json()
                self._scrips_cache_time = datetime.datetime.now()
            except Exception as e:
                logger.error(f"Failed to fetch or parse scrip master: {e}")
                return None
        return self._scrips

    def start_websocket(self):
        self.sws = SmartWebSocketV2(self.authToken, self.config['SMART_API']['API_KEY'], self.client_code, self.feedToken)

        def on_data(wsapp, message):
            self.live_data_q.put(message)

        def on_open(wsapp):
            logger.info("Websocket on open")

        def on_error(wsapp, error):
            logger.error(error)

        def on_close(wsapp):
            logger.info("Websocket on close")

        self.sws.on_open = on_open
        self.sws.on_data = on_data
        self.sws.on_error = on_error
        self.sws.on_close = on_close

        self.sws.connect()

    def subscribe_to_symbols(self, symbol_tokens):
        if self.sws:
            correlation_id = "abc123"
            mode = 1
            token_list = [
                {
                    "exchangeType": 1,
                    "tokens": symbol_tokens
                }
            ]
            self.sws.subscribe(correlation_id, mode, token_list)

    def get_websocket_message(self):
        """
        Gets a message from the websocket queue.
        """
        try:
            return self.live_data_q.get(block=False)
        except queue.Empty:
            return None

    def get_option_chain(self, symbol, expiry_date):
        """
        Constructs the option chain for a given symbol and expiry date.
        """
        scrips = self._fetch_scrips()
        if not scrips:
            return None

        option_chain = {'calls': [], 'puts': []}
        expiry_date_str = expiry_date.upper()

        for scrip in scrips:
            if scrip.get('instrumenttype') == 'OPTIDX' and scrip.get('name') == symbol and scrip.get('expiry').upper() == expiry_date_str:
                option_details = {
                    'symbol': scrip.get('symbol'),
                    'token': scrip.get('token'),
                    'strike': scrip.get('strike'),
                    'type': 'call' if scrip.get('optiontype') == 'CE' else 'put'
                }
                if scrip.get('optiontype') == 'CE':
                    option_chain['calls'].append(option_details)
                elif scrip.get('optiontype') == 'PE':
                    option_chain['puts'].append(option_details)

        return option_chain


    def get_option_greeks(self, symbol, expiry_date):
        try:
            params = {
                "name": symbol,
                "expirydate": expiry_date
            }
            greeks = self.smartApi.optionGreek(params)
            return greeks
        except Exception as e:
            logger.exception(f"Failed to get option greeks: {e}")
            return None

    def get_candle_data(self, historic_param):
        try:
            return self.smartApi.getCandleData(historic_param)
        except Exception as e:
            logger.exception(f"Failed to get candle data: {e}")
            return None

    def get_todays_historical_data(self, symbol, interval):
        """
        Gets today's historical data for a given symbol and interval.
        """
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

    def get_oi_data(self, symbol, expiry_date):
        """
        Fetches Open Interest data for a given symbol and expiry date.
        """
        try:
            params = {
                "name": symbol,
                "expirydate": expiry_date
            }
            oi_data = self.smartApi.getOIBreakdown(params)
            return oi_data
        except Exception as e:
            logger.exception(f"Failed to get OI data: {e}")
            return None
