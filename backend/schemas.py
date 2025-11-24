from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ---------- Auth ----------
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime

    class Config:
        orm_mode = True

# ---------- Portfolio ----------
class PortfolioResponse(BaseModel):
    id: int
    balance: float
    created_at: datetime

    class Config:
        orm_mode = True

# ---------- Trades ----------
class TradeCreate(BaseModel):
    asset: str
    side: str
    amount: float
    price: float

class TradeResponse(BaseModel):
    id: int
    asset: str
    side: str
    amount: float
    price: float
    timestamp: datetime

    class Config:
        orm_mode = True

# ---------- Transactions ----------
class TransactionCreate(BaseModel):
    type: str
    amount: float

class TransactionResponse(BaseModel):
    id: int
    type: str
    amount: float
    fee: float
    status: str
    timestamp: datetime

    class Config:
        orm_mode = True

# ---------- AI ----------
class AIRequest(BaseModel):
    question: str

class AIResponse(BaseModel):
    answer: str
