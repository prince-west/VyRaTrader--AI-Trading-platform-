# backend/app/models/performance.py
from sqlalchemy import Column, Integer, Float, DateTime
from datetime import datetime
from backend.models import Base
from backend.app.db.models import Base

class Performance(Base):
    __tablename__ = "performance"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    daily_return = Column(Float, default=0.0)
    cumulative_return = Column(Float, default=0.0)
    drawdown = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)
