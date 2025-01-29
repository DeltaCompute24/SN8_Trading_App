from typing import Dict, Any
import random
from datetime import datetime


def mock_switch_to_mainnet_response() -> Dict[Any, Any]:
    """
    Mock response for switch to mainnet API call that matches the actual usage pattern
    """
    trader_id = f"TR{random.randint(100000, 999999)}"
    
    return {
        "status": "success",
        "message": "Successfully switched to mainnet",
        "trader_id": trader_id,  # This is used in passing_details
        "account": {
            "login": random.randint(7000000, 7999999),
            "password": "dummypass123",
            "server": "Live-Server1",
            "balance": 100000.00,
            # Add other account details as needed
        }
    }

# Example usage in your testnet_validator.py:
"""
from src.mocks.mainnet_switch_mock import mock_switch_to_mainnet_response

# Replace the actual API call with mock for testing
# _response = requests.post(SWITCH_TO_MAINNET_URL, json=payload)
_response = type('Response', (), {
    'status_code': 200,
    'json': lambda: mock_switch_to_mainnet_response()
})()

data = _response.json()
"""