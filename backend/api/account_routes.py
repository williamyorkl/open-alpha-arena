"""
账户与持仓 API 路由
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import logging

from database.connection import SessionLocal
from database.models import User, Position, Trade, CryptoPrice
from repositories.user_repo import get_user
from repositories.position_repo import list_positions
from services.asset_calculator import calc_positions_value
from schemas.user import (
    UserOut, UserCreate, UserUpdate, AccountOverview
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/account", tags=["account"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/overview")
async def get_overview(user_id: int, db: Session = Depends(get_db)):
    """获取账户资金概览"""
    try:
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        positions_value = calc_positions_value(db, user_id)
        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "model": user.model,
                "base_url": user.base_url,
                "api_key": user.api_key[:20] + "..." if len(user.api_key) > 20 else user.api_key,
                "initial_capital": float(user.initial_capital),
                "current_cash": float(user.current_cash),
                "frozen_cash": float(user.frozen_cash),
            },
            "total_assets": positions_value + float(user.current_cash),
            "positions_value": positions_value,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取账户概览失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取账户概览失败: {str(e)}")


@router.get("/positions")
async def get_positions(user_id: int, db: Session = Depends(get_db)):
    """获取用户持仓列表"""
    try:
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        positions = list_positions(db, user_id)
        return [
            {
                "id": p.id,
                "user_id": p.user_id,
                "symbol": p.symbol,
                "name": p.name,
                "market": p.market,
                "quantity": p.quantity,
                "available_quantity": p.available_quantity,
                "avg_cost": float(p.avg_cost),
            }
            for p in positions
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取持仓失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取持仓失败: {str(e)}")


@router.get("/asset-curve")
async def get_asset_curve(user_id: int, db: Session = Depends(get_db)):
    """获取用户资产曲线数据"""
    try:
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 获取第一笔成交时间
        first_trade = db.query(Trade).filter(Trade.user_id == user_id).order_by(Trade.trade_time.asc()).first()
        
        if not first_trade:
            # 如果没有成交记录，返回初始资金点
            return [{
                "date": datetime.now().date().isoformat(),
                "total_assets": float(user.initial_capital),
                "cash": float(user.current_cash),
                "positions_value": 0.0,
                "is_initial": True
            }]
        
        # 第一个点：第一笔成交前一天，值为初始资金
        first_trade_date = first_trade.trade_time.date()
        start_date = first_trade_date - timedelta(days=1)
        
        curve_data = []
        
        # 添加起始点
        curve_data.append({
            "date": start_date.isoformat(),
            "total_assets": float(user.initial_capital),
            "cash": float(user.initial_capital),
            "positions_value": 0.0,
            "is_initial": True
        })
        
        # 获取所有交易日期（有成交的日期）
        trade_dates = db.query(func.date(Trade.trade_time).label('trade_date')).filter(
            Trade.user_id == user_id
        ).distinct().order_by('trade_date').all()
        
        # 获取所有有价格数据的日期
        price_dates = db.query(CryptoPrice.price_date).distinct().order_by(CryptoPrice.price_date).all()
        
        # 合并并去重所有相关日期
        all_dates = set()
        for td in trade_dates:
            # 处理不同类型的日期对象
            if hasattr(td, 'trade_date'):
                trade_date = td.trade_date
            else:
                trade_date = td[0]  # 当使用label时，结果是元组
            
            if isinstance(trade_date, str):
                trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
            elif hasattr(trade_date, 'date'):
                trade_date = trade_date.date()
            
            all_dates.add(trade_date)
            
        for pd in price_dates:
            # 处理价格日期
            if hasattr(pd, 'price_date'):
                price_date = pd.price_date
            else:
                price_date = pd[0]
                
            if isinstance(price_date, str):
                price_date = datetime.strptime(price_date, '%Y-%m-%d').date()
            elif hasattr(price_date, 'date'):
                price_date = price_date.date()
                
            all_dates.add(price_date)
        
        # 过滤出第一笔成交日期之后的日期
        relevant_dates = sorted([d for d in all_dates if d >= first_trade_date])
        
        for target_date in relevant_dates:
            try:
                # 计算到该日期为止的现金变化
                cash_changes = _calculate_cash_changes_up_to_date(db, user_id, target_date)
                current_cash = float(user.initial_capital) + cash_changes
                
                # 计算该日期的持仓价值
                positions_value = _calculate_positions_value_on_date(db, user_id, target_date)
                
                total_assets = current_cash + positions_value
                
                curve_data.append({
                    "date": target_date.isoformat(),
                    "total_assets": total_assets,
                    "cash": current_cash,
                    "positions_value": positions_value,
                    "is_initial": False
                })
                
            except Exception as e:
                logger.warning(f"计算日期 {target_date} 的资产失败: {e}")
                continue
        
        return curve_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取资产曲线失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取资产曲线失败: {str(e)}")


def get_all_asset_curves_data(db: Session):
    """获取所有用户的资产曲线数据 - 辅助函数"""
    try:
        # 获取所有用户
        users = db.query(User).all()
        if not users:
            return []
        
        all_curve_data = []
        
        for user in users:
            try:
                # 获取第一笔成交时间
                first_trade = db.query(Trade).filter(Trade.user_id == user.id).order_by(Trade.trade_time.asc()).first()
                
                if not first_trade:
                    # 如果没有成交记录，返回初始资金点
                    all_curve_data.append({
                        "date": datetime.now().date().isoformat(),
                        "total_assets": float(user.initial_capital),
                        "cash": float(user.current_cash),
                        "positions_value": 0.0,
                        "is_initial": True,
                        "user_id": user.id,
                        "username": user.username
                    })
                    continue
                
                # 第一个点：第一笔成交前一天，值为初始资金
                first_trade_date = first_trade.trade_time.date()
                start_date = first_trade_date - timedelta(days=1)
                
                # 添加起始点
                all_curve_data.append({
                    "date": start_date.isoformat(),
                    "total_assets": float(user.initial_capital),
                    "cash": float(user.initial_capital),
                    "positions_value": 0.0,
                    "is_initial": True,
                    "user_id": user.id,
                    "username": user.username
                })
                
                # 获取所有交易日期（有成交的日期）
                trade_dates = db.query(func.date(Trade.trade_time).label('trade_date')).filter(
                    Trade.user_id == user.id
                ).distinct().order_by('trade_date').all()
                
                # 获取所有有价格数据的日期
                price_dates = db.query(CryptoPrice.price_date).distinct().order_by(CryptoPrice.price_date).all()
                
                # 合并并去重所有相关日期
                all_dates = set()
                for td in trade_dates:
                    # 处理不同类型的日期对象
                    if hasattr(td, 'trade_date'):
                        trade_date = td.trade_date
                    else:
                        trade_date = td[0]  # 当使用label时，结果是元组
                    
                    if isinstance(trade_date, str):
                        trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
                    elif hasattr(trade_date, 'date'):
                        trade_date = trade_date.date()
                    
                    all_dates.add(trade_date)
                    
                for pd in price_dates:
                    # 处理价格日期
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
                        # 计算到该日期为止的现金变化
                        cash_changes = _calculate_cash_changes_up_to_date(db, user.id, target_date)
                        current_cash = float(user.initial_capital) + cash_changes
                        
                        # 计算该日期的持仓价值
                        positions_value = _calculate_positions_value_on_date(db, user.id, target_date)
                        
                        total_assets = current_cash + positions_value
                        
                        all_curve_data.append({
                            "date": target_date.isoformat(),
                            "total_assets": total_assets,
                            "cash": current_cash,
                            "positions_value": positions_value,
                            "is_initial": False,
                            "user_id": user.id,
                            "username": user.username
                        })
                        
                    except Exception as e:
                        logger.warning(f"计算用户 {user.id} 日期 {target_date} 的资产失败: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"处理用户 {user.id} 的资产曲线失败: {e}")
                continue
        
        return all_curve_data
        
    except Exception as e:
        logger.error(f"获取所有用户资产曲线失败: {e}")
        return []


@router.get("/asset-curve/all")
async def get_all_asset_curves(db: Session = Depends(get_db)):
    """获取所有用户的资产曲线数据"""
    try:
        # 获取所有用户
        users = db.query(User).all()
        if not users:
            return []
        
        all_curve_data = []
        
        for user in users:
            try:
                # 获取第一笔成交时间
                first_trade = db.query(Trade).filter(Trade.user_id == user.id).order_by(Trade.trade_time.asc()).first()
                
                if not first_trade:
                    # 如果没有成交记录，返回初始资金点
                    all_curve_data.append({
                        "date": datetime.now().date().isoformat(),
                        "total_assets": float(user.initial_capital),
                        "cash": float(user.current_cash),
                        "positions_value": 0.0,
                        "is_initial": True,
                        "user_id": user.id,
                        "username": user.username
                    })
                    continue
                
                # 第一个点：第一笔成交前一天，值为初始资金
                first_trade_date = first_trade.trade_time.date()
                start_date = first_trade_date - timedelta(days=1)
                
                # 添加起始点
                all_curve_data.append({
                    "date": start_date.isoformat(),
                    "total_assets": float(user.initial_capital),
                    "cash": float(user.initial_capital),
                    "positions_value": 0.0,
                    "is_initial": True,
                    "user_id": user.id,
                    "username": user.username
                })
                
                # 获取所有交易日期（有成交的日期）
                trade_dates = db.query(func.date(Trade.trade_time).label('trade_date')).filter(
                    Trade.user_id == user.id
                ).distinct().order_by('trade_date').all()
                
                # 获取所有有价格数据的日期
                price_dates = db.query(CryptoPrice.price_date).distinct().order_by(CryptoPrice.price_date).all()
                
                # 合并并去重所有相关日期
                all_dates = set()
                for td in trade_dates:
                    # 处理不同类型的日期对象
                    if hasattr(td, 'trade_date'):
                        trade_date = td.trade_date
                    else:
                        trade_date = td[0]  # 当使用label时，结果是元组
                    
                    if isinstance(trade_date, str):
                        trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
                    elif hasattr(trade_date, 'date'):
                        trade_date = trade_date.date()
                    
                    all_dates.add(trade_date)
                    
                for pd in price_dates:
                    # 处理价格日期
                    if hasattr(pd, 'price_date'):
                        price_date = pd.price_date
                    else:
                        price_date = pd[0]
                        
                    if isinstance(price_date, str):
                        price_date = datetime.strptime(price_date, '%Y-%m-%d').date()
                    elif hasattr(price_date, 'date'):
                        price_date = price_date.date()
                        
                    all_dates.add(price_date)
                
                # 过滤出第一笔成交日期之后的日期
                relevant_dates = sorted([d for d in all_dates if d >= first_trade_date])
                
                for target_date in relevant_dates:
                    try:
                        # 计算到该日期为止的现金变化
                        cash_changes = _calculate_cash_changes_up_to_date(db, user.id, target_date)
                        current_cash = float(user.initial_capital) + cash_changes
                        
                        # 计算该日期的持仓价值
                        positions_value = _calculate_positions_value_on_date(db, user.id, target_date)
                        
                        total_assets = current_cash + positions_value
                        
                        all_curve_data.append({
                            "date": target_date.isoformat(),
                            "total_assets": total_assets,
                            "cash": current_cash,
                            "positions_value": positions_value,
                            "is_initial": False,
                            "user_id": user.id,
                            "username": user.username
                        })
                        
                    except Exception as e:
                        logger.warning(f"计算用户 {user.id} 日期 {target_date} 的资产失败: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"处理用户 {user.id} 的资产曲线失败: {e}")
                continue
        
        return all_curve_data
        
    except Exception as e:
        logger.error(f"获取所有用户资产曲线失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取所有用户资产曲线失败: {str(e)}")


def _calculate_cash_changes_up_to_date(db: Session, user_id: int, target_date: date) -> float:
    """计算到指定日期为止的现金变化（买入为负，卖出为正）"""
    trades = db.query(Trade).filter(
        Trade.user_id == user_id,
        func.date(Trade.trade_time) <= target_date
    ).all()
    
    cash_change = 0.0
    for trade in trades:
        trade_amount = float(trade.price) * float(trade.quantity) + float(trade.commission)
        if trade.side == "BUY":
            cash_change -= trade_amount  # 买入减少现金
        else:  # SELL
            cash_change += trade_amount  # 卖出增加现金
    
    return cash_change


def _calculate_positions_value_on_date(db: Session, user_id: int, target_date: date) -> float:
    """计算指定日期的持仓价值"""
    # 获取到该日期为止的所有交易，计算每个股票的持仓数量
    trades = db.query(Trade).filter(
        Trade.user_id == user_id,
        func.date(Trade.trade_time) <= target_date
    ).order_by(Trade.trade_time.asc()).all()
    
    # 统计每个股票的净持仓
    position_quantities = {}
    for trade in trades:
        key = f"{trade.symbol}.{trade.market}"
        if key not in position_quantities:
            position_quantities[key] = {"symbol": trade.symbol, "market": trade.market, "quantity": 0.0}
        
        if trade.side == "BUY":
            position_quantities[key]["quantity"] += float(trade.quantity)
        else:  # SELL
            position_quantities[key]["quantity"] -= float(trade.quantity)
    
    # 计算持仓价值
    total_value = 0.0
    for pos_info in position_quantities.values():
        if pos_info["quantity"] <= 0:
            continue
            
        # 获取该日期的股票价格
        crypto_price = db.query(CryptoPrice).filter(
            CryptoPrice.symbol == pos_info["symbol"],
            CryptoPrice.market == pos_info["market"],
            CryptoPrice.price_date <= target_date
        ).order_by(CryptoPrice.price_date.desc()).first()
        
        if crypto_price:
            position_value = float(crypto_price.price) * pos_info["quantity"]
            total_value += position_value
        else:
            logger.warning(f"未找到 {pos_info['symbol']} 在 {target_date} 的价格数据")
    
    return total_value


# Removed password and auth endpoints - now using API key authentication

@router.get("/users", response_model=List[UserOut])
def get_all_users(db: Session = Depends(get_db)):
    """Get all AI trader accounts"""
    try:
        users = db.query(User).order_by(User.username).all()
        return [
            UserOut(
                id=user.id,
                username=user.username,
                model=user.model,
                base_url=user.base_url,
                api_key=user.api_key[:20] + "..." if len(user.api_key) > 20 else user.api_key,  # Mask API key
                initial_capital=float(user.initial_capital),
                current_cash=float(user.current_cash),
                frozen_cash=float(user.frozen_cash)
            )
            for user in users
        ]
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        raise HTTPException(status_code=500, detail="Failed to get users")


@router.post("/users", response_model=UserOut)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Create a new AI trader account"""
    try:
        # Check if username already exists
        existing = db.query(User).filter(User.username == user_data.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Create new user
        new_user = User(
            username=user_data.username,
            model=user_data.model,
            base_url=user_data.base_url,
            api_key=user_data.api_key,
            initial_capital=user_data.initial_capital,
            current_cash=user_data.initial_capital,
            frozen_cash=0.0
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return UserOut(
            id=new_user.id,
            username=new_user.username,
            model=new_user.model,
            base_url=new_user.base_url,
            api_key=new_user.api_key[:20] + "..." if len(new_user.api_key) > 20 else new_user.api_key,
            initial_capital=float(new_user.initial_capital),
            current_cash=float(new_user.current_cash),
            frozen_cash=float(new_user.frozen_cash)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db)):
    """Update an AI trader account"""
    try:
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update fields if provided
        if user_data.username is not None:
            # Check if new username already exists
            existing = db.query(User).filter(
                User.username == user_data.username,
                User.id != user_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Username already exists")
            user.username = user_data.username
        
        if user_data.model is not None:
            user.model = user_data.model
        if user_data.base_url is not None:
            user.base_url = user_data.base_url
        if user_data.api_key is not None:
            user.api_key = user_data.api_key
        
        db.commit()
        db.refresh(user)
        
        return UserOut(
            id=user.id,
            username=user.username,
            model=user.model,
            base_url=user.base_url,
            api_key=user.api_key[:20] + "..." if len(user.api_key) > 20 else user.api_key,
            initial_capital=float(user.initial_capital),
            current_cash=float(user.current_cash),
            frozen_cash=float(user.frozen_cash)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update user")


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete an AI trader account"""
    try:
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user has active positions
        positions = db.query(Position).filter(Position.user_id == user_id).all()
        if positions:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete account with active positions. Please close all positions first."
            )
        
        # Delete user
        db.delete(user)
        db.commit()
        
        return {"message": f"User {user.username} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete user")


@router.get("/asset-curve/timeframe")
async def get_asset_curve_by_timeframe(
    timeframe: str = "1d",
    db: Session = Depends(get_db)
):
    """获取所有账户在指定时间周期内的资产曲线数据（20个点）
    
    Args:
        timeframe: 时间周期，可选值: 5m, 1h, 1d
    """
    try:
        # Validate timeframe
        valid_timeframes = ["5m", "1h", "1d"]
        if timeframe not in valid_timeframes:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}")
        
        # Map timeframe to period for kline data
        timeframe_map = {
            "5m": "5m",
            "1h": "1h",
            "1d": "1d"
        }
        period = timeframe_map[timeframe]
        
        # Get all users
        users = db.query(User).all()
        if not users:
            return []
        
        # Get all unique symbols from all user positions and trades
        symbols_query = db.query(Trade.symbol, Trade.market).distinct().all()
        unique_symbols = set()
        for symbol, market in symbols_query:
            unique_symbols.add((symbol, market))
        
        if not unique_symbols:
            # No trades yet, return initial capital for all users
            now = datetime.now()
            return [{
                "timestamp": int(now.timestamp()),
                "datetime_str": now.isoformat(),
                "user_id": user.id,
                "username": user.username,
                "total_assets": float(user.initial_capital),
                "cash": float(user.current_cash),
                "positions_value": 0.0,
            } for user in users]
        
        # Fetch kline data for all symbols (20 points)
        from services.market_data import get_kline_data
        
        symbol_klines = {}
        for symbol, market in unique_symbols:
            try:
                klines = get_kline_data(symbol, market, period, 20)
                if klines:
                    symbol_klines[(symbol, market)] = klines
                    logger.info(f"Fetched {len(klines)} klines for {symbol}.{market}")
            except Exception as e:
                logger.warning(f"Failed to fetch klines for {symbol}.{market}: {e}")
        
        if not symbol_klines:
            raise HTTPException(status_code=500, detail="Failed to fetch market data")
        
        # Get timestamps from the first symbol's klines
        first_klines = next(iter(symbol_klines.values()))
        timestamps = [k['timestamp'] for k in first_klines]
        
        # Calculate asset value for each user at each timestamp
        result = []
        for user in users:
            user_id = user.id
            
            # Get all trades for this user
            trades = db.query(Trade).filter(
                Trade.user_id == user_id
            ).order_by(Trade.trade_time.asc()).all()
            
            if not trades:
                # No trades, return initial capital at all timestamps
                for i, ts in enumerate(timestamps):
                    result.append({
                        "timestamp": ts,
                        "datetime_str": first_klines[i]['datetime_str'],
                        "user_id": user_id,
                        "username": user.username,
                        "total_assets": float(user.initial_capital),
                        "cash": float(user.initial_capital),
                        "positions_value": 0.0,
                    })
                continue
            
            # Calculate holdings and cash at each timestamp
            for i, ts in enumerate(timestamps):
                ts_datetime = datetime.fromtimestamp(ts, tz=timezone.utc)
                
                # Calculate cash changes up to this timestamp
                cash_change = 0.0
                position_quantities = {}
                
                for trade in trades:
                    trade_time = trade.trade_time
                    if not trade_time.tzinfo:
                        trade_time = trade_time.replace(tzinfo=timezone.utc)
                    
                    if trade_time <= ts_datetime:
                        # Update cash
                        trade_amount = float(trade.price) * float(trade.quantity) + float(trade.commission)
                        if trade.side == "BUY":
                            cash_change -= trade_amount
                        else:  # SELL
                            cash_change += trade_amount
                        
                        # Update position
                        key = (trade.symbol, trade.market)
                        if key not in position_quantities:
                            position_quantities[key] = 0.0
                        
                        if trade.side == "BUY":
                            position_quantities[key] += float(trade.quantity)
                        else:  # SELL
                            position_quantities[key] -= float(trade.quantity)
                
                current_cash = float(user.initial_capital) + cash_change
                
                # Calculate positions value using prices at this timestamp
                positions_value = 0.0
                for (symbol, market), quantity in position_quantities.items():
                    if quantity > 0 and (symbol, market) in symbol_klines:
                        klines = symbol_klines[(symbol, market)]
                        if i < len(klines):
                            price = klines[i]['close']
                            if price:
                                positions_value += float(price) * quantity
                
                total_assets = current_cash + positions_value
                
                result.append({
                    "timestamp": ts,
                    "datetime_str": first_klines[i]['datetime_str'],
                    "user_id": user_id,
                    "username": user.username,
                    "total_assets": total_assets,
                    "cash": current_cash,
                    "positions_value": positions_value,
                })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取时间周期资产曲线失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取时间周期资产曲线失败: {str(e)}")
