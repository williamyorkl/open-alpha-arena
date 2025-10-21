from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any

from database.connection import get_db
from database.models import AIAccount

router = APIRouter()


class AIAccountCreate(BaseModel):
    name: str
    model: str
    base_url: str
    api_key: str


@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    accounts = db.query(AIAccount).all()
    return [
        {
            "id": acc.id,
            "name": acc.name,
            "model": acc.model,
            "base_url": acc.base_url,
            "api_key": acc.api_key
        }
        for acc in accounts
    ]


@router.post("/accounts")
def create_account(account: AIAccountCreate, db: Session = Depends(get_db)) -> Dict[str, Any]:
    existing = db.query(AIAccount).filter(AIAccount.name == account.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Account with this name already exists")
    
    db_account = AIAccount(
        name=account.name,
        model=account.model,
        base_url=account.base_url,
        api_key=account.api_key
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    
    return {
        "id": db_account.id,
        "name": db_account.name,
        "model": db_account.model,
        "base_url": db_account.base_url,
        "api_key": db_account.api_key
    }


@router.put("/accounts/{account_id}")
def update_account(account_id: int, account: AIAccountCreate, db: Session = Depends(get_db)) -> Dict[str, Any]:
    db_account = db.query(AIAccount).filter(AIAccount.id == account_id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    existing = db.query(AIAccount).filter(
        AIAccount.name == account.name,
        AIAccount.id != account_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Account with this name already exists")
    
    db_account.name = account.name
    db_account.model = account.model
    db_account.base_url = account.base_url
    db_account.api_key = account.api_key
    
    db.commit()
    db.refresh(db_account)
    
    return {
        "id": db_account.id,
        "name": db_account.name,
        "model": db_account.model,
        "base_url": db_account.base_url,
        "api_key": db_account.api_key
    }


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(AIAccount).filter(AIAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    db.delete(account)
    db.commit()
    return {"message": "Account deleted successfully"}
