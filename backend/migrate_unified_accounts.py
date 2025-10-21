"""
Migration script to create unified AI Trader Account system
Drops old database and creates new schema with merged User/AIAccount tables
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import Base, engine
from database.models import User, TradingConfig, SystemConfig

def migrate_to_unified_accounts():
    """Create new database with unified AI trader accounts"""
    
    print("=" * 60)
    print("UNIFIED AI TRADER ACCOUNT MIGRATION")
    print("=" * 60)
    print("\nThis will:")
    print("1. Drop all existing tables")
    print("2. Create new schema with unified User model")
    print("3. Merge trading accounts and AI accounts into one")
    print("4. Create sample AI trader accounts")
    print("\n" + "=" * 60)
    
    # Drop all tables
    print("\n[1/4] Dropping all existing tables...")
    Base.metadata.drop_all(bind=engine)
    print("✓ All tables dropped")
    
    # Create new schema
    print("\n[2/4] Creating new schema with unified accounts...")
    Base.metadata.create_all(bind=engine)
    print("✓ New schema created")
    
    # Create session
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Create trading config for CRYPTO market
        print("\n[3/4] Creating trading configuration...")
        trading_config = TradingConfig(
            version="v1",
            market="CRYPTO",
            min_commission=0.1,
            commission_rate=0.001,
            exchange_rate=1.0,
            min_order_quantity=1,
            lot_size=1
        )
        db.add(trading_config)
        db.commit()
        print("✓ Trading config created for CRYPTO market")
        
        # Create sample AI trader accounts
        print("\n[4/4] Creating sample AI trader accounts...")
        
        sample_accounts = [
            {
                "username": "GPT",
                "model": "gpt-4-turbo",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-demo-key-replace-with-real-key",
                "initial_capital": 10000.00,
                "current_cash": 10000.00,
                "frozen_cash": 0.00
            },
            {
                "username": "Claude",
                "model": "claude-3-opus",
                "base_url": "https://api.anthropic.com/v1",
                "api_key": "sk-ant-demo-key-replace-with-real-key",
                "initial_capital": 10000.00,
                "current_cash": 10000.00,
                "frozen_cash": 0.00
            },
            {
                "username": "Gemini",
                "model": "gemini-pro",
                "base_url": "https://generativelanguage.googleapis.com/v1",
                "api_key": "demo-gemini-key-replace-with-real-key",
                "initial_capital": 10000.00,
                "current_cash": 10000.00,
                "frozen_cash": 0.00
            }
        ]
        
        for account_data in sample_accounts:
            account = User(**account_data)
            db.add(account)
            print(f"  ✓ Created AI trader: {account_data['username']} ({account_data['model']})")
        
        db.commit()
        
        print("\n" + "=" * 60)
        print("MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nCreated AI Trader Accounts:")
        
        accounts = db.query(User).all()
        for acc in accounts:
            print(f"\n  Account: {acc.username}")
            print(f"    Model: {acc.model}")
            print(f"    URL: {acc.base_url}")
            print(f"    Capital: ${acc.initial_capital}")
            print(f"    Cash: ${acc.current_cash}")
        
        print("\n" + "=" * 60)
        print("\nNext steps:")
        print("1. Update API keys in Settings dialog")
        print("2. Start trading with AI agents!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_to_unified_accounts()
