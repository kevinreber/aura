"""Financial data schemas for stocks and cryptocurrency."""

from pydantic import BaseModel, Field
from typing import List, Optional
import datetime as dt


class FinancialInput(BaseModel):
    """Input for financial data requests."""
    symbols: List[str] = Field(
        ..., 
        description="List of stock symbols (e.g., ['MSFT', 'NVDA']) or crypto symbols (e.g., ['BTC', 'ETH'])",
        example=["MSFT", "NVDA", "BTC", "ETH"]
    )
    data_type: str = Field(
        default="mixed",
        description="Type of financial data: 'stocks', 'crypto', or 'mixed'",
        example="mixed"
    )


class FinancialItem(BaseModel):
    """Individual financial instrument data."""
    symbol: str = Field(..., description="Symbol/ticker", example="MSFT")
    name: str = Field(..., description="Full name", example="Microsoft Corporation")
    price: float = Field(..., description="Current price", example=415.50)
    change: float = Field(..., description="Price change", example=2.35)
    change_percent: float = Field(..., description="Percentage change", example=0.57)
    currency: str = Field(default="USD", description="Currency", example="USD")
    data_type: str = Field(..., description="stocks or crypto", example="stocks")
    last_updated: str = Field(..., description="Last update time", example="2025-08-11T09:30:00Z")


class FinancialOutput(BaseModel):
    """Output for financial data."""
    request_time: str = Field(..., description="When the request was made")
    total_items: int = Field(..., description="Number of financial instruments")
    market_status: str = Field(..., description="Market status (open/closed/mixed)")
    data: List[FinancialItem] = Field(..., description="Financial data for each symbol")
    summary: str = Field(..., description="Brief summary of the financial data")


class PortfolioSummary(BaseModel):
    """Portfolio summary for morning briefing."""
    total_value_change: float = Field(..., description="Total portfolio change in USD")
    total_percent_change: float = Field(..., description="Total portfolio percentage change")
    best_performer: str = Field(..., description="Best performing symbol")
    worst_performer: str = Field(..., description="Worst performing symbol")
    market_sentiment: str = Field(..., description="Overall market sentiment")
