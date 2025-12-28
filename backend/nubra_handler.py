import os
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData
from dotenv import load_dotenv

load_dotenv()

class NubraHandler:
    def __init__(self):
        self.sdk_initialized = False
        try:
            # Check for necessary environment variables before initializing
            if all(os.getenv(key) for key in ["PHONE_NO", "PASSWORD", "API_KEY", "API_SECRET", "MPIN"]):
                self.nubra = InitNubraSdk(NubraEnv.UAT, totp_login=True, env_creds=True)
                self.market_data = MarketData(self.nubra)
                self.sdk_initialized = True
                print("Nubra SDK initialized successfully.")
            else:
                print("Missing one or more Nubra environment variables. Using mock data.")
        except Exception as e:
            print(f"Error initializing Nubra SDK: {e}. Using mock data.")

    def get_mock_data(self):
        """Returns a mock data structure for the option chain."""
        return {
            "current_price": 50000.0,
            "atm_strike": 50000,
            "all_expiries": ["2024-12-31"],
            "pcr": 0.95,
            "max_pain": 49800,
            "india_vix": 15.5,
            "option_chain": {
                "calls": [
                    {"strike_price": 49800, "ltp": 250.0, "iv": 0.15, "oi": 10000, "oi_change": 500, "volume": 500},
                    {"strike_price": 50000, "ltp": 100.0, "iv": 0.14, "oi": 15000, "oi_change": 750, "volume": 750},
                    {"strike_price": 50200, "ltp": 50.0, "iv": 0.16, "oi": 8000, "oi_change": 400, "volume": 400},
                ],
                "puts": [
                    {"strike_price": 49800, "ltp": 55.0, "iv": 0.16, "oi": 9000, "oi_change": 450, "volume": 450},
                    {"strike_price": 50000, "ltp": 110.0, "iv": 0.15, "oi": 16000, "oi_change": 800, "volume": 800},
                    {"strike_price": 50200, "ltp": 240.0, "iv": 0.14, "oi": 7000, "oi_change": 350, "volume": 350},
                ],
            },
            "futures": [
                {"expiry": "2024-12-31", "ltp": 50100, "oi": 20000, "oi_change": 1000, "volume": 1000},
                {"expiry": "2025-01-31", "ltp": 50200, "oi": 15000, "oi_change": 500, "volume": 500},
            ]
        }

    def get_option_chain_data(self, symbol, exchange="NSE"):
        if not self.sdk_initialized:
            return self.get_mock_data()

        try:
            option_chain_response = self.market_data.option_chain(symbol, exchange=exchange)
            chain = option_chain_response.chain

            pcr = self._calculate_pcr(chain)
            max_pain = self.calculate_max_pain(chain)

            # I was unable to find the INDIAVIX and futures data in the Nubra SDK,
            # so I will continue to use mock data for these fields.
            india_vix = 15.5
            futures = [
                {"expiry": "2024-12-31", "ltp": 50100, "oi": 20000, "oi_change": 1000, "volume": 1000},
                {"expiry": "2025-01-31", "ltp": 50200, "oi": 15000, "oi_change": 500, "volume": 500},
            ]


            return {
                "current_price": chain.current_price,
                "atm_strike": chain.at_the_money_strike,
                "all_expiries": chain.all_expiries,
                "pcr": pcr,
                "max_pain": max_pain,
                "india_vix": india_vix,
                "option_chain": {
                    "calls": [self._format_option_data(o) for o in chain.ce],
                    "puts": [self._format_option_data(o) for o in chain.pe],
                },
                "futures": futures
            }
        except Exception as e:
            print(f"Error fetching option chain data: {e}")
            return {"error": str(e)}

    def _format_option_data(self, option_data):
        return {
            "strike_price": option_data.strike_price,
            "ltp": option_data.last_traded_price,
            "iv": option_data.iv,
            "oi": option_data.open_interest,
            "oi_change": option_data.open_interest_change,
            "volume": option_data.volume,
        }


    def _calculate_pcr(self, option_chain):
        total_put_oi = sum(opt.open_interest for opt in option_chain.pe)
        total_call_oi = sum(opt.open_interest for opt in option_chain.ce)

        if total_call_oi == 0:
            return 0
        return total_put_oi / total_call_oi

    def calculate_max_pain(self, option_chain):
        strikes = sorted(list(set([opt.strike_price for opt in option_chain.ce] + [opt.strike_price for opt in option_chain.pe])))
        pain_levels = {}

        for strike in strikes:
            total_loss = 0
            for call in option_chain.ce:
                if call.strike_price < strike:
                    total_loss += (strike - call.strike_price) * call.open_interest
            for put in option_chain.pe:
                if put.strike_price > strike:
                    total_loss += (put.strike_price - strike) * put.open_interest
            pain_levels[strike] = total_loss

        if not pain_levels:
            return 0

        max_pain_strike = min(pain_levels, key=pain_levels.get)
        return max_pain_strike
