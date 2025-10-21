"""Test script for AI-driven auto trader"""

import logging
from database.connection import SessionLocal
from database.models import User
from services.auto_trader import place_ai_driven_crypto_order

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_ai_trader():
    """Test AI-driven trading with a sample user"""
    db = SessionLocal()
    try:
        # Check if any users exist
        users = db.query(User).all()
        if not users:
            logger.error("No users found in database. Please create an AI account first.")
            return
        
        logger.info(f"Found {len(users)} user(s) in database")
        for user in users:
            logger.info(f"  - {user.username} (model: {user.model}, base_url: {user.base_url})")
        
        # Test AI trading
        logger.info("\n" + "="*60)
        logger.info("Running AI-driven crypto order placement...")
        logger.info("="*60 + "\n")
        
        place_ai_driven_crypto_order(max_ratio=0.2)
        
        logger.info("\n" + "="*60)
        logger.info("AI trading test completed")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    test_ai_trader()
