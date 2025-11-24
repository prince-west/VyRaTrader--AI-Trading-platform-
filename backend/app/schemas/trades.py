from pydantic import BaseModel
from typing import Optional

class TradeRequest(BaseModel):
    user_id: str
    symbol: str
    side: str
    size: float

class TradeResponse(BaseModel):
    id: str
    symbol: str
    side: str
    size: float
    price: Optional[float]
    status: str
    profit_loss: Optional[float]

    class Config:
        orm_mode = True
