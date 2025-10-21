import logging
import random
import json
from decimal import Decimal
from typing import Dict, Optional, Tuple, List

import requests
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import Position, User
from services.asset_calculator import calc_positions_value
from services.market_data import get_last_price
from services.order_matching import create_order, check_and_execute_order


logger = logging.getLogger(__name__)


SUPPORTED_SYMBOLS: Dict[str, str] = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "DOGE": "Dogecoin",
    "XRP": "Ripple",
    "BNB": "Binance Coin",
}

AI_TRADING_SYMBOLS: List[str] = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE"]


def _get_portfolio_data(db: Session, user: User) -> Dict:
    """Get current portfolio positions and values"""
    positions = db.query(Position).filter(
        Position.user_id == user.id,
        Position.market == "CRYPTO"
    ).all()
    
    portfolio = {}
    for pos in positions:
        if float(pos.quantity) > 0:
            portfolio[pos.symbol] = {
                "quantity": float(pos.quantity),
                "avg_cost": float(pos.avg_cost),
                "current_value": float(pos.quantity) * float(pos.avg_cost)
            }
    
    return {
        "cash": float(user.current_cash),
        "frozen_cash": float(user.frozen_cash),
        "positions": portfolio,
        "total_assets": float(user.current_cash) + calc_positions_value(db, user.id)
    }


def _get_market_prices(symbols: List[str]) -> Dict[str, float]:
    """Get latest prices for given symbols"""
    prices = {}
    for symbol in symbols:
        try:
            price = float(get_last_price(symbol, "CRYPTO"))
            if price > 0:
                prices[symbol] = price
        except Exception as err:
            logger.warning(f"Failed to get price for {symbol}: {err}")
    return prices


def _call_ai_for_decision(user: User, portfolio: Dict, prices: Dict[str, float]) -> Optional[Dict]:
    """Call AI model API to get trading decision"""
    try:
        prompt = f"""You are a cryptocurrency trading AI. Based on the following portfolio and market data, decide on a trading action.

Portfolio Data:
- Cash Available: ${portfolio['cash']:.2f}
- Frozen Cash: ${portfolio['frozen_cash']:.2f}
- Total Assets: ${portfolio['total_assets']:.2f}
- Current Positions: {json.dumps(portfolio['positions'], indent=2)}

Current Market Prices:
{json.dumps(prices, indent=2)}

Analyze the market and portfolio, then respond with ONLY a JSON object in this exact format:
{{
  "operation": "buy" or "sell" or "hold",
  "symbol": "BTC" or "ETH" or "SOL" or "BNB" or "XRP" or "DOGE",
  "target_portion_of_balance": 0.2,
  "reason": "Brief explanation of your decision"
}}

Rules:
- operation must be "buy", "sell", or "hold"
- For "buy": symbol is what to buy, target_portion_of_balance is % of cash to use (0.0-1.0)
- For "sell": symbol is what to sell, target_portion_of_balance is % of position to sell (0.0-1.0)
- For "hold": no action taken
- Keep target_portion_of_balance between 0.1 and 0.3 for risk management
- Only choose symbols you have data for"""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {user.api_key}"
        }
        
        payload = {
            "model": user.model,
            "input": prompt,
            "response_format": "text"
        }
        
        response = requests.post(
            f"{user.base_url}/responses",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"AI API returned status {response.status_code}: {response.text}")
            return None
        
        result = response.json()
        
        # Extract text from response
        if "output" in result and len(result["output"]) > 0:
            output_item = result["output"][0]
            if "content" in output_item and len(output_item["content"]) > 0:
                text_content = output_item["content"][0].get("text", "")
                
                # Try to extract JSON from the text
                # Sometimes AI might wrap JSON in markdown code blocks
                text_content = text_content.strip()
                if "```json" in text_content:
                    text_content = text_content.split("```json")[1].split("```")[0].strip()
                elif "```" in text_content:
                    text_content = text_content.split("```")[1].split("```")[0].strip()
                
                decision = json.loads(text_content)
                logger.info(f"AI decision for {user.username}: {decision}")
                return decision
        
        logger.error(f"Unexpected AI response format: {result}")
        return None
        
    except requests.RequestException as err:
        logger.error(f"AI API request failed: {err}")
        return None
    except json.JSONDecodeError as err:
        logger.error(f"Failed to parse AI response as JSON: {err}")
        return None
    except Exception as err:
        logger.error(f"Unexpected error calling AI: {err}")
        return None


def _choose_user(db: Session) -> Optional[User]:
    users = db.query(User).all()
    if not users:
        return None
    return random.choice(users)


def _select_side(db: Session, user: User, symbol: str, max_value: float) -> Optional[Tuple[str, int]]:
    market = "CRYPTO"
    try:
        price = float(get_last_price(symbol, market))
    except Exception as err:
        logger.warning("Cannot get price for %s: %s", symbol, err)
        return None

    if price <= 0:
        logger.debug("%s returned non-positive price %s", symbol, price)
        return None

    max_quantity_by_value = int(Decimal(str(max_value)) // Decimal(str(price)))
    position = (
        db.query(Position)
        .filter(Position.user_id == user.id, Position.symbol == symbol, Position.market == market)
        .first()
    )
    available_quantity = int(position.available_quantity) if position else 0

    choices = []

    if float(user.current_cash) >= price and max_quantity_by_value >= 1:
        choices.append(("BUY", max_quantity_by_value))

    if available_quantity > 0:
        max_sell_quantity = min(available_quantity, max_quantity_by_value if max_quantity_by_value >= 1 else available_quantity)
        if max_sell_quantity >= 1:
            choices.append(("SELL", max_sell_quantity))

    if not choices:
        return None

    side, max_qty = random.choice(choices)
    quantity = random.randint(1, max_qty)
    return side, quantity


def place_ai_driven_crypto_order(max_ratio: float = 0.2) -> None:
    """Place crypto order based on AI model decision"""
    db = SessionLocal()
    try:
        user = _choose_user(db)
        if not user:
            logger.debug("No available users, skipping AI trading")
            return

        # Get portfolio data
        portfolio = _get_portfolio_data(db, user)
        
        if portfolio['total_assets'] <= 0:
            logger.debug(f"User {user.username} has non-positive total assets, skipping")
            return

        # Get latest market prices
        prices = _get_market_prices(AI_TRADING_SYMBOLS)
        if not prices:
            logger.warning("Failed to fetch market prices, skipping AI trading")
            return

        # Call AI for trading decision
        decision = _call_ai_for_decision(user, portfolio, prices)
        if not decision:
            logger.warning(f"Failed to get AI decision for {user.username}, skipping")
            return

        operation = decision.get("operation", "").lower()
        symbol = decision.get("symbol", "").upper()
        target_portion = float(decision.get("target_portion_of_balance", 0))
        reason = decision.get("reason", "No reason provided")

        logger.info(f"AI decision for {user.username}: {operation} {symbol} (portion: {target_portion:.2%}) - {reason}")

        # Validate decision
        if operation not in ["buy", "sell", "hold"]:
            logger.warning(f"Invalid operation '{operation}' from AI, skipping")
            return
        
        if operation == "hold":
            logger.info(f"AI decided to HOLD for {user.username}")
            return

        if symbol not in SUPPORTED_SYMBOLS:
            logger.warning(f"Invalid symbol '{symbol}' from AI, skipping")
            return

        if target_portion <= 0 or target_portion > 1:
            logger.warning(f"Invalid target_portion {target_portion} from AI, skipping")
            return

        # Get current price
        price = prices.get(symbol)
        if not price or price <= 0:
            logger.warning(f"Invalid price for {symbol}, skipping")
            return

        # Calculate quantity based on operation
        if operation == "buy":
            # Calculate quantity based on available cash and target portion
            available_cash = float(user.current_cash)
            order_value = available_cash * target_portion
            quantity = int(Decimal(str(order_value)) // Decimal(str(price)))
            
            if quantity < 1:
                logger.info(f"Calculated BUY quantity < 1 for {symbol}, skipping")
                return
            
            side = "BUY"

        elif operation == "sell":
            # Calculate quantity based on position and target portion
            position = (
                db.query(Position)
                .filter(Position.user_id == user.id, Position.symbol == symbol, Position.market == "CRYPTO")
                .first()
            )
            
            if not position or float(position.available_quantity) <= 0:
                logger.info(f"No position available to SELL for {symbol}, skipping")
                return
            
            available_quantity = int(position.available_quantity)
            quantity = max(1, int(available_quantity * target_portion))
            
            if quantity > available_quantity:
                quantity = available_quantity
            
            side = "SELL"
        
        else:
            return

        # Create and execute order
        name = SUPPORTED_SYMBOLS[symbol]
        
        order = create_order(
            db=db,
            user=user,
            symbol=symbol,
            name=name,
            market="CRYPTO",
            side=side,
            order_type="MARKET",
            price=None,
            quantity=quantity,
        )

        db.commit()
        db.refresh(order)

        executed = check_and_execute_order(db, order)
        if executed:
            db.refresh(order)
            logger.info(
                f"AI order executed: user={user.username} {side} {symbol} {order.order_no} "
                f"quantity={quantity} reason='{reason}'"
            )
        else:
            logger.info(
                f"AI order created: user={user.username} {side} {symbol} "
                f"quantity={quantity} order_id={order.order_no} reason='{reason}'"
            )

    except Exception as err:
        logger.error(f"AI-driven order placement failed: {err}", exc_info=True)
        db.rollback()
    finally:
        db.close()


def place_random_crypto_order(max_ratio: float = 0.2) -> None:
    """Legacy random order placement (kept for backward compatibility)"""
    db = SessionLocal()
    try:
        user = _choose_user(db)
        if not user:
            logger.debug("No available users, skipping auto order placement")
            return

        positions_value = calc_positions_value(db, user.id)
        total_assets = positions_value + float(user.current_cash)

        if total_assets <= 0:
            logger.debug("User %s total assets non-positive, skipping auto order placement", user.username)
            return

        max_order_value = total_assets * max_ratio
        if max_order_value <= 0:
            logger.debug("User %s maximum order amount is 0, skipping", user.username)
            return

        symbol = random.choice(list(SUPPORTED_SYMBOLS.keys()))
        side_info = _select_side(db, user, symbol, max_order_value)
        if not side_info:
            logger.debug("User %s has no executable direction for %s, skipping", user.username, symbol)
            return

        side, quantity = side_info
        name = SUPPORTED_SYMBOLS[symbol]

        order = create_order(
            db=db,
            user=user,
            symbol=symbol,
            name=name,
            market="CRYPTO",
            side=side,
            order_type="MARKET",
            price=None,
            quantity=quantity,
        )

        db.commit()
        db.refresh(order)

        executed = check_and_execute_order(db, order)
        if executed:
            db.refresh(order)
            logger.info("Auto order executed: user=%s %s %s %s quantity=%s", user.username, side, symbol, order.order_no, quantity)
        else:
            logger.info("Auto order created: user=%s %s %s quantity=%s order_id=%s", user.username, side, symbol, quantity, order.order_no)

    except Exception as err:
        logger.error("Auto order placement failed: %s", err)
        db.rollback()
    finally:
        db.close()


AUTO_TRADE_JOB_ID = "auto_crypto_trade"
AI_TRADE_JOB_ID = "ai_crypto_trade"


def schedule_auto_trading(interval_seconds: int = 300, max_ratio: float = 0.2, use_ai: bool = True) -> None:
    """Schedule automatic trading tasks
    
    Args:
        interval_seconds: Interval between trading attempts
        max_ratio: Maximum portion of portfolio to use per trade
        use_ai: If True, use AI-driven trading; if False, use random trading
    """
    from services.scheduler import task_scheduler

    if use_ai:
        task_func = place_ai_driven_crypto_order
        job_id = AI_TRADE_JOB_ID
        logger.info("Scheduling AI-driven crypto trading")
    else:
        task_func = place_random_crypto_order
        job_id = AUTO_TRADE_JOB_ID
        logger.info("Scheduling random crypto trading")

    task_scheduler.add_interval_task(
        task_func=task_func,
        interval_seconds=interval_seconds,
        task_id=job_id,
        max_ratio=max_ratio,
    )
