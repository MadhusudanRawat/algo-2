from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from smart_api_handler.handler import SmartApiHandler
from functools import lru_cache
import asyncio

app = FastAPI()

# Allow CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@lru_cache()
def get_smart_api_handler():
    """
    Dependency function to get a cached instance of the SmartApiHandler.
    """
    try:
        handler = SmartApiHandler()
        handler.start_websocket() # Start the WebSocket connection on initialization
        return handler
    except Exception as e:
        print(f"Failed to initialize SmartApiHandler: {e}")
        return None

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/api/option-chain")
def get_initial_option_chain(symbol: str = "NIFTY", expiry_date: str = "25JUL2024", smart_api_handler: SmartApiHandler = Depends(get_smart_api_handler)):
    if smart_api_handler:
        option_chain, tokens = smart_api_handler.get_option_chain(symbol, expiry_date)
        if option_chain:
            # Subscribe to the tokens for live data
            smart_api_handler.subscribe_to_symbols(tokens)
            return option_chain

    return {"calls": [], "puts": []}

@app.websocket("/ws/option-chain")
async def websocket_endpoint(websocket: WebSocket, smart_api_handler: SmartApiHandler = Depends(get_smart_api_handler)):
    await websocket.accept()
    if not smart_api_handler:
        await websocket.close(code=1011, reason="SmartAPI handler not initialized.")
        return

    try:
        while True:
            # Get message from the SmartAPI WebSocket queue
            message = smart_api_handler.get_websocket_message()
            if message:
                await websocket.send_json(message)
            await asyncio.sleep(0.1) # Prevent a busy-wait loop
    except WebSocketDisconnect:
        print("Client disconnected from WebSocket.")
    except Exception as e:
        print(f"An error occurred in the WebSocket endpoint: {e}")
        await websocket.close(code=1011, reason=f"An error occurred: {e}")
