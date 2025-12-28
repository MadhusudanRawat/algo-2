from fastapi import FastAPI
from nubra_handler import NubraHandler
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


nubra_handler = NubraHandler()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/api/dashboard_data")
def get_dashboard_data(symbol: str = "NIFTY"):
    return nubra_handler.get_option_chain_data(symbol)
