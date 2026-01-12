from fastapi import FastAPI, WebSocket
from nubra_handler import NubraHandler
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import threading
import uvicorn

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print("WebSocket connected.")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print("WebSocket disconnected.")

    async def broadcast(self, message: str):
        print(f"Broadcasting message: {message[:100]}...")
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()
nubra_handler = NubraHandler()

def start_nubra_websocket(loop):
    """This function runs in a separate thread and manages the WebSocket."""
    print("Nubra WebSocket thread started.")
    try:
        def on_option_data(msg):
            print("Received option data from Nubra.")
            asyncio.run_coroutine_threadsafe(manager.broadcast(msg), loop)

        nubra_handler.start_websocket(on_option_data)
    except Exception as e:
        print(f"Error in Nubra WebSocket thread: {e}")

def run_app():
    """Starts the Nubra WebSocket and then the Uvicorn server."""
    loop = asyncio.get_event_loop()
    websocket_thread = threading.Thread(
        target=start_nubra_websocket,
        args=(loop,),
        daemon=True
    )
    websocket_thread.start()
    print("Nubra WebSocket thread scheduled to start.")

    uvicorn.run(app, host="127.0.0.1", port=8000)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/api/dashboard_data")
def get_dashboard_data(symbol: str = "NIFTY"):
    return nubra_handler.get_option_chain_data(symbol)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive by waiting for messages
            data = await websocket.receive_text()
            print(f"Received message from client: {data}")
    except Exception as e:
        print(f"Error in WebSocket endpoint: {e}")
        # This will handle client disconnects
        manager.disconnect(websocket)
