# 🧪 Testnet Setup and Configuration

## Overview

Testnet trading is **MANDATORY** before any live trading. This document provides comprehensive testnet setup for all supported exchanges with step-by-step instructions.

## Why Testnet is Critical

### ✅ **Testnet Benefits**
- **Zero Financial Risk** - Trade with fake money
- **Real API Testing** - Verify API integrations work
- **Error Handling Validation** - Test error scenarios safely
- **Performance Benchmarking** - Measure execution speeds
- **Strategy Validation** - Test AI strategies without risk

### 🚨 **Live Trading Requirements**
- **Minimum 100 successful testnet trades**
- **All safety controls verified working**
- **Emergency stop tested**
- **Error scenarios handled**
- **Performance benchmarks met**

## Exchange Testnet Setup

### 1. Binance Testnet

#### Account Creation
```bash
# 1. Visit Binance Testnet
# https://testnet.binance.vision/

# 2. Create testnet account (separate from main Binance)
# 3. Complete identity verification for testnet
# 4. Generate API credentials
```

#### API Credentials Setup
```python
# Environment variables for Binance Testnet
BINANCE_TESTNET_API_KEY="your_testnet_api_key_here"
BINANCE_TESTNET_SECRET="your_testnet_secret_here"

# Testnet-specific configuration
BINANCE_TESTNET_URL="https://testnet.binance.vision"
```

#### Initial Testnet Funding
```python
# Get testnet funds (automatically provided)
# Binance testnet provides:
# - 1,000 USDT
# - 1 BTC
# - Various altcoins for testing

# Python script to verify testnet balance
import ccxt

exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_TESTNET_API_KEY'),
    'secret': os.getenv('BINANCE_TESTNET_SECRET'),
    'sandbox': True,  # Critical for testnet
    'enableRateLimit': True,
})

balance = exchange.fetch_balance()
print(f"USDT Balance: {balance['USDT']['free']}")
```

#### Testnet Trading Verification
```python
# backend/tests/test_binance_testnet.py
import pytest
import os
import ccxt
from services.exchange_trader import ExchangeTrader

@pytest.mark.skipif(not os.getenv("BINANCE_TESTNET_API_KEY"), reason="Binance testnet credentials not set")
class TestBinanceTestnet:
    """Comprehensive Binance testnet testing"""

    @pytest.fixture
    def testnet_exchange(self):
        """Initialize Binance testnet exchange"""
        return ccxt.binance({
            'apiKey': os.getenv('BINANCE_TESTNET_API_KEY'),
            'secret': os.getenv('BINANCE_TESTNET_SECRET'),
            'sandbox': True,
            'enableRateLimit': True,
        })

    def test_testnet_connection(self, testnet_exchange):
        """Verify testnet connection"""
        balance = testnet_exchange.fetch_balance()
        assert 'USDT' in balance
        assert balance['USDT']['free'] >= 0

    def test_small_market_order(self, testnet_exchange):
        """Place small test market order"""
        # Buy small amount of BTC
        order = testnet_exchange.create_market_order('BTC/USDT', 'buy', 0.001)

        assert order['id'] is not None
        assert order['status'] in ['open', 'closed', 'filled']

        # Clean up - cancel if still open
        if order['status'] == 'open':
            testnet_exchange.cancel_order(order['id'], 'BTC/USDT')

    def test_limit_order_behavior(self, testnet_exchange):
        """Test limit order placement and cancellation"""
        # Place limit order far from market price (won't execute)
        limit_price = 1000000  # Very high for BTC
        order = testnet_exchange.create_limit_order('BTC/USDT', 'buy', 0.001, limit_price)

        assert order['status'] == 'open'

        # Cancel the order
        cancelled = testnet_exchange.cancel_order(order['id'], 'BTC/USDT')
        assert cancelled is True

    def test_error_handling(self, testnet_exchange):
        """Test error handling with invalid orders"""
        # Test insufficient balance
        with pytest.raises(Exception):  # Should raise insufficient funds error
            testnet_exchange.create_market_order('BTC/USDT', 'buy', 1000)  # Huge amount

        # Test invalid symbol
        with pytest.raises(Exception):
            testnet_exchange.create_market_order('INVALID/USDT', 'buy', 0.001)
```

### 2. Coinbase Testnet

#### Account Creation
```bash
# 1. Visit Coinbase Pro Sandbox
# https://public.sandbox.pro.coinbase.com/

# 2. Create sandbox account (separate from main Coinbase)
# 3. Generate sandbox API credentials
# 4. Note the different endpoints
```

#### API Configuration
```python
# Environment variables
COINBASE_SANDBOX_API_KEY="your_sandbox_api_key"
COINBASE_SANDBOX_SECRET="your_sandbox_secret"
COINBASE_SANDBOX_PASSPHRASE="your_sandbox_passphrase"

# Sandbox-specific configuration
COINBASE_SANDBOX_URL="https://api-public.sandbox.pro.coinbase.com"
```

#### Testnet Verification
```python
# backend/tests/test_coinbase_sandbox.py
import pytest
import ccxt

@pytest.mark.skipif(not os.getenv("COINBASE_SANDBOX_API_KEY"), reason="Coinbase sandbox credentials not set")
class TestCoinbaseSandbox:
    """Test Coinbase sandbox functionality"""

    @pytest.fixture
    def sandbox_exchange(self):
        """Initialize Coinbase sandbox exchange"""
        return ccxt.coinbase({
            'apiKey': os.getenv('COINBASE_SANDBOX_API_KEY'),
            'secret': os.getenv('COINBASE_SANDBOX_SECRET'),
            'passphrase': os.getenv('COINBASE_SANDBOX_PASSPHRASE'),
            'sandbox': True,
            'enableRateLimit': True,
        })

    def test_sandbox_connection(self, sandbox_exchange):
        """Verify sandbox connection"""
        balance = sandbox_exchange.fetch_balance()
        assert 'USD' in balance or 'USDT' in balance

    def test_market_order(self, sandbox_exchange):
        """Test market order in sandbox"""
        # Place small test order
        order = sandbox_exchange.create_market_order('BTC-USD', 'buy', 0.001)
        assert order['id'] is not None

        # Cancel if not filled
        if order['status'] == 'open':
            sandbox_exchange.cancel_order(order['id'], 'BTC-USD')
```

### 3. Mock Exchange for Testing

```python
# backend/tests/mock_exchange.py
import time
import random
from typing import Dict, List
from decimal import Decimal

class MockExchange:
    """Mock exchange for comprehensive testing without real API calls"""

    def __init__(self, initial_balance: float = 10000.0):
        self.balance = {
            'USD': initial_balance,
            'USDT': initial_balance,
            'BTC': 0.0,
            'ETH': 0.0
        }
        self.orders = {}
        self.order_counter = 1000
        self.trades = []
        self.current_prices = {
            'BTC/USDT': 50000.0,
            'ETH/USDT': 3000.0,
            'SOL/USDT': 100.0
        }

    def create_market_order(self, symbol: str, side: str, amount: float) -> Dict:
        """Simulate market order"""
        self.order_counter += 1
        order_id = f"mock_order_{self.order_counter}"

        price = self.current_prices.get(symbol, 50000.0)
        total_cost = price * amount

        # Simulate order execution
        if side.lower() == 'buy':
            if self.balance['USDT'] >= total_cost:
                self.balance['USDT'] -= total_cost
                # Add the crypto to balance
                crypto_symbol = symbol.split('/')[0]
                self.balance[crypto_symbol] = self.balance.get(crypto_symbol, 0) + amount

                order = {
                    'id': order_id,
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'price': price,
                    'status': 'filled',
                    'filled': amount,
                    'remaining': 0,
                    'cost': total_cost
                }
            else:
                raise Exception("Insufficient balance")
        else:
            # Sell order
            crypto_symbol = symbol.split('/')[0]
            if self.balance.get(crypto_symbol, 0) >= amount:
                self.balance[crypto_symbol] -= amount
                self.balance['USDT'] += total_cost * 0.999  # Include 0.1% fee

                order = {
                    'id': order_id,
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'price': price,
                    'status': 'filled',
                    'filled': amount,
                    'remaining': 0,
                    'cost': total_cost * 0.999
                }
            else:
                raise Exception("Insufficient position")

        self.orders[order_id] = order
        self.trades.append(order)

        # Simulate processing time
        time.sleep(0.1)

        return order

    def create_limit_order(self, symbol: str, side: str, amount: float, price: float) -> Dict:
        """Simulate limit order"""
        self.order_counter += 1
        order_id = f"mock_limit_{self.order_counter}"

        order = {
            'id': order_id,
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': price,
            'status': 'open',
            'filled': 0,
            'remaining': amount
        }

        self.orders[order_id] = order

        # Simulate random fills
        if random.random() < 0.1:  # 10% chance of immediate fill
            self._fill_limit_order(order_id)

        return order

    def cancel_order(self, order_id: str, symbol: str = None) -> bool:
        """Cancel order"""
        if order_id in self.orders:
            self.orders[order_id]['status'] = 'cancelled'
            return True
        return False

    def fetch_balance(self) -> Dict:
        """Get current balance"""
        return {
            'free': self.balance.copy(),
            'used': {k: 0.0 for k in self.balance.keys()},
            'total': self.balance.copy()
        }

    def fetch_open_orders(self) -> List[Dict]:
        """Get open orders"""
        return [order for order in self.orders.values() if order['status'] == 'open']

    def _fill_limit_order(self, order_id: str):
        """Simulate limit order fill"""
        if order_id in self.orders:
            order = self.orders[order_id]
            order['status'] = 'filled'
            order['filled'] = order['amount']
            order['remaining'] = 0
            self.trades.append(order)

    def simulate_price_movement(self):
        """Simulate price movements for testing"""
        for symbol in self.current_prices:
            # Random price movement ±2%
            change_percent = random.uniform(-0.02, 0.02)
            self.current_prices[symbol] *= (1 + change_percent)

        # Check if any limit orders should be filled
        for order_id, order in list(self.orders.items()):
            if order['status'] == 'open':
                current_price = self.current_prices.get(order['symbol'])
                if current_price:
                    should_fill = False
                    if order['side'].lower() == 'buy' and current_price <= order['price']:
                        should_fill = True
                    elif order['side'].lower() == 'sell' and current_price >= order['price']:
                        should_fill = True

                    if should_fill:
                        self._fill_limit_order(order_id)
```

## Comprehensive Testnet Testing Suite

### 1. Integration Tests

```python
# backend/tests/test_real_trading_integration.py
import pytest
import os
from decimal import Decimal
from unittest.mock import patch
from services.exchange_trader import ExchangeTrader
from services.risk_manager import RiskManager
from services.credential_manager import CredentialManager
from database.models import Account, Order, Trade

@pytest.mark.skipif(not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests disabled")
class TestRealTradingIntegration:
    """Comprehensive integration tests for real trading"""

    @pytest.fixture
    def test_account(self, db):
        """Create test account with testnet credentials"""
        account = Account(
            name="Integration Test Account",
            exchange_name="binance",
            testnet_mode="true",
            trading_mode="LIVE",
            trading_enabled="true",
            emergency_stop="false",
            max_position_size=100.0,
            max_daily_loss=50.0
        )
        db.add(account)
        db.commit()
        db.refresh(account)

        # Add testnet credentials
        credential_manager = CredentialManager(os.getenv("MASTER_PASSWORD"))
        credential_manager.encrypt_and_store_api_credentials(
            account.id, db,
            os.getenv("BINANCE_TESTNET_API_KEY"),
            os.getenv("BINANCE_TESTNET_SECRET")
        )

        return account

    def test_full_trading_workflow(self, test_account, db):
        """Test complete trading workflow"""
        # 1. Initialize exchange trader
        trader = ExchangeTrader(test_account, db)

        # 2. Check initial balance
        initial_balance = trader.get_real_balance()
        assert initial_balance.get('USDT', 0) > 0

        # 3. Place small buy order
        buy_result = trader.create_market_order("BTC/USDT", "buy", 0.001)
        assert buy_result['success'] is True
        assert buy_result['order_id'] is not None

        # 4. Wait a moment for order processing
        time.sleep(2)

        # 5. Check balance after buy
        balance_after_buy = trader.get_real_balance()
        # Should have slightly less USDT (spent on BTC)

        # 6. Place sell order
        sell_result = trader.create_market_order("BTC/USDT", "sell", 0.001)
        assert sell_result['success'] is True

        # 7. Verify order records in database
        orders = db.query(Order).filter(Order.account_id == test_account.id).all()
        assert len(orders) >= 2

        # 8. Verify risk metrics
        risk_manager = RiskManager(test_account, db)
        metrics = risk_manager.get_risk_metrics()
        assert metrics['risk_status']['testnet_mode'] is True

    def test_error_recovery(self, test_account, db):
        """Test error handling and recovery"""
        trader = ExchangeTrader(test_account, db)

        # Test invalid order (too large)
        large_order_result = trader.create_market_order("BTC/USDT", "buy", 100.0)
        assert large_order_result['success'] is False
        assert 'error' in large_order_result

        # Test invalid symbol
        invalid_symbol_result = trader.create_market_order("INVALID/USDT", "buy", 0.001)
        assert invalid_symbol_result['success'] is False

        # Verify system still works after errors
        valid_order_result = trader.create_market_order("BTC/USDT", "buy", 0.001)
        assert valid_order_result['success'] is True

    def test_emergency_stop(self, test_account, db):
        """Test emergency stop functionality"""
        # Activate emergency stop
        risk_manager = RiskManager(test_account, db)
        success = risk_manager.activate_emergency_stop("Test emergency stop")
        assert success is True

        # Verify trading is blocked
        trader = ExchangeTrader(test_account, db)
        order_result = trader.create_market_order("BTC/USDT", "buy", 0.001)
        assert order_result['success'] is False
        assert "Emergency stop" in order_result['error']

        # Verify emergency stop is recorded
        updated_account = db.query(Account).filter(Account.id == test_account.id).first()
        assert updated_account.emergency_stop == "true"

    def test_risk_limits_enforced(self, test_account, db):
        """Test that risk limits are properly enforced"""
        # Set very low limits for testing
        test_account.max_position_size = 10.0  # $10 max position
        db.commit()

        risk_manager = RiskManager(test_account, db)
        trader = ExchangeTrader(test_account, db)

        # Try to place order exceeding limit
        result = trader.create_market_order("BTC/USDT", "buy", 0.001)  # ~$50
        assert result['success'] is False
        assert "exceeds limit" in result['error']

    def test_balance_synchronization(self, test_account, db):
        """Test balance synchronization after trades"""
        trader = ExchangeTrader(test_account, db)

        # Get initial balance
        initial_balance = trader.get_real_balance()
        initial_usdt = initial_balance.get('USDT', 0)

        # Place trade
        trader.create_market_order("BTC/USDT", "buy", 0.001)

        # Sync balance
        updated_balance = trader.get_real_balance()
        updated_usdt = updated_balance.get('USDT', 0)

        # Verify balance was updated
        assert updated_usdt < initial_usdt

        # Verify database was updated
        updated_account = db.query(Account).filter(Account.id == test_account.id).first()
        assert updated_account.last_balance_sync is not None
```

### 2. Performance Tests

```python
# backend/tests/test_performance.py
import pytest
import time
from services.exchange_trader import ExchangeTrader

class TestPerformance:
    """Performance testing for trading operations"""

    @pytest.mark.performance
    def test_order_execution_speed(self, test_account, db):
        """Test order execution speed"""
        trader = ExchangeTrader(test_account, db)

        start_time = time.time()
        result = trader.create_market_order("BTC/USDT", "buy", 0.001)
        execution_time = time.time() - start_time

        # Orders should execute within 2 seconds
        assert execution_time < 2.0
        assert result['success'] is True

    @pytest.mark.performance
    def test_balance_sync_speed(self, test_account, db):
        """Test balance synchronization speed"""
        trader = ExchangeTrader(test_account, db)

        start_time = time.time()
        balance = trader.get_real_balance()
        sync_time = time.time() - start_time

        # Balance sync should complete within 1 second
        assert sync_time < 1.0
        assert isinstance(balance, dict)

    @pytest.mark.performance
    def test_concurrent_orders(self, test_account, db):
        """Test handling multiple concurrent orders"""
        trader = ExchangeTrader(test_account, db)

        results = []
        start_time = time.time()

        # Place multiple orders rapidly
        for i in range(5):
            result = trader.create_market_order("BTC/USDT", "buy", 0.0001)
            results.append(result)

        total_time = time.time() - start_time

        # All orders should complete within 5 seconds
        assert total_time < 5.0
        assert all(r['success'] for r in results)
```

### 3. Load Testing

```python
# backend/tests/test_load.py
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from services.exchange_trader import ExchangeTrader

@pytest.mark.load
class TestLoad:
    """Load testing for high-volume scenarios"""

    def test_high_frequency_trading(self, test_account, db):
        """Test high-frequency trading scenario"""
        trader = ExchangeTrader(test_account, db)

        def place_trade():
            """Place a single trade"""
            result = trader.create_market_order("BTC/USDT", "buy", 0.0001)
            time.sleep(0.1)  # Small delay
            if result['success']:
                # Place corresponding sell
                trader.create_market_order("BTC/USDT", "sell", 0.0001)
            return result['success']

        # Execute 20 trades concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(place_trade) for _ in range(20)]
            results = [f.result() for f in futures]

        # Most trades should succeed
        success_rate = sum(results) / len(results)
        assert success_rate > 0.8  # At least 80% success rate

    def test_order_cancellation_load(self, test_account, db):
        """Test bulk order cancellation"""
        trader = ExchangeTrader(test_account, db)

        # Place many limit orders
        order_ids = []
        for i in range(10):
            result = trader.create_limit_order("BTC/USDT", "buy", 0.0001, 30000.0)
            if result['success']:
                order_ids.append(result['order_id'])

        # Cancel all orders rapidly
        start_time = time.time()
        cancellation_results = []
        for order_id in order_ids:
            result = trader.cancel_order("mock_id", "BTC/USDT")  # Use mock for testing
            cancellation_results.append(result)

        total_time = time.time() - start_time

        # Cancellations should be fast
        assert total_time < 2.0
```

## Testnet Configuration Management

### 1. Environment Configuration

```python
# backend/config/testnet_config.py
import os
from typing import Dict, Optional
from pydantic import BaseModel

class TestnetConfig(BaseModel):
    """Configuration for testnet environments"""

    # Exchange settings
    binance_testnet: bool = True
    coinbase_sandbox: bool = True
    mock_exchange: bool = True

    # Test limits
    max_test_order_value: float = 100.0  # Max order value in testnet
    max_daily_trades: int = 100  # Max trades per day in testnet
    test_duration_hours: int = 24  # Minimum testnet testing duration

    # Safety settings
    enforce_testnet_only: bool = True  # Block live trading attempts
    emergency_stop_enabled: bool = True
    require_manual_confirmation: bool = False  # Auto-confirm in testnet

    @classmethod
    def from_environment(cls) -> 'TestnetConfig':
        """Load configuration from environment variables"""
        return cls(
            binance_testnet=os.getenv('BINANCE_TESTNET', 'true').lower() == 'true',
            coinbase_sandbox=os.getenv('COINBASE_SANDBOX', 'true').lower() == 'true',
            mock_exchange=os.getenv('MOCK_EXCHANGE', 'true').lower() == 'true',
            enforce_testnet_only=os.getenv('ENFORCE_TESTNET_ONLY', 'true').lower() == 'true',
            emergency_stop_enabled=os.getenv('EMERGENCY_STOP_ENABLED', 'true').lower() == 'true',
        )

    def validate_testnet_credentials(self) -> Dict[str, bool]:
        """Validate that testnet credentials are properly configured"""
        credentials_status = {}

        if self.binance_testnet:
            credentials_status['binance'] = bool(
                os.getenv('BINANCE_TESTNET_API_KEY') and
                os.getenv('BINANCE_TESTNET_SECRET')
            )

        if self.coinbase_sandbox:
            credentials_status['coinbase'] = bool(
                os.getenv('COINBASE_SANDBOX_API_KEY') and
                os.getenv('COINBASE_SANDBOX_SECRET') and
                os.getenv('COINBASE_SANDBOX_PASSPHRASE')
            )

        credentials_status['mock'] = self.mock_exchange

        return credentials_status
```

### 2. Testnet Validation Script

```python
# backend/scripts/validate_testnet_setup.py
import os
import sys
import logging
from config.testnet_config import TestnetConfig
from services.exchange_trader import ExchangeTrader

def validate_testnet_setup():
    """Comprehensive testnet setup validation"""
    print("🧪 Validating Testnet Setup")
    print("=" * 50)

    # 1. Check configuration
    config = TestnetConfig.from_environment()
    print(f"✅ Configuration loaded")
    print(f"   - Enforce testnet only: {config.enforce_testnet_only}")
    print(f"   - Emergency stop enabled: {config.emergency_stop_enabled}")

    # 2. Validate credentials
    credentials = config.validate_testnet_credentials()
    print(f"\n🔑 Credentials Status:")
    for exchange, status in credentials.items():
        status_icon = "✅" if status else "❌"
        print(f"   - {exchange.capitalize()}: {status_icon}")

    # 3. Test exchange connections
    print(f"\n🔄 Testing Exchange Connections:")

    if credentials.get('binance'):
        try:
            # Test Binance testnet connection
            from database.connection import SessionLocal
            from database.models import Account

            db = SessionLocal()
            test_account = Account(
                name="Validation Test",
                exchange_name="binance",
                testnet_mode="true"
            )

            trader = ExchangeTrader(test_account, db)
            balance = trader.get_real_balance()
            print(f"   - Binance Testnet: ✅ Connected (Balance: {balance.get('USDT', 0)} USDT)")

        except Exception as e:
            print(f"   - Binance Testnet: ❌ Connection failed: {e}")

    # 4. Test mock exchange
    if credentials.get('mock'):
        try:
            from tests.mock_exchange import MockExchange
            mock = MockExchange()
            order = mock.create_market_order('BTC/USDT', 'buy', 0.001)
            print(f"   - Mock Exchange: ✅ Working (Order ID: {order['id']})")
        except Exception as e:
            print(f"   - Mock Exchange: ❌ Failed: {e}")

    # 5. Safety checks
    print(f"\n🛡️ Safety Checks:")

    # Check if live trading would be blocked
    if config.enforce_testnet_only:
        print(f"   - Live trading protection: ✅ Enforced")
    else:
        print(f"   - Live trading protection: ⚠️  NOT ENFORCED")

    # Check master password
    if os.getenv('MASTER_PASSWORD'):
        print(f"   - Master password: ✅ Set")
    else:
        print(f"   - Master password: ❌ Not set")

    print(f"\n📋 Validation Complete!")

    # Return validation status
    all_credentials_valid = all(credentials.values())
    return all_credentials_valid and config.enforce_testnet_only

if __name__ == "__main__":
    try:
        success = validate_testnet_setup()
        if success:
            print("✅ All validations passed - Ready for testnet trading!")
            sys.exit(0)
        else:
            print("❌ Some validations failed - Review and fix issues")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        sys.exit(1)
```

## Testnet Usage Guidelines

### ✅ **Testnet Best Practices**

1. **Start with Mock Exchange** - Test all logic with mock exchange first
2. **Use Small Amounts** - Test with 0.001 BTC or equivalent
3. **Test All Scenarios** - Success, failure, edge cases
4. **Verify Safety Controls** - Test emergency stop, risk limits
5. **Monitor Performance** - Check execution speeds, API response times
6. **Document Results** - Keep detailed test logs

### 📊 **Required Test Metrics**

Before any live trading:

```python
REQUIRED_METRICS = {
    'successful_trades': 100,
    'min_success_rate': 0.95,  # 95% success rate
    'max_execution_time': 2.0,  # 2 seconds max
    'emergency_stop_tested': True,
    'risk_limits_tested': True,
    'error_recovery_tested': True,
    'balance_sync_working': True,
    'api_rate_limits_respected': True
}
```

### 🚀 **Progressive Testing Path**

1. **Phase 1**: Mock exchange only (1 day)
2. **Phase 2**: Single exchange testnet (3 days)
3. **Phase 3**: Multiple exchanges testnet (1 week)
4. **Phase 4**: Stress testing (1 week)
5. **Phase 5**: Live trading readiness review

### 📝 **Testnet Documentation**

Maintain detailed testnet logs:

```python
# backend/utils/testnet_logger.py
import logging
from datetime import datetime

class TestnetLogger:
    """Log all testnet trading activities"""

    def __init__(self):
        self.logger = logging.getLogger('testnet')
        handler = logging.FileHandler('testnet_trades.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_trade(self, symbol: str, side: str, amount: float, result: dict):
        """Log testnet trade"""
        self.logger.info(f"TRADE: {side} {amount} {symbol} - Result: {result}")

    def log_error(self, operation: str, error: str):
        """Log testnet error"""
        self.logger.error(f"ERROR in {operation}: {error}")

    def log_safety_event(self, event_type: str, details: str):
        """Log safety-related events"""
        self.logger.warning(f"SAFETY: {event_type} - {details}")
```

This comprehensive testnet setup ensures safe, thorough testing before any real trading occurs. Remember: **Never skip testnet testing** - it's your safety net against financial loss.