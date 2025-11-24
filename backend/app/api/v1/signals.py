"""
Signals API endpoints for VyRaTrader.
- GET /v1/signals/latest - Get latest trading signals
- POST /v1/signals/run - Trigger strategy runner
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio import AsyncSession

from backend.app.core.logger import logger
from backend.app.db.models import Signals
from backend.app.db.session import get_session
from backend.app.services.strategy_runner import (
    get_strategy_runner,
    run_strategies,
    run_strategies_for_symbol,
    get_latest_signals,
    cleanup_expired_signals
)


router = APIRouter(tags=["signals"])


# Pydantic models for request/response
class SignalResponse(BaseModel):
    """Response model for signal data."""
    id: str
    strategy: str
    symbol: str
    action: str
    entry: float
    sl: float
    tp: float
    confidence: float
    source_meta: Optional[dict] = None
    timestamp: str
    processed: bool
    expires_at: Optional[str] = None

    class Config:
        from_attributes = True


class RunStrategiesRequest(BaseModel):
    """Request model for running strategies."""
    symbols: Optional[List[str]] = Field(None, description="Specific symbols to analyze")
    symbol: Optional[str] = Field(None, description="Single symbol to analyze")
    cleanup_expired: bool = Field(True, description="Whether to cleanup expired signals")


class RunStrategiesResponse(BaseModel):
    """Response model for strategy run results."""
    success: bool
    signals_generated: int
    symbols_analyzed: List[str]
    strategies_run: List[str]
    cleanup_count: int
    message: str


@router.get("/latest", response_model=List[SignalResponse])
async def get_latest_signals_endpoint(
    limit: int = Query(50, ge=1, le=100, description="Number of signals to return"),
    strategy: Optional[str] = Query(None, description="Filter by strategy name"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    session: AsyncSession = Depends(get_session)
) -> List[SignalResponse]:
    """
    Get latest trading signals with optional filtering.
    
    Args:
        limit: Maximum number of signals to return (1-100)
        strategy: Filter by strategy name
        symbol: Filter by symbol
        session: Database session
    
    Returns:
        List of latest signals
    """
    try:
        signals = await get_latest_signals(limit, strategy, symbol)
        
        # Convert to response model
        response_signals = []
        for signal in signals:
            response_signal = SignalResponse(
                id=signal.id or "",
                strategy=signal.strategy,
                symbol=signal.symbol,
                action=signal.action,
                entry=signal.entry,
                sl=signal.sl,
                tp=signal.tp,
                confidence=signal.confidence,
                source_meta=signal.source_meta,
                timestamp=signal.timestamp.isoformat(),
                processed=signal.processed,
                expires_at=signal.expires_at.isoformat() if signal.expires_at else None
            )
            response_signals.append(response_signal)
        
        logger.info(f"Returned {len(response_signals)} signals")
        return response_signals
        
    except Exception as exc:
        logger.exception(f"Error getting latest signals: {exc}")
        raise HTTPException(status_code=500, detail=f"Error retrieving signals: {str(exc)}")


@router.post("/run", response_model=RunStrategiesResponse)
async def run_strategies_endpoint(
    request: RunStrategiesRequest,
    session: AsyncSession = Depends(get_session)
) -> RunStrategiesResponse:
    """
    Trigger strategy runner to generate new signals.
    
    Args:
        request: Run strategies request with optional parameters
        session: Database session
    
    Returns:
        Results of strategy run
    """
    try:
        runner = get_strategy_runner()
        
        # Determine symbols to analyze
        symbols_to_analyze = []
        if request.symbol:
            symbols_to_analyze = [request.symbol]
        elif request.symbols:
            symbols_to_analyze = request.symbols
        else:
            # Get symbols from recent price data
            symbols_to_analyze = await runner.get_symbols_to_analyze(session)
        
        # Get enabled strategies
        strategies = await runner.get_enabled_strategies(session)
        strategy_names = [s.name for s in strategies]
        
        # Run strategies
        generated_signals = await run_strategies(symbols_to_analyze)
        
        # Cleanup expired signals if requested
        cleanup_count = 0
        if request.cleanup_expired:
            cleanup_count = await cleanup_expired_signals()
        
        response = RunStrategiesResponse(
            success=True,
            signals_generated=len(generated_signals),
            symbols_analyzed=symbols_to_analyze,
            strategies_run=strategy_names,
            cleanup_count=cleanup_count,
            message=f"Generated {len(generated_signals)} signals from {len(strategy_names)} strategies"
        )
        
        logger.info(f"Strategy run completed: {response.message}")
        return response
        
    except Exception as exc:
        logger.exception(f"Error running strategies: {exc}")
        raise HTTPException(status_code=500, detail=f"Error running strategies: {str(exc)}")


@router.get("/{symbol}/latest", response_model=List[SignalResponse])
async def get_latest_signals_for_symbol(
    symbol: str,
    limit: int = Query(20, ge=1, le=50, description="Number of signals to return"),
    strategy: Optional[str] = Query(None, description="Filter by strategy name"),
    session: AsyncSession = Depends(get_session)
) -> List[SignalResponse]:
    """
    Get latest signals for a specific symbol.
    
    Args:
        symbol: Symbol to get signals for
        limit: Maximum number of signals to return
        strategy: Optional strategy filter
        session: Database session
    
    Returns:
        List of latest signals for the symbol
    """
    try:
        signals = await get_latest_signals(limit, strategy, symbol)
        
        # Convert to response model
        response_signals = []
        for signal in signals:
            response_signal = SignalResponse(
                id=signal.id or "",
                strategy=signal.strategy,
                symbol=signal.symbol,
                action=signal.action,
                entry=signal.entry,
                sl=signal.sl,
                tp=signal.tp,
                confidence=signal.confidence,
                source_meta=signal.source_meta,
                timestamp=signal.timestamp.isoformat(),
                processed=signal.processed,
                expires_at=signal.expires_at.isoformat() if signal.expires_at else None
            )
            response_signals.append(response_signal)
        
        logger.info(f"Returned {len(response_signals)} signals for {symbol}")
        return response_signals
        
    except Exception as exc:
        logger.exception(f"Error getting signals for {symbol}: {exc}")
        raise HTTPException(status_code=500, detail=f"Error retrieving signals for {symbol}: {str(exc)}")


@router.post("/{symbol}/run", response_model=RunStrategiesResponse)
async def run_strategies_for_symbol_endpoint(
    symbol: str,
    session: AsyncSession = Depends(get_session)
) -> RunStrategiesResponse:
    """
    Run all strategies for a specific symbol.
    
    Args:
        symbol: Symbol to analyze
        session: Database session
    
    Returns:
        Results of strategy run for the symbol
    """
    try:
        runner = get_strategy_runner()
        
        # Get enabled strategies
        strategies = await runner.get_enabled_strategies(session)
        strategy_names = [s.name for s in strategies]
        
        # Run strategies for the symbol
        generated_signals = await run_strategies_for_symbol(symbol)
        
        response = RunStrategiesResponse(
            success=True,
            signals_generated=len(generated_signals),
            symbols_analyzed=[symbol],
            strategies_run=strategy_names,
            cleanup_count=0,
            message=f"Generated {len(generated_signals)} signals for {symbol}"
        )
        
        logger.info(f"Strategy run for {symbol} completed: {response.message}")
        return response
        
    except Exception as exc:
        logger.exception(f"Error running strategies for {symbol}: {exc}")
        raise HTTPException(status_code=500, detail=f"Error running strategies for {symbol}: {str(exc)}")


@router.delete("/expired")
async def cleanup_expired_signals_endpoint(
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Manually trigger cleanup of expired signals.
    
    Args:
        session: Database session
    
    Returns:
        Cleanup results
    """
    try:
        cleanup_count = await cleanup_expired_signals()
        
        return {
            "success": True,
            "cleanup_count": cleanup_count,
            "message": f"Cleaned up {cleanup_count} expired signals"
        }
        
    except Exception as exc:
        logger.exception(f"Error cleaning up expired signals: {exc}")
        raise HTTPException(status_code=500, detail=f"Error cleaning up signals: {str(exc)}")


@router.get("/stats/summary")
async def get_signals_stats(
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Get summary statistics about signals.
    
    Args:
        session: Database session
    
    Returns:
        Signals statistics
    """
    try:
        from sqlmodel import select, func
        
        # Get total signals count
        total_stmt = select(func.count(Signals.id))
        total_result = await session.exec(total_stmt)
        total_signals = total_result.first() or 0
        
        # Get signals by strategy
        strategy_stmt = select(
            Signals.strategy,
            func.count(Signals.id).label("count")
        ).group_by(Signals.strategy)
        strategy_result = await session.exec(strategy_stmt)
        strategy_counts = {row[0]: row[1] for row in strategy_result.all()}
        
        # Get signals by action
        action_stmt = select(
            Signals.action,
            func.count(Signals.id).label("count")
        ).group_by(Signals.action)
        action_result = await session.exec(action_stmt)
        action_counts = {row[0]: row[1] for row in action_result.all()}
        
        # Get unprocessed signals count
        unprocessed_stmt = select(func.count(Signals.id)).where(Signals.processed == False)
        unprocessed_result = await session.exec(unprocessed_stmt)
        unprocessed_count = unprocessed_result.first() or 0
        
        return {
            "total_signals": total_signals,
            "unprocessed_signals": unprocessed_count,
            "by_strategy": strategy_counts,
            "by_action": action_counts
        }
        
    except Exception as exc:
        logger.exception(f"Error getting signals stats: {exc}")
        raise HTTPException(status_code=500, detail=f"Error retrieving stats: {str(exc)}")
