from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from smart_api_handler.handler import SmartApiHandler

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
