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
import time

class SmartApiHandler:
    def __init__(self):
        self.live_data_q = queue.Queue()
        self.active_subscriptions = set()
        self.websocket_open_event = threading.Event()

        api_key = self.config['SMART_API']['API_KEY']
        self.client_code = self.config['SMART_API']['CLIENT_CODE']
        self.password = self.config['SMART_API']['MPIN']
        self.totp_token = self.config['SMART_API']['TOTP_TOKEN']

        if not all([self.api_key, self.client_code, self.password, self.totp_token]):
            raise ValueError("One or more SmartAPI environment variables are not set.")

        self.smartApi = SmartConnect(self.api_key)
        self.session = self._login()

        self.sws = None
        self._oi_cache = {}

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

    def get_historical_data(self, symbol, interval, from_date, to_date, expiry_dates=None):
        """
        Get historical candle data for a symbol or for option expiries.

        - `symbol`: underlying symbol name.
        - `interval`: e.g. '1minute', '5minute', '15minute', 'day' (as supported by SmartAPI).
        - `from_date`, `to_date`: either datetime.datetime or string in 'YYYY-MM-DD HH:MM' format.
        - `expiry_dates`: None (underlying) or a string/list of expiry date(s) to fetch option candles for.

        Returns:
          - If `expiry_dates` is None: the candle data for the underlying symbol (dict or API response).
          - If `expiry_dates` provided: dict keyed by expiry -> {'calls': {strike: data}, 'puts': {strike: data}}
        """
        def _fmt(dt):
            if isinstance(dt, datetime.datetime):
                return dt.strftime('%Y-%m-%d %H:%M')
            return str(dt)

        from_s = _fmt(from_date)
        to_s = _fmt(to_date)

        # If expiry_dates supplied, fetch option chain tokens and get candles per option
        if expiry_dates:
            if isinstance(expiry_dates, (str,)):
                expiry_list = [expiry_dates]
            else:
                expiry_list = list(expiry_dates)

            result = {}
            for exp in expiry_list:
                chain = self.get_option_chain(symbol, exp)
                if not chain:
                    result[exp] = None
                    continue
                # gather additional components: greeks, OI, PCR, max pain, IV percentile
                greeks_raw = self.get_option_greeks(symbol, exp)
                greeks_map = self._normalize_greeks(greeks_raw) if greeks_raw else {}
                oi_entries = self.get_option_oi(symbol, exp) or []
                # map strike -> oi entry
                oi_map = {e.get('strike'): e for e in oi_entries}
                pcr = self.get_put_call_ratio(symbol, exp)
                max_pain = self.get_max_pain(symbol, exp)
                iv_pct = self.get_iv_percentile(symbol, exp)

                result[exp] = {'calls': {}, 'puts': {}, 'greeks': greeks_map, 'oi_summary': oi_map, 'pcr': pcr, 'max_pain': max_pain, 'iv_percentile': iv_pct}

                for side in ('calls', 'puts'):
                    for opt in chain.get(side, []):
                        token = opt.get('token') or opt.get('symbol')
                        strike = opt.get('strike')
                        if not token:
                            continue
                        historic_param = {
                            'exchange': 'NSE',
                            'symboltoken': token,
                            'interval': interval,
                            'fromdate': from_s,
                            'todate': to_s
                        }
                        try:
                            data = self.get_candle_data(historic_param)
                        except Exception as e:
                            logger.exception(f'Failed to get candle data for {symbol} {exp} {strike}: {e}')
                            data = None

                        # attach greeks/oi/iv/volume where available
                        greeks_for_strike = greeks_map.get(str(strike)) or greeks_map.get(strike) or None
                        oi_for_strike = oi_map.get(strike)
                        entry = {
                            'token': token,
                            'strike': strike,
                            'side': side,
                            'candle': data,
                            'greeks': greeks_for_strike,
                            'oi': oi_for_strike.get('oi') if oi_for_strike else None,
                            'oi_change': oi_for_strike.get('change') if oi_for_strike else None,
                            'iv': (greeks_for_strike.get('impliedVolatility') if isinstance(greeks_for_strike, dict) and 'impliedVolatility' in greeks_for_strike else (oi_for_strike.get('iv') if oi_for_strike else None)),
                            'volume': oi_for_strike.get('volume') if oi_for_strike else None
                        }
                        result[exp][side][strike] = entry
            return result

        # No expiry_dates: return underlying historical candles
        token = self.get_symbol_token(symbol)
        if not token:
            logger.warning(f'No symbol token found for {symbol}')
            return None

        historic_param = {
            'exchange': 'NSE',
            'symboltoken': token,
            'interval': interval,
            'fromdate': from_s,
            'todate': to_s
        }
        try:
            return self.get_candle_data(historic_param)
        except Exception as e:
            logger.exception(f'Failed to get historical data for {symbol}: {e}')
            return None


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
        params = {
            "name": symbol,
            "expirydate": expiry_date
        }
        # Try several possible SmartApi client method names for OI data with retries
        candidates = [
            'getOIBreakdown',
            'getOiBreakdown',
            'getOIData',
            'oiBreakdown',
            'getOI',
            'get_oi_data',
            'getOIBreakdownData',
        ]

        cache_key = (symbol, expiry_date)
        max_attempts = 3
        backoff = 1.0

        for attempt in range(1, max_attempts + 1):
            for method_name in candidates:
                try:
                    method = getattr(self.smartApi, method_name, None)
                    if callable(method):
                        oi_data = method(params)
                        # Some SmartAPI responses use {'status': False, 'errorcode': 'AB1004', ...}
                        if isinstance(oi_data, dict) and oi_data.get('status') is False:
                            err = oi_data.get('errorcode') or oi_data.get('error') or oi_data.get('message')
                            logger.warning(f"get_oi_data attempt {attempt} method {method_name} returned error: {err}")
                            # If recoverable server-side error, retry after backoff
                            if oi_data.get('errorcode') == 'AB1004' or 'Something Went Wrong' in str(oi_data.get('message', '')):
                                time.sleep(backoff)
                                backoff *= 2
                                continue
                            # non-recoverable: skip this method
                            continue
                        # success-ish response; cache and return
                        try:
                            self._oi_cache[cache_key] = {'ts': time.time(), 'data': oi_data}
                        except Exception:
                            pass
                        return oi_data
                except Exception as e:
                    logger.debug(f"SmartAPI method {method_name} raised: {e}")

            # try optionChain as a fallback between attempts
            try:
                if hasattr(self.smartApi, 'optionChain'):
                    oi_data = self.smartApi.optionChain(params)
                    if oi_data:
                        self._oi_cache[cache_key] = {'ts': time.time(), 'data': oi_data}
                        return oi_data
            except Exception as e:
                logger.debug(f"optionChain attempt failed: {e}")

            # If not last attempt, wait and retry
            if attempt < max_attempts:
                time.sleep(backoff)
                backoff *= 2

        # All attempts failed: return cached data if recent (<= 10 minutes)
        cached = self._oi_cache.get(cache_key)
        if cached and (time.time() - cached.get('ts', 0) <= 600):
            logger.info('Returning cached OI data after failed attempts')
            return cached.get('data')

        logger.warning('Failed to get OI data after retries and no cache available')
        return None

    def _normalize_oi(self, raw):
        """
        Normalize various SmartAPI OI response shapes into a list of entries:
        Each entry: {'strike': float, 'type': 'CE'|'PE'|'FUT', 'oi': int, 'change': float, 'iv': float (optional), 'volume': int (optional)}
        """
        entries = []
        # If raw is a mapping with 'data' or 'result' containing list
        if isinstance(raw, dict):
            # Common nests
            for key in ('data', 'result', 'records', 'oi', 'openinterest'):
                if key in raw and isinstance(raw[key], (list, dict)):
                    raw = raw[key]
                    break

        # If now a dict keyed by strike (or nested CE/PE), handle patterns
        if isinstance(raw, dict):
            # pattern: { '12300': {'CE': {...}, 'PE': {...}}, ... }
            for strike_key, v in raw.items():
                try:
                    strike = float(strike_key)
                except Exception:
                    continue
                if isinstance(v, dict):
                    if 'CE' in v or 'PE' in v:
                        for opt_type in ('CE', 'PE'):
                            if opt_type in v and isinstance(v[opt_type], dict):
                                o = v[opt_type]
                                entries.append({
                                    'strike': strike,
                                    'type': opt_type,
                                    'oi': int(o.get('openInterest', o.get('oi', o.get('open_interest', 0)) or 0)),
                                    'change': float(o.get('changeinOpenInterest', o.get('oi_change', o.get('change', 0)) or 0)),
                                    'iv': float(o.get('impliedVolatility', o.get('iv', 0) or 0)),
                                    'volume': int(o.get('totalTradedVolume', o.get('volume', 0) or 0))
                                })
                    else:
                        # maybe a single option dict
                        entries.append({
                            'strike': strike,
                            'type': v.get('optiontype') or v.get('type') or 'OPT',
                            'oi': int(v.get('openInterest', v.get('oi', 0) or 0)),
                            'change': float(v.get('changeinOpenInterest', v.get('oi_change', 0) or 0)),
                            'iv': float(v.get('impliedVolatility', v.get('iv', 0) or 0)),
                            'volume': int(v.get('totalTradedVolume', v.get('volume', 0) or 0))
                        })
        elif isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                # try many common key names
                strike = None
                for k in ('strikePrice', 'strike', 'strike_price'):
                    if k in item:
                        try:
                            strike = float(item.get(k))
                        except Exception:
                            strike = None
                        break
                typ = item.get('optiontype') or item.get('type') or item.get('instrumentType') or item.get('optType')
                if typ is None:
                    # futures may have 'instrumenttype' or 'instrumentType'
                    typ = 'FUT' if item.get('instrumenttype', '').upper().startswith('FUT') else 'OPT'
                oi = int(item.get('openInterest', item.get('oi', 0) or 0))
                change = float(item.get('changeinOpenInterest', item.get('oi_change', item.get('change', 0) or 0)))
                iv = float(item.get('impliedVolatility', item.get('iv', 0) or 0))
                vol = int(item.get('totalTradedVolume', item.get('volume', 0) or 0))
                if strike is None:
                    # skip entries without strike unless FUT
                    if typ and typ.upper().startswith('F'):
                        entries.append({'strike': None, 'type': 'FUT', 'oi': oi, 'change': change, 'iv': iv, 'volume': vol})
                else:
                    entries.append({'strike': strike, 'type': 'CE' if str(typ).upper().startswith('C') else ('PE' if str(typ).upper().startswith('P') else typ), 'oi': oi, 'change': change, 'iv': iv, 'volume': vol})

        return entries

    def get_option_oi(self, symbol, expiry_date):
        """Return option open interest entries for symbol+expiry."""
        oi_raw = self.get_oi_data(symbol, expiry_date)
        if not oi_raw:
            return None
        entries = self._normalize_oi(oi_raw)
        # filter only CE and PE
        return [e for e in entries if e.get('type') in ('CE', 'PE')]

    def get_option_oi_change(self, symbol, expiry_date):
        """Return per-strike OI change and total change for options."""
        entries = self.get_option_oi(symbol, expiry_date)
        if entries is None:
            return None
        total_change = sum(e.get('change', 0) for e in entries)
        by_strike = {}
        for e in entries:
            s = e.get('strike')
            if s not in by_strike:
                by_strike[s] = {'call_change': 0, 'put_change': 0}
            if e.get('type') == 'CE':
                by_strike[s]['call_change'] += e.get('change', 0)
            else:
                by_strike[s]['put_change'] += e.get('change', 0)
        return {'total_change': total_change, 'by_strike': by_strike}

    def get_put_call_ratio(self, symbol, expiry_date):
        """Compute PCR = sum(Puts OI) / sum(Calls OI) for given expiry."""
        entries = self.get_option_oi(symbol, expiry_date)
        if entries is None:
            return None
        calls = sum(e.get('oi', 0) for e in entries if e.get('type') == 'CE')
        puts = sum(e.get('oi', 0) for e in entries if e.get('type') == 'PE')
        if calls == 0:
            return None
        return puts / calls

    def get_max_pain(self, symbol, expiry_date):
        """Estimate max pain strike from option OI: minimize payoff-weighted OI.
        Uses current underlying LTP when available.
        """
        entries = self.get_option_oi(symbol, expiry_date)
        if not entries:
            return None
        # gather strikes
        strikes = sorted({e['strike'] for e in entries if e.get('strike') is not None})
        if not strikes:
            return None
        # current underlying price
        token = self.get_symbol_token(symbol)
        underlying_price = None
        try:
            underlying_price = float(self.get_ltp('NSE', token) or 0)
        except Exception:
            underlying_price = None

        # build call and put oi maps
        call_oi = {s: 0 for s in strikes}
        put_oi = {s: 0 for s in strikes}
        for e in entries:
            s = e.get('strike')
            if s not in call_oi:
                continue
            if e.get('type') == 'CE':
                call_oi[s] += e.get('oi', 0)
            else:
                put_oi[s] += e.get('oi', 0)

        # for each candidate strike, compute pain = sum(call_oi * max(0, strike - k)) + sum(put_oi * max(0, k - strike))
        pains = {}
        for k in strikes:
            pain = 0
            for s in strikes:
                c_oi = call_oi.get(s, 0)
                p_oi = put_oi.get(s, 0)
                # call payoff if underlying at k: max(0, s - k)
                pain += c_oi * max(0, s - k)
                # put payoff: max(0, k - s)
                pain += p_oi * max(0, k - s)
            pains[k] = pain

        # pick strike with minimal pain
        max_pain_strike = min(pains, key=lambda x: pains[x])
        return {'max_pain': max_pain_strike, 'pains': pains, 'underlying': underlying_price}

    def get_futures_oi(self, symbol):
        """Return futures OI for the underlying symbol (all expiries aggregated)."""
        # Try to call possible futures OI endpoints
        params = {"name": symbol}
        candidates = ['futOpenInterest', 'getFuturesOI', 'getFuturesOpenInterest', 'getFutOI', 'futuresOi', 'getOIForFutures']
        for method_name in candidates:
            method = getattr(self.smartApi, method_name, None)
            try:
                if callable(method):
                    res = method(params)
                    if res:
                        entries = self._normalize_oi(res)
                        # return futures entries
                        return [e for e in entries if e.get('type') in ('FUT', 'F') or e.get('strike') is None]
            except Exception:
                continue
        # fallback to get_oi_data with no expiry
        try:
            raw = self.get_oi_data(symbol, '')
            if raw:
                entries = self._normalize_oi(raw)
                return [e for e in entries if e.get('type') in ('FUT', 'F') or e.get('strike') is None]
        except Exception:
            pass
        return None

    def get_futures_oi_change(self, symbol):
        """Aggregate futures OI change (total and per-contract)."""
        entries = self.get_futures_oi(symbol)
        if entries is None:
            return None
        total_change = sum(e.get('change', 0) for e in entries)
        return {'total_change': total_change, 'entries': entries}

    def get_option_iv(self, symbol, expiry_date):
        """Return implied volatility per-strike for options."""
        entries = self.get_option_oi(symbol, expiry_date)
        if entries is None:
            return None
        iv_map = {}
        for e in entries:
            s = e.get('strike')
            if s not in iv_map:
                iv_map[s] = {'call_iv': None, 'put_iv': None}
            if e.get('type') == 'CE':
                iv_map[s]['call_iv'] = e.get('iv')
            else:
                iv_map[s]['put_iv'] = e.get('iv')
        return iv_map

    def get_indiavix(self):
        """Return India VIX value from SmartAPI if available, otherwise None."""
        candidates = ['indiaVIX', 'getIndiaVix', 'getINDIAVIX', 'getIndiaVIX']
        for method_name in candidates:
            method = getattr(self.smartApi, method_name, None)
            try:
                if callable(method):
                    res = method()
                    if res:
                        # try to extract a numeric vix
                        if isinstance(res, dict):
                            for k in ('vix', 'value', 'indiavix', 'IndiaVIX'):
                                if k in res:
                                    try:
                                        return float(res[k])
                                    except Exception:
                                        continue
                        try:
                            return float(res)
                        except Exception:
                            continue
            except Exception:
                continue
        # fallback: try to fetch via option greeks on NIFTY if available
        try:
            g = self.get_option_greeks('NIFTY', '')
            if g and isinstance(g, dict):
                for k in ('volatility', 'vix'):
                    if k in g:
                        try:
                            return float(g[k])
                        except Exception:
                            continue
        except Exception:
            pass
        return None

    def get_iv_percentile(self, symbol, expiry_date, lookback_days=252):
        """Estimate IV percentile by comparing current IVs to historical (best-effort via option greeks/candles).
        NOTE: SmartAPI may not provide historical IV series; this returns None if not available.
        """
        # try to get current indiavix or average option IV
        iv_map = self.get_option_iv(symbol, expiry_date)
        if not iv_map:
            return None
        # compute current median IV across strikes (calls+puts)
        ivs = []
        for s, v in iv_map.items():
            if v.get('call_iv'):
                ivs.append(v.get('call_iv'))
            if v.get('put_iv'):
                ivs.append(v.get('put_iv'))
        if not ivs:
            return None
        current_iv = sum(ivs) / len(ivs)
        # Without historical IV series, we cannot compute percentile reliably
        return {'current_iv': current_iv, 'percentile': None}

    def get_futures_volume(self, symbol):
        """Return recent futures volume (per-contract) if SmartAPI exposes it."""
        # Try candidate method names
        candidates = ['futuresVolume', 'getFuturesVolume', 'getFutVolume', 'getFuturesStats']
        params = {"name": symbol}
        for method_name in candidates:
            method = getattr(self.smartApi, method_name, None)
            try:
                if callable(method):
                    res = method(params) if method.__code__.co_argcount > 1 else method()
                    if res:
                        # normalize
                        entries = self._normalize_oi(res)
                        # keep those with volume
                        vols = [e for e in entries if e.get('volume')]
                        return {'entries': vols}
            except Exception:
                continue
        # fallback: attempt futures OI entries which may include volume
        futs = self.get_futures_oi(symbol)
        if futs:
            return {'entries': [e for e in futs if e.get('volume')]} 
        return None
