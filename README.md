# Trade Monitor CLI

The Trade Monitor CLI is an advanced command-line interface tool designed for monitoring and managing cryptocurrency and forex trades in real-time. It connects to a WebSocket for live price feeds and allows users to set dynamic thresholds for taking profits and stopping losses.

## Features

- **Real-Time Trade Monitoring**: Connects via WebSocket to receive and process live market data.- **Dynamic Trade Management**: Users can set custom values for take profit and stop loss thresholds.- **Asset Flexibility**: Supports various asset types including cryptocurrencies and forex.- **Trade Simulations**: Includes a test mode for simulating trades without executing real transactions.- **Visual Summaries**: Provides colorful and structured summaries of trade performance.

## Prerequisites

Before you begin, ensure you have Python 3.8 or higher installed on your system.

## Setup

1. **Clone the Repository**:   
    ```bash   
    git clone git@github.com:DeltaCompute24/SN8_Trading_App.git   

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

## Usage

Run the script from the command line, specifying parameters for summary and check intervals, and trading thresholds:

```bash
python3 trade.py --summary_interval 10 --check_interval 1 --take_profit 2 --stop_loss -9.5 --test_mode
```

### Parameters

- `--summary_interval` (int): Frequency in seconds to display the trade summary (default: 60)
- `--check_interval` (int): Frequency in seconds to check for new price updates (default: 5)
- `--take_profit` (float): Take profit level in percentage (default: 2.0)
- `--stop_loss` (float): Stop loss level in percentage (default: -9.5)
- `--test_mode` (bool): Run the bot in simulation mode to test without making actual trades (default: disabled)

### Interactive Inputs

Upon running the script, you will be prompted to enter:- Trade Pair (e.g., BTCUSD)- Order Type (LONG/SHORT)- Leverage (e.g., 25)- Asset Type (forex, crypto)

## Example Output

```plaintext
2024-04-16 23:30:54 - INFO - ============= Trade Summary =============
Trade Open Time : 2024-04-16 23:30:51
Trade Pair      : BTCUSD
Asset Type      : Crypto
Order Type      : LONG
Leverage        : 25.00x
Entry Price     : 63711.00
Current Price   : 63722.00
Profit/Loss     : 0.02% (274.95)
Fee Deducted    : 0.050000
Take Profit     : 2.00%
Stop Loss       : -9.50%
========================================
2024-04-16 23:30:55 - INFO - ============= Trade Summary =============
Trade Open Time : 2024-04-16 23:30:51
Trade Pair      : BTCUSD
Asset Type      : Crypto
Order Type      : LONG
Leverage        : 25.00x
Entry Price     : 63711.00
Current Price   : 63681.26
Profit/Loss     : -0.05% (-743.55)
Fee Deducted    : 0.050000
Take Profit     : 2.00%
Stop Loss       : -9.50%
========================================
```

The output will display structured and colorful summaries at specified intervals, detailing the trade's current status, performance, and relevant thresholds.
