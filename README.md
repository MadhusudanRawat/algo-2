# Live Data Analysis Dashboard

This project is a full-stack application that provides a live data analysis dashboard for stock market options and futures. The backend is built with Python and FastAPI, and it uses the Nubra Python SDK to fetch live market data. The frontend is a React application that displays the data in a clean and intuitive user interface.

## Features

- Displays live option chain data (Calls and Puts)
- Calculates and displays the Put-Call Ratio (PCR)
- Calculates and displays the Max Pain level
- Displays key metrics like the underlying price and INDIAVIX
- Includes a table for futures data

## Backend Setup

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment:**
    - On macOS and Linux:
      ```bash
      source venv/bin/activate
      ```
    - On Windows:
      ```bash
      .\venv\Scripts\activate
      ```

4.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Create a `.env` file:**
    Create a file named `.env` in the `backend` directory and add your Nubra SDK credentials. This is required for the live data feed.
    ```
    PHONE_NO=your_phone_number
    PASSWORD=your_password
    API_KEY=your_api_key
    API_SECRET=your_api_secret
    MPIN=your_mpin
    ```

## Frontend Setup

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install the required dependencies:**
    ```bash
    npm install
    ```

## Running the Application

To run the application for local development, you will need to start both the backend and frontend servers in separate terminal windows.

### Running the Backend

1.  Navigate to the `backend` directory.
2.  Activate your virtual environment.
3.  Run the FastAPI server:
    ```bash
    uvicorn server:app --reload
    ```
    The backend API will be available at `http://127.0.0.1:8000`.

### Running the Frontend

1.  Navigate to the `frontend` directory.
2.  Run the React development server:
    ```bash
    npm start
    ```
    The frontend application will open automatically in your browser at `http://localhost:3000`.
