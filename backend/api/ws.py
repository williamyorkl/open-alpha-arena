from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import Dict, Set
import json

from database.connection import SessionLocal
from repositories.user_repo import get_or_create_user, get_user
from repositories.account_repo import get_or_create_default_account, get_account
from repositories.order_repo import list_orders
from repositories.position_repo import list_positions
from services.asset_calculator import calc_positions_value
from services.market_data import get_last_price
from services.scheduler import add_account_snapshot_job, remove_account_snapshot_job
from database.models import Trade, User, Account, CryptoPrice, AIDecisionLog
from sqlalchemy import func
from datetime import datetime, timedelta, date
import logging


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        pass  # WebSocket is already accepted in the endpoint

    def register(self, account_id: int, websocket: WebSocket):
        self.active_connections.setdefault(account_id, set()).add(websocket)
        # Add scheduled snapshot task for new account
        add_account_snapshot_job(account_id, interval_seconds=10)

    def unregister(self, account_id: int, websocket: WebSocket):
        if account_id in self.active_connections:
            self.active_connections[account_id].discard(websocket)
            if not self.active_connections[account_id]:
                del self.active_connections[account_id]
                # Remove the scheduled task for this account
                remove_account_snapshot_job(account_id)

    async def send_to_account(self, account_id: int, message: dict):
        if account_id not in self.active_connections:
            return
        payload = json.dumps(message, ensure_ascii=False)
        for ws in list(self.active_connections[account_id]):
            try:
                await ws.send_text(payload)
            except Exception:
                # remove broken connection
                self.active_connections[account_id].discard(ws)


manager = ConnectionManager()


def get_all_asset_curves_data(db: Session):
    """Get asset curve data for all accounts - WebSocket version"""
    try:
        # Get all accounts
        accounts = db.query(Account).all()
        if not accounts:
            return []

        all_curve_data = []

        for account in accounts:
            try:
                # Get first trade time
                first_trade = db.query(Trade).filter(Trade.account_id == account.id).order_by(Trade.trade_time.asc()).first()

                if not first_trade:
                    # If no trading records, return initial capital point
                    all_curve_data.append({
                        "date": datetime.now().date().isoformat(),
                        "total_assets": float(account.initial_capital),
                        "cash": float(account.current_cash),
                        "positions_value": 0.0,
                        "is_initial": True,
                        "user_id": account.user_id,
                        "username": account.name
                    })
                    continue

                # First point: day before first trade, value is initial capital
                first_trade_date = first_trade.trade_time.date()
                start_date = first_trade_date - timedelta(days=1)

                # Add starting point
                all_curve_data.append({
                    "date": start_date.isoformat(),
                    "total_assets": float(account.initial_capital),
                    "cash": float(account.initial_capital),
                    "positions_value": 0.0,
                    "is_initial": True,
                    "user_id": account.user_id,
                    "username": account.name
                })

                # Get all trading dates (dates with trades)
                trade_dates = db.query(func.date(Trade.trade_time).label('trade_date')).filter(
                    Trade.account_id == account.id
                ).distinct().order_by('trade_date').all()

                # Get all dates with price data
                price_dates = db.query(CryptoPrice.price_date).distinct().order_by(CryptoPrice.price_date).all()

                # Merge and deduplicate all relevant dates
                all_dates = set()
                for td in trade_dates:
                    # Handle different types of date objects
                    if hasattr(td, 'trade_date'):
                        trade_date = td.trade_date
                    else:
                        trade_date = td[0]  # When using label, the result is a tuple

                    if isinstance(trade_date, str):
                        trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
                    elif hasattr(trade_date, 'date'):
                        trade_date = trade_date.date()

                    all_dates.add(trade_date)

                for pd in price_dates:
                    # Process price dates
                    if hasattr(pd, 'price_date'):
                        price_date = pd.price_date
                    else:
                        price_date = pd[0]

                    if isinstance(price_date, str):
                        price_date = datetime.strptime(price_date, '%Y-%m-%d').date()
                    elif hasattr(price_date, 'date'):
                        price_date = price_date.date()

                    all_dates.add(price_date)


                relevant_dates = sorted([d for d in all_dates if d >= first_trade_date])

                for target_date in relevant_dates:
                    try:
                        # Calculate cash changes up to the target date
                        cash_changes = _calculate_cash_changes_up_to_date(db, account.id, target_date)
                        current_cash = float(account.initial_capital) + cash_changes

                        # Calculate position value on the target date
                        positions_value = _calculate_positions_value_on_date(db, account.id, target_date)

                        total_assets = current_cash + positions_value

                        all_curve_data.append({
                            "date": target_date.isoformat(),
                            "total_assets": total_assets,
                            "cash": current_cash,
                            "positions_value": positions_value,
                            "is_initial": False,
                            "user_id": account.user_id,
                            "username": account.name
                        })

                    except Exception as e:
                        logging.warning(f"Failed to calculate assets for account {account.id} on date {target_date}: {e}")
                        continue

            except Exception as e:
                logging.warning(f"Failed to process asset curve for account {account.id}: {e}")
                continue

        return all_curve_data

    except Exception as e:
        logging.error(f"Failed to get asset curves for all users: {e}")
        return []


def _calculate_cash_changes_up_to_date(db: Session, account_id: int, target_date: date) -> float:
    """Calculate cash changes up to the specified date"""
    try:
        # Calculate the impact of all trades on cash up to the target date
        trades = db.query(Trade).filter(
            Trade.account_id == account_id,
            func.date(Trade.trade_time) <= target_date
        ).all()

        cash_changes = 0.0
        for trade in trades:
            if trade.side == 'BUY':
                # Buy: cash decreases (price * quantity + commission)
                cash_changes -= (float(trade.price) * float(trade.quantity) + float(trade.commission))
            else:  # SELL
                # Sell: cash increases (price * quantity - commission)
                cash_changes += (float(trade.price) * float(trade.quantity) - float(trade.commission))

        return cash_changes
    except Exception as e:
        logging.error(f"Failed to calculate cash changes: {e}")
        return 0.0


def _calculate_positions_value_on_date(db: Session, account_id: int, target_date: date) -> float:
    """Calculate position value on the specified date"""
    try:
        # 获取到该日期为止的所有交易
        trades = db.query(Trade).filter(
            Trade.account_id == account_id,
            func.date(Trade.trade_time) <= target_date
        ).order_by(Trade.trade_time).all()

        # 计算持仓
        positions = {}
        for trade in trades:
            symbol_key = f"{trade.symbol}.{trade.market}"
            if symbol_key not in positions:
                positions[symbol_key] = 0.0

            if trade.side == 'BUY':
                positions[symbol_key] += float(trade.quantity)
            else:  # SELL
                positions[symbol_key] -= float(trade.quantity)

        # 计算持仓价值
        total_value = 0.0
        for symbol_key, quantity in positions.items():
            if quantity > 0:  # 只计算正持仓
                symbol, market = symbol_key.split('.')
                try:
                    # 获取该日期的价格
                    price_record = db.query(CryptoPrice).filter(
                        CryptoPrice.symbol == symbol,
                        CryptoPrice.market == market,
                        CryptoPrice.price_date <= target_date
                    ).order_by(CryptoPrice.price_date.desc()).first()

                    if price_record:
                        price = float(price_record.price)
                        total_value += price * quantity
                except Exception as e:
                    logging.warning(f"获取 {symbol_key} 在 {target_date} 的价格失败: {e}")
                    continue

        return total_value
    except Exception as e:
        logging.error(f"计算持仓价值失败: {e}")
        return 0.0


manager = ConnectionManager()


async def _send_snapshot(db: Session, account_id: int):
    account = get_account(db, account_id)
    if not account:
        return
    positions = list_positions(db, account_id)
    orders = list_orders(db, account_id)
    trades = (
        db.query(Trade).filter(Trade.account_id == account_id).order_by(Trade.trade_time.desc()).limit(20).all()
    )
    ai_decisions = (
        db.query(AIDecisionLog).filter(AIDecisionLog.account_id == account_id).order_by(AIDecisionLog.decision_time.desc()).limit(20).all()
    )
    positions_value = calc_positions_value(db, account_id)

    overview = {
        "account": {
            "id": account.id,
            "user_id": account.user_id,
            "name": account.name,
            "account_type": account.account_type,
            "initial_capital": float(account.initial_capital),
            "current_cash": float(account.current_cash),
            "frozen_cash": float(account.frozen_cash),
        },
        "total_assets": positions_value + float(account.current_cash),
        "positions_value": positions_value,
    }
    # enrich positions with latest price and market value
    enriched_positions = []
    price_error_message = None

    for p in positions:
        try:
            price = get_last_price(p.symbol, p.market)
        except Exception as e:
            price = None
            # 收集价格获取错误信息，特别是cookie相关的错误
            error_msg = str(e)
            if "cookie" in error_msg.lower() and price_error_message is None:
                price_error_message = error_msg

        enriched_positions.append({
            "id": p.id,
            "account_id": p.account_id,
            "symbol": p.symbol,
            "name": p.name,
            "market": p.market,
            "quantity": float(p.quantity),
            "available_quantity": float(p.available_quantity),
            "avg_cost": float(p.avg_cost),
            "last_price": float(price) if price is not None else None,
            "market_value": (float(price) * float(p.quantity)) if price is not None else None,
        })

    # 准备响应数据
    response_data = {
        "type": "snapshot",
        "overview": overview,
        "positions": enriched_positions,
        "orders": [
            {
                "id": o.id,
                "order_no": o.order_no,
                "user_id": o.account_id,
                "symbol": o.symbol,
                "name": o.name,
                "market": o.market,
                "side": o.side,
                "order_type": o.order_type,
                "price": float(o.price) if o.price is not None else None,
                "quantity": float(o.quantity),
                "filled_quantity": float(o.filled_quantity),
                "status": o.status,
            }
            for o in orders[:20]
        ],
        "trades": [
            {
                "id": t.id,
                "order_id": t.order_id,
                "user_id": t.account_id,
                "symbol": t.symbol,
                "name": t.name,
                "market": t.market,
                "side": t.side,
                "price": float(t.price),
                "quantity": float(t.quantity),
                "commission": float(t.commission),
                "trade_time": str(t.trade_time),
            }
            for t in trades
        ],
        "ai_decisions": [
            {
                "id": d.id,
                "decision_time": str(d.decision_time),
                "reason": d.reason,
                "operation": d.operation,
                "symbol": d.symbol,
                "prev_portion": float(d.prev_portion),
                "target_portion": float(d.target_portion),
                "total_balance": float(d.total_balance),
                "executed": d.executed,
                "order_id": d.order_id,
            }
            for d in ai_decisions
        ],
        "all_asset_curves": get_all_asset_curves_data(db),  # 添加所有账户的资产曲线数据
    }

    # 如果有价格获取错误，添加警告信息
    if price_error_message:
        response_data["warning"] = {
            "type": "market_data_error",
            "message": price_error_message
        }

    await manager.send_to_account(account_id, response_data)


async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    account_id: int | None = None
    user_id: int | None = None  # Initialize user_id to avoid UnboundLocalError

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            kind = msg.get("type")
            db: Session = SessionLocal()
            try:
                if kind == "bootstrap":
                    #  mode: Create or get default default user
                    username = msg.get("username", "default")
                    user = get_or_create_user(db, username)
                    
                    # Get or create default account for this user
                    account = get_or_create_default_account(
                        db, 
                        user.id,
                        account_name=f"{username} AI Trader",
                        initial_capital=float(msg.get("initial_capital", 100000))
                    )
                    account_id = account.id
                    manager.register(account_id, websocket)
                    
                    # Send bootstrap confirmation with account info
                    await manager.send_to_account(account_id, {
                        "type": "bootstrap_ok", 
                        "user": {"id": user.id, "username": user.username},
                        "account": {"id": account.id, "name": account.name, "user_id": account.user_id}
                    })
                    await _send_snapshot(db, account_id)
                elif kind == "subscribe":
                    # subscribe existing user_id
                    uid = int(msg.get("user_id"))
                    u = get_user(db, uid)
                    if not u:
                        await websocket.send_text(json.dumps({"type": "error", "message": "user not found"}))
                        continue
                    user_id = uid
                    manager.register(user_id, websocket)
                    await _send_snapshot(db, user_id)
                elif kind == "switch_user":
                    # Switch to different user account
                    target_username = msg.get("username")
                    if not target_username:
                        await websocket.send_text(json.dumps({"type": "error", "message": "username required"}))
                        continue

                    # Unregister from current user if any
                    if user_id is not None:
                        manager.unregister(user_id, websocket)

                    # Find target user
                    target_user = get_or_create_user(db, target_username, 100000.0)
                    user_id = target_user.id

                    # Register to new user
                    manager.register(user_id, websocket)

                    # Send confirmation and snapshot
                    await manager.send_to_user(user_id, {
                        "type": "user_switched",
                        "user": {
                            "id": target_user.id,
                            "username": target_user.username
                        }
                    })
                    await _send_snapshot(db, user_id)
                elif kind == "switch_account":
                    # Switch to different account by ID
                    target_account_id = msg.get("account_id")
                    if not target_account_id:
                        await websocket.send_text(json.dumps({"type": "error", "message": "account_id required"}))
                        continue

                    # Unregister from current account if any
                    if account_id is not None:
                        manager.unregister(account_id, websocket)

                    # Get target account
                    target_account = get_account(db, target_account_id)
                    if not target_account:
                        await websocket.send_text(json.dumps({"type": "error", "message": "account not found"}))
                        continue

                    account_id = target_account.id
                    
                    # Register to new account
                    manager.register(account_id, websocket)

                    # Send confirmation and snapshot
                    await manager.send_to_account(account_id, {
                        "type": "account_switched",
                        "account": {
                            "id": target_account.id,
                            "user_id": target_account.user_id,
                            "name": target_account.name
                        }
                    })
                    await _send_snapshot(db, account_id)
                elif kind == "get_snapshot":
                    if account_id is not None:
                        await _send_snapshot(db, account_id)
                elif kind == "place_order":
                    if account_id is None:
                        await websocket.send_text(json.dumps({"type": "error", "message": "not authenticated"}))
                        continue

                    try:
                        # Import the order creation service
                        from services.order_matching import create_order

                        # Get account and user object
                        account = get_account(db, account_id)
                        if not account:
                            await websocket.send_text(json.dumps({"type": "error", "message": "account not found"}))
                            continue

                        user = get_user(db, account.user_id)
                        if not user:
                            await websocket.send_text(json.dumps({"type": "error", "message": "user not found"}))
                            continue

                        # Extract order parameters
                        symbol = msg.get("symbol")
                        name = msg.get("name", symbol)  # Use symbol as name if not provided
                        market = msg.get("market", "US")
                        side = msg.get("side")
                        order_type = msg.get("order_type")
                        price = msg.get("price")
                        quantity = msg.get("quantity")

                        # Validate required parameters
                        if not all([symbol, side, order_type, quantity]):
                            await websocket.send_text(json.dumps({"type": "error", "message": "missing required parameters"}))
                            continue

                        # Convert quantity to int
                        try:
                            quantity = int(quantity)
                        except (ValueError, TypeError):
                            await websocket.send_text(json.dumps({"type": "error", "message": "invalid quantity"}))
                            continue

                        # Create the order
                        order = create_order(
                            db=db,
                            user=user,
                            symbol=symbol,
                            name=name,
                            market=market,
                            side=side,
                            order_type=order_type,
                            price=price,
                            quantity=quantity
                        )

                        # Commit the order
                        db.commit()

                        # Send success response
                        await manager.send_to_account(account_id, {"type": "order_pending", "order_id": order.id})

                        # Send updated snapshot
                        await _send_snapshot(db, account_id)

                    except ValueError as e:
                        # Business logic errors (insufficient funds, etc.)
                        await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
                    except Exception as e:
                        # Unexpected errors
                        import traceback
                        print(f"Order placement error: {e}")
                        print(traceback.format_exc())
                        await websocket.send_text(json.dumps({"type": "error", "message": f"order placement failed: {str(e)}"}))
                elif kind == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                else:
                    await websocket.send_text(json.dumps({"type": "error", "message": "unknown message"}))
            finally:
                db.close()
    except WebSocketDisconnect:
        if account_id is not None:
            manager.unregister(account_id, websocket)
        if user_id is not None:
            manager.unregister(user_id, websocket)
        return
    finally:
        # Clean up resources when user disconnects
        if account_id is not None:
            manager.unregister(account_id, websocket)
        if user_id is not None:
            manager.unregister(user_id, websocket)
