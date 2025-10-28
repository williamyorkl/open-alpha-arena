# 🗄️ Database Models for Real Trading

## Overview

This document outlines the database schema modifications required to support real trading functionality with secure credential storage, risk management, and safety controls.

## Database Schema Updates

### Updated Account Model

```python
# backend/database/models.py
from sqlalchemy import Column, Integer, String, DECIMAL, TIMESTAMP, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

class Account(Base):
    """Enhanced Trading Account with real trading capabilities"""
    __tablename__ = "accounts"

    # Existing fields
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    version = Column(String(100), nullable=False, default="v1")
    name = Column(String(100), nullable=False)
    account_type = Column(String(20), nullable=False, default="AI")
    is_active = Column(String(10), nullable=False, default="true")

    # AI Model Configuration (existing)
    model = Column(String(100), nullable=True, default="gpt-4")
    base_url = Column(String(500), nullable=True, default="https://api.openai.com/v1")
    api_key = Column(String(500), nullable=True)  # Legacy field for AI API

    # Trading Balances (existing)
    initial_capital = Column(DECIMAL(18, 2), nullable=False, default=10000.00)
    current_cash = Column(DECIMAL(18, 2), nullable=False, default=10000.00)
    frozen_cash = Column(DECIMAL(18, 2), nullable=False, default=0.00)

    # ========== NEW: REAL TRADING FIELDS ==========

    # Trading Mode Configuration
    trading_mode = Column(String(20), nullable=False, default="PAPER")  # "PAPER" or "LIVE"
    exchange_name = Column(String(50), nullable=True)  # "binance", "coinbase", "kraken", etc.

    # Encrypted Exchange Credentials
    exchange_api_key_encrypted = Column(String(1000), nullable=True)
    exchange_api_secret_encrypted = Column(String(1000), nullable=True)
    exchange_passphrase_encrypted = Column(String(500), nullable=True)  # For exchanges requiring passphrase

    # Encrypted Web3 Wallet Credentials
    wallet_private_key_encrypted = Column(String(1000), nullable=True)
    wallet_address = Column(String(100), nullable=True)
    wallet_network = Column(String(20), nullable=True, default="ethereum")  # ethereum, polygon, bsc, etc.

    # Risk Management Settings
    max_position_size = Column(DECIMAL(18, 2), nullable=True, default=1000.00)  # Max USD per position
    max_daily_loss = Column(DECIMAL(18, 2), nullable=True, default=100.00)     # Max daily loss in USD
    max_positions = Column(Integer, nullable=True, default=5)                  # Max concurrent positions
    max_leverage = Column(DECIMAL(5, 2), nullable=True, default=1.0)          # Maximum leverage allowed

    # Safety and Emergency Controls
    emergency_stop = Column(String(10), nullable=False, default="false")       # Emergency stop flag
    testnet_mode = Column(String(10), nullable=False, default="true")          # Force testnet trading
    require_confirmation = Column(String(10), nullable=False, default="true")  # Manual confirmation required

    # Real-time Synchronization
    last_balance_sync = Column(TIMESTAMP, nullable=True)                       # Last balance sync time
    sync_status = Column(String(20), nullable=True, default="pending")         # sync status
    real_balance_usd = Column(DECIMAL(18, 2), nullable=True)                  # Real balance from exchange

    # Advanced Settings
    trading_enabled = Column(String(10), nullable=False, default="false")      # Master trading switch
    auto_rebalance = Column(String(10), nullable=False, default="false")       # Auto rebalancing enabled
    slippage_tolerance = Column(DECIMAL(5, 4), nullable=True, default=0.0050) # 0.5% default slippage

    # Audit and Compliance
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    last_trade_at = Column(TIMESTAMP, nullable=True)                          # Last trade timestamp
    compliance_flags = Column(Text, nullable=True)                             # Compliance notes

    # Relationships
    user = relationship("User", back_populates="accounts")
    positions = relationship("Position", back_populates="account")
    orders = relationship("Order", back_populates="account")
    trades = relationship("Trade", back_populates="account")

    # New relationships for real trading
    risk_logs = relationship("RiskLog", back_populates="account")
    sync_logs = relationship("SyncLog", back_populates="account")
    emergency_events = relationship("EmergencyEvent", back_populates="account")
```

### New Risk Management Models

```python
class RiskLog(Base):
    """Risk management event log"""
    __tablename__ = "risk_logs"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    # Event Details
    event_type = Column(String(50), nullable=False)  # "POSITION_LIMIT", "DAILY_LOSS", "EMERGENCY_STOP"
    event_severity = Column(String(20), nullable=False)  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    event_message = Column(Text, nullable=False)

    # Risk Metrics
    current_position_size = Column(DECIMAL(18, 2), nullable=True)
    current_daily_loss = Column(DECIMAL(18, 2), nullable=True)
    available_balance = Column(DECIMAL(18, 2), nullable=True)
    total_exposure = Column(DECIMAL(18, 2), nullable=True)

    # Action Taken
    action_taken = Column(String(100), nullable=True)  # "ORDER_BLOCKED", "TRADING_STOPPED", "ALERT_SENT"
    action_result = Column(String(20), nullable=True)  # "SUCCESS", "FAILED", "PARTIAL"

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    # Relationships
    account = relationship("Account", back_populates="risk_logs")


class SyncLog(Base):
    """Balance synchronization log"""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    # Sync Details
    sync_type = Column(String(20), nullable=False)  # "BALANCE", "POSITIONS", "ORDERS"
    sync_source = Column(String(50), nullable=False)  # "BINANCE", "COINBASE", "WALLET"
    sync_status = Column(String(20), nullable=False)  # "SUCCESS", "FAILED", "PARTIAL"

    # Data Before Sync
    balance_before = Column(DECIMAL(18, 2), nullable=True)
    positions_before = Column(Text, nullable=True)  # JSON string

    # Data After Sync
    balance_after = Column(DECIMAL(18, 2), nullable=True)
    positions_after = Column(Text, nullable=True)   # JSON string

    # Performance Metrics
    sync_duration_ms = Column(Integer, nullable=True)
    api_calls_count = Column(Integer, nullable=True)

    # Error Details
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    # Relationships
    account = relationship("Account", back_populates="sync_logs")


class EmergencyEvent(Base):
    """Emergency stop and safety events"""
    __tablename__ = "emergency_events"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    # Event Details
    event_type = Column(String(50), nullable=False)  # "MANUAL_STOP", "AUTO_STOP", "SYSTEM_ERROR"
    trigger_reason = Column(Text, nullable=False)
    trigger_source = Column(String(50), nullable=True)  # "USER", "SYSTEM", "API", "MONITOR"

    # State Changes
    trading_stopped = Column(String(10), nullable=False, default="true")
    orders_cancelled = Column(String(10), nullable=False, default="false")
    positions_liquidated = Column(String(10), nullable=False, default="false")

    # Resolution
    resolved = Column(String(10), nullable=False, default="false")
    resolved_at = Column(TIMESTAMP, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Impact Assessment
    orders_affected_count = Column(Integer, nullable=True)
    positions_affected_count = Column(Integer, nullable=True)
    financial_impact = Column(DECIMAL(18, 2), nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    # Relationships
    account = relationship("Account", back_populates="emergency_events")
```

### Enhanced Order Model

```python
class Order(Base):
    """Enhanced Order model with real trading support"""
    __tablename__ = "orders"

    # Existing fields
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(100), nullable=False, default="v1")
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    order_no = Column(String(32), unique=True, nullable=False)
    symbol = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    market = Column(String(10), nullable=False, default="CRYPTO")
    side = Column(String(10), nullable=False)
    order_type = Column(String(20), nullable=False)
    price = Column(DECIMAL(18, 6))
    quantity = Column(DECIMAL(18, 8), nullable=False)
    filled_quantity = Column(DECIMAL(18, 8), nullable=False, default=0)
    status = Column(String(20), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    # ========== NEW: REAL TRADING FIELDS ==========

    # Exchange Integration
    exchange_order_id = Column(String(100), nullable=True)  # Real exchange order ID
    exchange_name = Column(String(50), nullable=True)       # Exchange where order was placed
    exchange_status = Column(String(50), nullable=True)     # Exchange-specific status

    # Execution Details
    filled_price = Column(DECIMAL(18, 6), nullable=True)    # Actual execution price
    fill_timestamp = Column(TIMESTAMP, nullable=True)       # When order was filled
    exchange_fee = Column(DECIMAL(18, 6), nullable=True)    # Actual exchange fee charged
    exchange_fee_currency = Column(String(10), nullable=True) # Fee currency (USD, BTC, etc.)

    # Risk and Compliance
    risk_check_passed = Column(String(10), nullable=False, default="true")
    risk_check_details = Column(Text, nullable=True)         # JSON with risk metrics
    manual_confirmation = Column(String(10), nullable=True)  # If manual confirmation was required
    confirmed_by = Column(String(100), nullable=True)        # Who confirmed the trade

    # Error Handling
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)

    # SL/TP Integration
    stop_loss_price = Column(DECIMAL(18, 6), nullable=True)  # Stop loss price
    take_profit_price = Column(DECIMAL(18, 6), nullable=True) # Take profit price
    parent_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True) # For SL/TP orders

    # Audit Trail
    created_by = Column(String(100), nullable=True)          # Who created the order
    modified_by = Column(String(100), nullable=True)         # Who last modified
    modification_reason = Column(Text, nullable=True)         # Reason for modification

    # Relationships
    account = relationship("Account", back_populates="orders")
    trades = relationship("Trade", back_populates="order")

    # Self-referential relationship for SL/TP
    child_orders = relationship("Order", backref=backref('parent_order', remote_side=[id]))
```

### Enhanced Trade Model

```python
class Trade(Base):
    """Enhanced Trade model with real trading details"""
    __tablename__ = "trades"

    # Existing fields
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    market = Column(String(10), nullable=False, default="CRYPTO")
    side = Column(String(10), nullable=False)
    price = Column(DECIMAL(18, 6), nullable=False)
    quantity = Column(DECIMAL(18, 8), nullable=False)
    commission = Column(DECIMAL(18, 6), nullable=False, default=0)
    trade_time = Column(TIMESTAMP, server_default=func.current_timestamp())

    # ========== NEW: REAL TRADING FIELDS ==========

    # Exchange Details
    exchange_trade_id = Column(String(100), nullable=True)   # Real exchange trade ID
    exchange_name = Column(String(50), nullable=True)        # Exchange where trade occurred
    exchange_timestamp = Column(TIMESTAMP, nullable=True)    # Exchange's timestamp

    # Fee Details
    exchange_fee_amount = Column(DECIMAL(18, 6), nullable=True)
    exchange_fee_currency = Column(String(10), nullable=True)
    exchange_fee_rate = Column(DECIMAL(8, 6), nullable=True) # Fee percentage

    # Financial Impact
    usd_value = Column(DECIMAL(18, 2), nullable=True)        # Trade value in USD
    price_impact = Column(DECIMAL(8, 6), nullable=True)      # Price impact in percentage
    slippage = Column(DECIMAL(8, 6), nullable=True)          # Slippage from expected price

    # Blockchain Details (for DEX trades)
    transaction_hash = Column(String(100), nullable=True)    # Blockchain transaction hash
    block_number = Column(Integer, nullable=True)            # Block number
    gas_used = Column(Integer, nullable=True)                # Gas used (for ETH trades)
    gas_price = Column(DECIMAL(18, 9), nullable=True)        # Gas price in Gwei

    # Settlement Details
    settlement_status = Column(String(20), nullable=True)    # "PENDING", "COMPLETED", "FAILED"
    settlement_time = Column(TIMESTAMP, nullable=True)        # When trade settled

    # Compliance and Audit
    compliance_checked = Column(String(10), nullable=False, default="false")
    compliance_notes = Column(Text, nullable=True)
    audit_trail = Column(Text, nullable=True)                 # JSON with audit data

    # Relationships
    order = relationship("Order", back_populates="trades")
```

## Migration Scripts

### Initial Migration Script

```python
# backend/migrations/001_add_real_trading_fields.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    """Add real trading fields to accounts table"""

    # Trading mode and exchange info
    op.add_column('accounts', sa.Column('trading_mode', sa.String(20), nullable=False, server_default='PAPER'))
    op.add_column('accounts', sa.Column('exchange_name', sa.String(50), nullable=True))

    # Encrypted credentials
    op.add_column('accounts', sa.Column('exchange_api_key_encrypted', sa.String(1000), nullable=True))
    op.add_column('accounts', sa.Column('exchange_api_secret_encrypted', sa.String(1000), nullable=True))
    op.add_column('accounts', sa.Column('exchange_passphrase_encrypted', sa.String(500), nullable=True))

    # Web3 wallet
    op.add_column('accounts', sa.Column('wallet_private_key_encrypted', sa.String(1000), nullable=True))
    op.add_column('accounts', sa.Column('wallet_address', sa.String(100), nullable=True))
    op.add_column('accounts', sa.Column('wallet_network', sa.String(20), nullable=True, server_default='ethereum'))

    # Risk management
    op.add_column('accounts', sa.Column('max_position_size', sa.Numeric(18, 2), nullable=True))
    op.add_column('accounts', sa.Column('max_daily_loss', sa.Numeric(18, 2), nullable=True))
    op.add_column('accounts', sa.Column('max_positions', sa.Integer, nullable=True))
    op.add_column('accounts', sa.Column('max_leverage', sa.Numeric(5, 2), nullable=True))

    # Safety controls
    op.add_column('accounts', sa.Column('emergency_stop', sa.String(10), nullable=False, server_default='false'))
    op.add_column('accounts', sa.Column('testnet_mode', sa.String(10), nullable=False, server_default='true'))
    op.add_column('accounts', sa.Column('require_confirmation', sa.String(10), nullable=False, server_default='true'))

    # Synchronization
    op.add_column('accounts', sa.Column('last_balance_sync', sa.TIMESTAMP(), nullable=True))
    op.add_column('accounts', sa.Column('sync_status', sa.String(20), nullable=True, server_default='pending'))
    op.add_column('accounts', sa.Column('real_balance_usd', sa.Numeric(18, 2), nullable=True))

    # Advanced settings
    op.add_column('accounts', sa.Column('trading_enabled', sa.String(10), nullable=False, server_default='false'))
    op.add_column('accounts', sa.Column('auto_rebalance', sa.String(10), nullable=False, server_default='false'))
    op.add_column('accounts', sa.Column('slippage_tolerance', sa.Numeric(5, 4), nullable=True))

    # Audit and compliance
    op.add_column('accounts', sa.Column('last_trade_at', sa.TIMESTAMP(), nullable=True))
    op.add_column('accounts', sa.Column('compliance_flags', sa.Text(), nullable=True))

    # Set default values for existing accounts
    op.execute("""
        UPDATE accounts SET
            max_position_size = 1000.00,
            max_daily_loss = 100.00,
            max_positions = 5,
            max_leverage = 1.0,
            slippage_tolerance = 0.0050
        WHERE max_position_size IS NULL
    """)

def downgrade():
    """Remove real trading fields"""

    # List of columns to drop
    columns_to_drop = [
        'trading_mode', 'exchange_name',
        'exchange_api_key_encrypted', 'exchange_api_secret_encrypted', 'exchange_passphrase_encrypted',
        'wallet_private_key_encrypted', 'wallet_address', 'wallet_network',
        'max_position_size', 'max_daily_loss', 'max_positions', 'max_leverage',
        'emergency_stop', 'testnet_mode', 'require_confirmation',
        'last_balance_sync', 'sync_status', 'real_balance_usd',
        'trading_enabled', 'auto_rebalance', 'slippage_tolerance',
        'last_trade_at', 'compliance_flags'
    ]

    for column in columns_to_drop:
        op.drop_column('accounts', column)
```

### New Tables Migration

```python
# backend/migrations/002_create_real_trading_tables.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    """Create new tables for real trading functionality"""

    # Create risk_logs table
    op.create_table('risk_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_severity', sa.String(20), nullable=False),
        sa.Column('event_message', sa.Text(), nullable=False),
        sa.Column('current_position_size', sa.Numeric(18, 2), nullable=True),
        sa.Column('current_daily_loss', sa.Numeric(18, 2), nullable=True),
        sa.Column('available_balance', sa.Numeric(18, 2), nullable=True),
        sa.Column('total_exposure', sa.Numeric(18, 2), nullable=True),
        sa.Column('action_taken', sa.String(100), nullable=True),
        sa.Column('action_result', sa.String(20), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_risk_logs_account_id', 'risk_logs', ['account_id'])
    op.create_index('ix_risk_logs_created_at', 'risk_logs', ['created_at'])

    # Create sync_logs table
    op.create_table('sync_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('sync_type', sa.String(20), nullable=False),
        sa.Column('sync_source', sa.String(50), nullable=False),
        sa.Column('sync_status', sa.String(20), nullable=False),
        sa.Column('balance_before', sa.Numeric(18, 2), nullable=True),
        sa.Column('positions_before', sa.Text(), nullable=True),
        sa.Column('balance_after', sa.Numeric(18, 2), nullable=True),
        sa.Column('positions_after', sa.Text(), nullable=True),
        sa.Column('sync_duration_ms', sa.Integer(), nullable=True),
        sa.Column('api_calls_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sync_logs_account_id', 'sync_logs', ['account_id'])
    op.create_index('ix_sync_logs_created_at', 'sync_logs', ['created_at'])

    # Create emergency_events table
    op.create_table('emergency_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('trigger_reason', sa.Text(), nullable=False),
        sa.Column('trigger_source', sa.String(50), nullable=True),
        sa.Column('trading_stopped', sa.String(10), nullable=False, server_default='true'),
        sa.Column('orders_cancelled', sa.String(10), nullable=False, server_default='false'),
        sa.Column('positions_liquidated', sa.String(10), nullable=False, server_default='false'),
        sa.Column('resolved', sa.String(10), nullable=False, server_default='false'),
        sa.Column('resolved_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('resolved_by', sa.String(100), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('orders_affected_count', sa.Integer(), nullable=True),
        sa.Column('positions_affected_count', sa.Integer(), nullable=True),
        sa.Column('financial_impact', sa.Numeric(18, 2), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_emergency_events_account_id', 'emergency_events', ['account_id'])
    op.create_index('ix_emergency_events_created_at', 'emergency_events', ['created_at'])

def downgrade():
    """Drop new tables"""
    op.drop_table('emergency_events')
    op.drop_table('sync_logs')
    op.drop_table('risk_logs')
```

## Database Configuration Updates

### Enhanced Database Connection

```python
# backend/database/connection.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backend/data.db")

# Enhanced engine configuration for production
if DATABASE_URL.startswith("postgresql"):
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=20,
        max_overflow=30,
        echo=os.getenv("DEBUG", "false").lower() == "true"
    )
else:
    # SQLite configuration for development
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 20
        },
        poolclass=StaticPool,
        echo=os.getenv("DEBUG", "false").lower() == "true"
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Database dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Database Backup and Security

```python
# backend/utils/backup_manager.py
import os
import subprocess
import logging
from datetime import datetime
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

class BackupManager:
    """Manage encrypted database backups"""

    def __init__(self, encryption_key: str):
        self.encryption_key = encryption_key
        self.cipher = Fernet(encryption_key)

    def create_backup(self, db_path: str, backup_dir: str) -> str:
        """Create encrypted database backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.db.enc"
            backup_path = os.path.join(backup_dir, backup_filename)

            # Create backup directory if it doesn't exist
            os.makedirs(backup_dir, exist_ok=True)

            # Read database file
            with open(db_path, 'rb') as f:
                db_data = f.read()

            # Encrypt and save
            encrypted_data = self.cipher.encrypt(db_data)
            with open(backup_path, 'wb') as f:
                f.write(encrypted_data)

            logger.info(f"Backup created: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            raise

    def restore_backup(self, backup_path: str, restore_path: str) -> bool:
        """Restore database from encrypted backup"""
        try:
            # Read and decrypt backup
            with open(backup_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = self.cipher.decrypt(encrypted_data)

            # Restore database
            with open(restore_path, 'wb') as f:
                f.write(decrypted_data)

            logger.info(f"Backup restored: {restore_path}")
            return True

        except Exception as e:
            logger.error(f"Backup restoration failed: {e}")
            return False
```

## Security Considerations

### 1. Data Encryption at Rest
- All sensitive credentials encrypted in database
- Database backups encrypted
- Database connections use SSL/TLS
- Row-level security for multi-tenant environments

### 2. Access Control
- Database access limited to application
- Separate read/write users for different operations
- Regular access log reviews
- IP whitelisting for database connections

### 3. Audit Trail
- All credential access logged
- Database change tracking enabled
- Regular integrity checks
- Compliance reporting capabilities

### 4. Backup Security
- Encrypted backups with rotation
- Off-site backup storage
- Regular restore testing
- Backup access logging

This database schema provides a solid foundation for real trading while maintaining security, auditability, and scalability.