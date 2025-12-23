const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
const WS_BASE_URL = process.env.REACT_APP_WS_BASE_URL || 'ws://localhost:8000';

export const fetchOptionChain = async (symbol, expiryDate) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/option-chain?symbol=${symbol}&expiry_date=${expiryDate}`);
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch option chain:", error);
    return { calls: [], puts: [] };
  }
};

export const connectToOptionChainFeed = (onMessageCallback) => {
  const ws = new WebSocket(`${WS_BASE_URL}/ws/option-chain`);

  ws.onopen = () => {
    console.log("WebSocket connection established.");
  };

  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    onMessageCallback(message);
  };

  ws.onclose = () => {
    console.log("WebSocket connection closed.");
  };

  ws.onerror = (error) => {
    console.error("WebSocket error:", error);
  };

  return () => {
    ws.close();
  };
};
