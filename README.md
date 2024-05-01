# Trade Monitor Fast API

This API allows users to initiate and monitor cryptocurrency or forex trades programmatically. It provides a simple interface for starting trades with specific parameters and checking the status of those trades using a unique session ID. The system is designed to handle requests asynchronously, ensuring that operations do not block the API's responsiveness.

## Features

- **Real-Time Trade Monitoring**: Connects via WebSocket to receive and process live market data.- **Dynamic Trade Management**: Users can set custom values for take profit and stop loss thresholds.- **Asset Flexibility**: Supports various asset types including cryptocurrencies and forex.- **Trade Simulations**: Includes a test mode for simulating trades without executing real transactions.- 

## Prerequisites

Before you begin, ensure you have Python 3.8 or higher installed on your system.

## Setup

1. **Clone the Repository and select the api branch**:   
    ```bash   
    git clone git@github.com:DeltaCompute24/SN8_Trading_App.git 
    git checkout api
    cd SN8_Trading_App
    ```


2. **Setup Virtual Environment**:

    ```bash   
    python3 -m venv venv   

    -macos/linus: source venv/bin/activate  

    -Windows: `venv\Scripts\activate`   
    ```

3. **Install Requirements**:   
    ```bash   
    pip install -r requirements.txt   
    ```

4. **Set Environment Variables**:   
Create a `.env` file in the root directory of the project and add the following lines:  

    ```bash 
    POLYGON_API_KEY="XXXXXXXXXXXXXXXXXXXXXXXX"
    SIGNAL_API_KEY="XXXXXXXXXXXXXXXXXXXXXX"    
    ```

5. **Modify Permission for the Script** :   
    ```bash   
    chmod +x trade.py   
    ```

### Endpoints
#### POST /trades/
- **Description**: Initiates a new trading session based on the provided parameters.
- **Request Body**:
  ```json
  {
    "trader_id": 4040,
    "trade_pair": "BTCUSD",
    "order_type": "LONG",
    "leverage": 10,
    "asset_type": "crypto",
    "stop_loss": 2.5,
    "take_profit": 5.0,
    "test_mode": true
  }
  ```
- **Response**:
  ```json
  {
    "session_id": "<unique-session-id>",
    "message": "Initiating trade"
  }
  ```
#### GET /trades/{session_id}
- **Description**: Retrieves the current status of the specified trading session.
- **Parameters**:
  - **session_id**: UUID of the trade session to query.
- **Response**:
  ```json
  {
    "Trade Open Time": "<timestamp>",
    "Trade Pair": "BTCUSD",
    "Asset Type": "Crypto",
    "Order Type": "LONG",
    "Leverage": "10.00x",
    "Entry Price": "10000.00",
    "Current Price": "10050.00",
    "Profit/Loss": "0.5% (50.00)",
    "Fee Deducted": "0.020000",
    "Take Profit": "5.00%",
    "Stop Loss": "2.50%"
  }
  ```

## Usage

1. Navigate to the project directory in the terminal.
2. Run the following command to start the Uvicorn server:
   ```bash
   uvicorn api:app --host 0.0.0.0 --port 8000 --reload
   ```
3. Open a web browser and navigate to `http://localhost:8000/docs` to access the Swagger UI.
## Testing Using Swagger UI
1. Open Swagger UI by visiting `http://localhost:8000/docs`.
2. Expand the `/trades/` endpoint and try executing a POST request using the sample request body provided above.
3. Note the `session_id` returned from the POST response.
4. Expand the `/trades/{session_id}` endpoint, enter the `session_id`, and execute the GET request to see the trade status.

