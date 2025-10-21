from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    """Create a new AI Trader Account"""
    username: str
    model: str = "gpt-4-turbo"
    base_url: str = "https://api.openai.com/v1"
    api_key: str
    initial_capital: float = 10000.0


class UserUpdate(BaseModel):
    """Update AI Trader Account"""
    username: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class UserOut(BaseModel):
    """AI Trader Account output"""
    id: int
    username: str
    model: str
    base_url: str
    api_key: str  # Will be masked in API responses
    initial_capital: float
    current_cash: float
    frozen_cash: float

    class Config:
        from_attributes = True


# Removed password-based auth - now using API keys


class AccountOverview(BaseModel):
    user: UserOut
    total_assets: float  # Total assets in USD
    positions_value: float  # Total positions value in USD
