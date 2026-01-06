from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from smart_api_handler.handler import SmartApiHandler
import datetime
from typing import Optional

app = FastAPI()

# CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust for your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the SmartApiHandler
try:
    api_handler = SmartApiHandler()
except (ValueError, KeyError) as e:
    print(f"Error initializing SmartApiHandler: {e}. Check your config.ini.")
    api_handler = None

@app.get("/")
def read_root():
    return {"message": "Welcome to the Algo Trading Dashboard API"}

# Example endpoint to get option chain
@app.get("/api/option-chain/{symbol}/{expiry_date}")
def get_option_chain_endpoint(symbol: str, expiry_date: str):
    if not api_handler:
        raise HTTPException(status_code=503, detail="SmartAPI handler not initialized")
    option_chain, tokens = api_handler.get_option_chain(symbol, expiry_date)
    if not option_chain:
        raise HTTPException(status_code=404, detail="Option chain not found.")
    return {"option_chain": option_chain, "tokens": tokens}

@app.get("/api/pcr/{symbol}/{expiry_date}")
def get_pcr_endpoint(symbol: str, expiry_date: str):
    if not api_handler:
        raise HTTPException(status_code=503, detail="SmartAPI handler not initialized")
    pcr = api_handler.get_put_call_ratio(symbol, expiry_date)
    if pcr is None:
        raise HTTPException(status_code=404, detail="PCR data not found for the given symbol and expiry.")
    return {"pcr": pcr}

@app.get("/api/max-pain/{symbol}/{expiry_date}")
def get_max_pain_endpoint(symbol: str, expiry_date: str):
    if not api_handler:
        raise HTTPException(status_code=503, detail="SmartAPI handler not initialized")
    max_pain_data = api_handler.get_max_pain(symbol, expiry_date)
    if max_pain_data is None:
        raise HTTPException(status_code=404, detail="Max Pain data not found for the given symbol and expiry.")
    return max_pain_data


@app.get("/api/historical/options/{symbol}/{expiry_date}")
def get_historical_options_endpoint(
    symbol: str,
    expiry_date: str,
    interval: Optional[str] = Query('15minute'),
    fromdate: Optional[str] = Query(None),
    todate: Optional[str] = Query(None),
):
    """Return historical candle data for option chain with greeks/OI attached.

    Query params:
      - interval: candle interval (default '15minute')
      - fromdate, todate: 'YYYY-MM-DD HH:MM' strings. If omitted, defaults to today's 09:15 to now.
    """
    if not api_handler:
        raise HTTPException(status_code=503, detail="SmartAPI handler not initialized")

    try:
        if fromdate is None or todate is None:
            now = datetime.datetime.now()
            to_dt = now
            from_dt = now.replace(hour=9, minute=15, second=0, microsecond=0)
        else:
            from_dt = datetime.datetime.strptime(fromdate, '%Y-%m-%d %H:%M')
            to_dt = datetime.datetime.strptime(todate, '%Y-%m-%d %H:%M')

        data = api_handler.get_historical_data(symbol, interval, from_dt, to_dt, expiry_dates=expiry_date)
        if data is None:
            raise HTTPException(status_code=404, detail="Historical data not found")
        return data
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use 'YYYY-MM-DD HH:MM'.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/{symbol}/{expiry_date}")
def get_metrics_endpoint(symbol: str, expiry_date: str):
    """Aggregate metrics used by the dashboard: PCR, max pain, indiavix, option IV map, futures OI/volume."""
    if not api_handler:
        raise HTTPException(status_code=503, detail="SmartAPI handler not initialized")
    try:
        pcr = api_handler.get_put_call_ratio(symbol, expiry_date)
        max_pain = api_handler.get_max_pain(symbol, expiry_date)
        indiavix = api_handler.get_indiavix()
        iv_map = api_handler.get_option_iv(symbol, expiry_date)
        oi_summary_list = api_handler.get_option_oi(symbol, expiry_date) or []
        # convert oi summary list to map by strike
        oi_summary = {}
        for item in oi_summary_list:
            oi_summary[item.get('strike')] = oi_summary.get(item.get('strike'), {})
            if item.get('type') == 'CE':
                oi_summary[item.get('strike')]['call_oi'] = item.get('oi')
                oi_summary[item.get('strike')]['call_iv'] = item.get('iv')
                oi_summary[item.get('strike')]['call_change'] = item.get('change')
            else:
                oi_summary[item.get('strike')]['put_oi'] = item.get('oi')
                oi_summary[item.get('strike')]['put_iv'] = item.get('iv')
                oi_summary[item.get('strike')]['put_change'] = item.get('change')

        futures_oi = api_handler.get_futures_oi(symbol)
        futures_oi_change = api_handler.get_futures_oi_change(symbol)
        futures_volume = api_handler.get_futures_volume(symbol)

        return {
            'pcr': pcr,
            'max_pain': max_pain,
            'indiavix': indiavix,
            'iv_map': iv_map,
            'oi_summary': oi_summary,
            'futures_oi': futures_oi,
            'futures_oi_change': futures_oi_change,
            'futures_volume': futures_volume,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
