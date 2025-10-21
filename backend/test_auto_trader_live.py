#!/usr/bin/env python3
"""
Live test script for auto_trader functionality
This script verifies that trades are being created by the auto-trader
"""

import time
import logging
from database.connection import SessionLocal
from database.models import User, Trade, Position
from services.auto_trader import place_random_crypto_order

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_database_state():
    """Check current database state"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        total_trades = db.query(Trade).count()
        
        logger.info(f"=== Database State ===")
        logger.info(f"Total users: {len(users)}")
        logger.info(f"Total trades: {total_trades}")
        
        for user in users:
            user_trades = db.query(Trade).filter(Trade.user_id == user.id).count()
            user_positions = db.query(Position).filter(Position.user_id == user.id).count()
            logger.info(f"User '{user.username}' (id={user.id}):")
            logger.info(f"  - Cash: ${user.current_cash:.2f}")
            logger.info(f"  - Trades: {user_trades}")
            logger.info(f"  - Positions: {user_positions}")
        
        return total_trades
    finally:
        db.close()


def test_auto_trader():
    """Test the auto trader by running it multiple times"""
    logger.info("Starting auto-trader test...")
    
    initial_trades = check_database_state()
    
    logger.info("\n=== Testing Auto Trader ===")
    logger.info("Running auto-trader 5 times...")
    
    for i in range(5):
        logger.info(f"\nAttempt {i+1}/5:")
        try:
            place_random_crypto_order(max_ratio=0.3)
            time.sleep(1)  # Wait a bit between attempts
        except Exception as e:
            logger.error(f"Error in attempt {i+1}: {e}")
    
    logger.info("\n=== Final State ===")
    final_trades = check_database_state()
    
    trades_created = final_trades - initial_trades
    logger.info(f"\n✓ Test complete! Created {trades_created} new trades")
    
    if trades_created > 0:
        logger.info("✓ SUCCESS: Auto-trader is working!")
        return True
    else:
        logger.warning("✗ WARNING: No trades were created. This might be normal if:")
        logger.warning("  1. Users have insufficient funds")
        logger.warning("  2. Market data API is unavailable")
        logger.warning("  3. Random selection didn't find valid trading opportunities")
        return False


if __name__ == "__main__":
    success = test_auto_trader()
    exit(0 if success else 1)
