"""
账户管理 API 路由 - 处理交易账户的 CRUD 操作
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import logging

from database.connection import SessionLocal
from database.models import Account
from repositories.account_repo import (
    create_account, get_account, get_accounts_by_user,
    update_account, update_account_cash, deactivate_account,
    get_or_create_default_account
)
from repositories.user_repo import verify_auth_session, get_user
from schemas.account import (
    AccountCreate, AccountUpdate, AccountOut, AccountOverview
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user_id(session_token: str, db: Session = Depends(get_db)) -> int:
    """从 session token 获取当前用户 ID"""
    user_id = verify_auth_session(db, session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user_id


@router.get("/", response_model=List[AccountOut])
async def list_user_accounts(session_token: str, db: Session = Depends(get_db)):
    """获取当前用户的所有交易账户"""
    try:
        user_id = await get_current_user_id(session_token, db)
        accounts = get_accounts_by_user(db, user_id, active_only=True)
        
        return [
            AccountOut(
                id=account.id,
                user_id=account.user_id,
                name=account.name,
                model=account.model,
                base_url=account.base_url,
                api_key="****" + account.api_key[-4:] if account.api_key else "",  # Mask API key
                initial_capital=float(account.initial_capital),
                current_cash=float(account.current_cash),
                frozen_cash=float(account.frozen_cash),
                account_type=account.account_type,
                is_active=account.is_active == "true"
            )
            for account in accounts
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取账户列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取账户列表失败: {str(e)}")


@router.post("/", response_model=AccountOut)
async def create_trading_account(
    session_token: str,
    account_data: AccountCreate,
    db: Session = Depends(get_db)
):
    """创建新的交易账户"""
    try:
        user_id = await get_current_user_id(session_token, db)
        
        # Check if account name exists for this user
        existing_accounts = get_accounts_by_user(db, user_id, active_only=True)
        for acc in existing_accounts:
            if acc.name == account_data.name:
                raise HTTPException(status_code=400, detail="Account name already exists")
        
        account = create_account(
            db=db,
            user_id=user_id,
            name=account_data.name,
            account_type=account_data.account_type,
            initial_capital=account_data.initial_capital,
            model=account_data.model,
            base_url=account_data.base_url,
            api_key=account_data.api_key
        )
        
        return AccountOut(
            id=account.id,
            user_id=account.user_id,
            name=account.name,
            model=account.model,
            base_url=account.base_url,
            api_key="****" + account.api_key[-4:] if account.api_key else "",
            initial_capital=float(account.initial_capital),
            current_cash=float(account.current_cash),
            frozen_cash=float(account.frozen_cash),
            account_type=account.account_type,
            is_active=account.is_active == "true"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建账户失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建账户失败: {str(e)}")


@router.get("/{account_id}", response_model=AccountOut)
async def get_account_details(
    account_id: int,
    session_token: str,
    db: Session = Depends(get_db)
):
    """获取账户详情"""
    try:
        user_id = await get_current_user_id(session_token, db)
        account = get_account(db, account_id)
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        if account.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return AccountOut(
            id=account.id,
            user_id=account.user_id,
            name=account.name,
            model=account.model,
            base_url=account.base_url,
            api_key="****" + account.api_key[-4:] if account.api_key else "",
            initial_capital=float(account.initial_capital),
            current_cash=float(account.current_cash),
            frozen_cash=float(account.frozen_cash),
            account_type=account.account_type,
            is_active=account.is_active == "true"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取账户详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取账户详情失败: {str(e)}")


@router.put("/{account_id}", response_model=AccountOut)
async def update_trading_account(
    account_id: int,
    session_token: str,
    account_data: AccountUpdate,
    db: Session = Depends(get_db)
):
    """更新交易账户"""
    try:
        user_id = await get_current_user_id(session_token, db)
        account = get_account(db, account_id)
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        if account.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if new name conflicts with existing accounts
        if account_data.name:
            existing_accounts = get_accounts_by_user(db, user_id, active_only=True)
            for acc in existing_accounts:
                if acc.name == account_data.name and acc.id != account_id:
                    raise HTTPException(status_code=400, detail="Account name already exists")
        
        updated_account = update_account(
            db=db,
            account_id=account_id,
            name=account_data.name,
            model=account_data.model,
            base_url=account_data.base_url,
            api_key=account_data.api_key
        )
        
        return AccountOut(
            id=updated_account.id,
            user_id=updated_account.user_id,
            name=updated_account.name,
            model=updated_account.model,
            base_url=updated_account.base_url,
            api_key="****" + updated_account.api_key[-4:] if updated_account.api_key else "",
            initial_capital=float(updated_account.initial_capital),
            current_cash=float(updated_account.current_cash),
            frozen_cash=float(updated_account.frozen_cash),
            account_type=updated_account.account_type,
            is_active=updated_account.is_active == "true"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新账户失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新账户失败: {str(e)}")


@router.delete("/{account_id}")
async def delete_trading_account(
    account_id: int,
    session_token: str,
    db: Session = Depends(get_db)
):
    """删除交易账户 (软删除)"""
    try:
        user_id = await get_current_user_id(session_token, db)
        account = get_account(db, account_id)
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        if account.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        deactivate_account(db, account_id)
        return {"message": f"Account {account.name} deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除账户失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除账户失败: {str(e)}")


@router.get("/{account_id}/default")
async def get_or_create_default(
    session_token: str,
    db: Session = Depends(get_db)
):
    """获取或创建默认账户 (向后兼容)"""
    try:
        user_id = await get_current_user_id(session_token, db)
        account = get_or_create_default_account(db, user_id)
        
        return AccountOut(
            id=account.id,
            user_id=account.user_id,
            name=account.name,
            model=account.model,
            base_url=account.base_url,
            api_key="****" + account.api_key[-4:] if account.api_key else "",
            initial_capital=float(account.initial_capital),
            current_cash=float(account.current_cash),
            frozen_cash=float(account.frozen_cash),
            account_type=account.account_type,
            is_active=account.is_active == "true"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取默认账户失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取默认账户失败: {str(e)}")