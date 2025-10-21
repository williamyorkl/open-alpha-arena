"""
Demo mode API routes for simulation trading
不需要认证，专注于交易功能测试
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from database.connection import SessionLocal
from repositories.user_repo import get_or_create_user
from repositories.account_repo import get_or_create_default_account, get_accounts_by_user
from repositories.order_repo import list_orders
from repositories.position_repo import list_positions
from services.asset_calculator import calc_positions_value
from schemas.account import AccountOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/demo", tags=["demo"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/init")
async def init_demo_user(username: str = "demo", db: Session = Depends(get_db)):
    """初始化演示用户和默认账户"""
    try:
        # Create demo user
        user = get_or_create_user(db, username)
        
        # Create default account
        account = get_or_create_default_account(
            db, 
            user.id,
            account_name=f"{username} AI Trader",
            initial_capital=100000.0
        )
        
        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "is_active": user.is_active == "true"
            },
            "account": {
                "id": account.id,
                "name": account.name,
                "account_type": account.account_type,
                "initial_capital": float(account.initial_capital),
                "current_cash": float(account.current_cash)
            }
        }
        
    except Exception as e:
        logger.error(f"Demo initialization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Demo initialization failed: {str(e)}")


@router.get("/accounts")
async def get_demo_accounts(username: str = "demo", db: Session = Depends(get_db)):
    """获取演示用户的所有账户"""
    try:
        user = get_or_create_user(db, username)
        accounts = get_accounts_by_user(db, user.id, active_only=True)
        
        return [
            {
                "id": account.id,
                "name": account.name,
                "account_type": account.account_type,
                "initial_capital": float(account.initial_capital),
                "current_cash": float(account.current_cash),
                "frozen_cash": float(account.frozen_cash),
                "model": account.model,
                "api_key": "****" + (account.api_key[-4:] if account.api_key and len(account.api_key) > 4 else ""),
            }
            for account in accounts
        ]
        
    except Exception as e:
        logger.error(f"Get demo accounts failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get demo accounts failed: {str(e)}")


@router.get("/overview")
async def get_demo_overview(username: str = "demo", db: Session = Depends(get_db)):
    """获取演示账户概览"""
    try:
        user = get_or_create_user(db, username)
        account = get_or_create_default_account(db, user.id)
        
        # Get trading data
        positions = list_positions(db, account.id)
        orders = list_orders(db, account.id)
        positions_value = calc_positions_value(db, account.id)
        
        return {
            "user": {
                "id": user.id,
                "username": user.username
            },
            "account": {
                "id": account.id,
                "name": account.name,
                "account_type": account.account_type,
                "initial_capital": float(account.initial_capital),
                "current_cash": float(account.current_cash),
                "frozen_cash": float(account.frozen_cash)
            },
            "portfolio": {
                "total_assets": positions_value + float(account.current_cash),
                "positions_value": positions_value,
                "positions_count": len(positions),
                "pending_orders": len([o for o in orders if o.status == "PENDING"])
            }
        }
        
    except Exception as e:
        logger.error(f"Get demo overview failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get demo overview failed: {str(e)}")


@router.post("/reset")
async def reset_demo_account(username: str = "demo", db: Session = Depends(get_db)):
    """重置演示账户 (清空所有交易数据，恢复初始资金)"""
    try:
        user = get_or_create_user(db, username)
        account = get_or_create_default_account(db, user.id)
        
        # Reset account cash
        account.current_cash = account.initial_capital
        account.frozen_cash = 0.0
        
        # Clear all positions and orders (in a real implementation)
        # For now, just reset the cash
        db.commit()
        
        return {
            "message": f"Demo account for {username} has been reset",
            "account": {
                "id": account.id,
                "name": account.name,
                "current_cash": float(account.current_cash),
                "frozen_cash": float(account.frozen_cash)
            }
        }
        
    except Exception as e:
        logger.error(f"Reset demo account failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Reset demo account failed: {str(e)}")