import pytest
from src.models.transaction import Transaction, OrderType
from src.tasks.position_monitor_sync import update_trailing_stop_loss, update_trailing_limit
from src.schemas.redis_position import RedisQuotesData

@pytest.fixture
def db():
    """Fixture for database operations"""
    class MockDB:
        def __init__(self):
            self.calls = []
            
        def update_transaction_sync_gen(self, *args):
            self.calls.append(args)
    
    return MockDB()

@pytest.fixture
def base_position():
    """Base position fixture with common attributes"""
    return Transaction(
        trader_id="test_trader",
        trade_pair="BTCUSD",
        trailing=True,
        stop_loss= 2,  # 2% stop loss
        entry_price= 1000.0,
        order_type=OrderType.buy
    )

@pytest.fixture
def mock_redis_quotes(monkeypatch):
    """
    Fixture to mock Redis quotes using monkeypatch
    Returns a function to set quote values during tests
    """
    quotes = RedisQuotesData(bp=0.0, ap=0.0)
    
    def set_quotes(bid_price=0.0, ask_price=0.0):
        quotes.bp = bid_price
        quotes.ap = ask_price
        return quotes
        
    def mock_get_quotes(*args, **kwargs):
        return quotes
        
    monkeypatch.setattr(
        'src.tasks.position_monitor_sync.get_bid_ask_price',
        mock_get_quotes
    )
    return set_quotes

@pytest.fixture
def mock_update_stop_loss(monkeypatch):
    """Mock the update_stop_loss function"""
    calls = []
    
    def mock_update(*args, **kwargs):
        calls.append((args, kwargs))
    
    monkeypatch.setattr(
        'src.tasks.position_monitor_sync.update_stop_loss',
        mock_update
    )
    mock_update.calls = calls
    return mock_update
  

@pytest.fixture
def mock_update_transaction_gen(monkeypatch):
    """Mock the update_stop_loss function"""
    calls = []
    
    def mock_update(*args, **kwargs):
        calls.append((args, kwargs))
    
    monkeypatch.setattr(
        'src.tasks.position_monitor_sync.update_transaction_gen',
        mock_update
    )
    mock_update.calls = calls
    return mock_update

@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(
            {
                "order_type": OrderType.buy,
                "current_price": 1200.0,
                "entry_price": 1000.0,
                "should_update": True
            },
            id="buy_price_increased"
        ),
        pytest.param(
            {
                "order_type": OrderType.buy,
                "current_price": 900.0,
                "entry_price": 1000.0,
                "should_update": False
            },
            id="buy_price_decreased"
        ),
        pytest.param(
            {
                "order_type": OrderType.sell,
                "current_price": 900.0,
                "entry_price": 1000.0,
                "should_update": True
            },
            id="sell_price_decreased"
        ),
        pytest.param(
            {
                "order_type": OrderType.sell,
                "current_price": 1200.0,
                "entry_price": 1000.0,
                "should_update": False
            },
            id="sell_price_increased"
        ),
    ]
)
def test_trailing_stop_loss_scenarios(
    db, 
    base_position, 
    mock_redis_quotes,
    mock_update_stop_loss,
    scenario
):
    """Test trailing stop loss updates for different price scenarios"""
    # Arrange
    base_position.order_type = scenario["order_type"]
    base_position.entry_price = scenario["entry_price"]
    mock_redis_quotes(scenario["current_price"], scenario["current_price"])

    # Act
    result = update_trailing_stop_loss(db, base_position)

    # Assert
    if scenario["should_update"]:
        assert len(mock_update_stop_loss.calls) == 1
    else:
        assert len(mock_update_stop_loss.calls) == 0

@pytest.mark.parametrize(
    "config",
    [
        pytest.param(
            {"trailing": True, "stop_loss": 2, "should_process": True},
            id="valid_trailing_stop"
        ),
        pytest.param(
            {"trailing": False, "stop_loss": 2, "should_process": False},
            id="trailing_disabled"
        ),
        pytest.param(
            {"trailing": True, "stop_loss": 0, "should_process": False},
            id="no_stop_loss"
        ),
    ]
)
def test_position_configurations(
    db, 
    base_position, 
    mock_redis_quotes,
    mock_update_stop_loss, 
    config
):
    """Test different position configurations for trailing stop loss"""
    # Arrange
    base_position.trailing = config["trailing"]
    base_position.stop_loss = config["stop_loss"]
    mock_redis_quotes(1200.0, 1200.0)

    # Act
    result = update_trailing_stop_loss(db, base_position)

    # Assert
    if config["should_process"]:
        assert len(mock_update_stop_loss.calls) == 1
    else:
        assert len(mock_update_stop_loss.calls) == 0

def test_invalid_quotes(db, base_position, mock_redis_quotes):
    """Test handling of invalid quote prices"""
    # Arrange
    mock_redis_quotes(0.0, 0.0)

    # Act
    result = update_trailing_stop_loss(db, base_position)

    # Assert
    assert result is None

@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(
            {
                "order_type": OrderType.buy,
                "initial_price": 1000.0,
                "buy_price": 900.0,  # Favorable for buy
                "sell_price": 900.0,
                "limit_order": 0.02,  # 2%
                "should_update": True,
                "expected_entry": 882.0,  # 900 - (900 * 0.02)
            },
            id="buy_price_decreased_favorable"
        ),
        pytest.param(
            {
                "order_type": OrderType.buy,
                "initial_price": 1000.0,
                "buy_price": 1100.0,  # Unfavorable for buy
                "sell_price": 1100.0,
                "limit_order": 0.02,
                "should_update": False,
                "expected_entry": 1000.0
            },
            id="buy_price_increased_unfavorable"
        ),
        pytest.param(
            {
                "order_type": OrderType.sell,
                "initial_price": 1000.0,
                "buy_price": 1100.0,
                "sell_price": 1100.0,  # Favorable for sell
                "limit_order": 0.02,
                "should_update": True,
                "expected_entry": 1122.0  # 1100 + (1100 * 0.02)
            },
            id="sell_price_increased_favorable"
        ),
        pytest.param(
            {
                "order_type": OrderType.sell,
                "initial_price": 1000.0,
                "buy_price": 900.0,
                "sell_price": 900.0,  # Unfavorable for sell
                "limit_order": 0.02,
                "should_update": False,
                "expected_entry": 1000.0
            },
            id="sell_price_decreased_unfavorable"
        ),
    ]
)
def test_update_trailing_limit_scenarios(
    db,
    base_position,
    mock_update_transaction_gen,  # Added this fixture
    scenario
):
    """Test trailing limit updates for different price scenarios"""
    # Arrange
    base_position.order_type = scenario["order_type"]
    base_position.initial_price = scenario["initial_price"]
    base_position.limit_order = scenario["limit_order"]
    base_position.entry_price = scenario["initial_price"]

    # Act
    update_trailing_limit(
        db,
        base_position,
        scenario["buy_price"],
        scenario["sell_price"]
    )

   # Assert
    if scenario["should_update"]:
        # Check if mock function was called once
        assert len(mock_update_transaction_gen.calls) == 1
        
        # Get the call arguments
        args, _ = mock_update_transaction_gen.calls[0]
        db_arg, position_arg, update_values = args
        
        # Check if update values match expected values
        expected_values = {
            "entry_price": scenario["expected_entry"],
            "initial_price": (scenario["buy_price"] if scenario["order_type"] == OrderType.buy 
                            else scenario["sell_price"]),
            "limit_order": (scenario["buy_price"] * scenario["limit_order"] / scenario["initial_price"])
                          if scenario["order_type"] == OrderType.buy
                          else (scenario["sell_price"] * scenario["limit_order"] / scenario["initial_price"])
        }
        
        # Check each expected value
        for key, expected_value in expected_values.items():
            assert key in update_values
            assert abs(update_values[key] - expected_value) < 0.0001
    else:
        # Check that mock function was not called
        assert len(mock_update_transaction_gen.calls) == 0

@pytest.mark.parametrize(
    "config",
    [
        pytest.param(
            {
                "trailing": True,
                "limit_order": 0.02,
                "initial_price": 1000.0,
                "should_process": True,
                "buy_price": 1100.0,
                "sell_price": 1100.0,  # Favorable for sell
            },
            id="valid_trailing_limit"
        ),
        
    
     
    ]
)
def test_trailing_limit_configurations(
    db,
    base_position,
    mock_update_transaction_gen,
    config
):
    """Test different configurations for trailing limit"""
    # Arrange
    base_position.trailing = config["trailing"]
    base_position.limit_order = config["limit_order"]
    base_position.initial_price = config["initial_price"]
    
    # Act
    update_trailing_limit(db, base_position, 900.0, 900.0)

    # Assert
    if config["should_process"]:
        assert len(mock_update_transaction_gen.calls) == 1
    else:
        assert len(mock_update_transaction_gen.calls) == 0

def test_trailing_limit_calculation_accuracy(
    db,
    base_position
):
    """Test accurate calculation of new trailing limit values"""
    # Arrange
    base_position.order_type = OrderType.buy
    base_position.initial_price = 1000.0
    base_position.limit_order = 0.02  # 2%
    current_price = 900.0

    # Act
    update_trailing_limit(db, base_position, current_price, current_price)

    # Assert
    assert len(db.calls) == 1
    update_call = db.calls[0]
    update_values = update_call[2]

    # Verify calculations
    expected_decrement = current_price * base_position.limit_order
    expected_decrement_percent = (expected_decrement / base_position.initial_price) * 100
    expected_entry = current_price - expected_decrement

    assert abs(update_values["entry_price"] - expected_entry) < 0.0001
    assert update_values["initial_price"] == current_price
    assert abs(update_values["limit_order"] - expected_decrement_percent) < 0.0001

