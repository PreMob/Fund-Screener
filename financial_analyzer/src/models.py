from pydantic import BaseModel, Field, field_validator, ValidationInfo
from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal, List

class OHLCV(BaseModel):
    date: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    @field_validator("high")
    @classmethod
    def high_greater_than_low(cls, v, info: ValidationInfo):
        if info.data and "low" in info.data and v < info.data["low"]:
            raise ValueError("High price must be >= Low price")
        return v
    
class Fundamentals(BaseModel):
    report_date: datetime
    total_assets: Optional[Decimal]
    total_liabilities: Optional[Decimal]
    book_value: Optional[Decimal]
    revenue: Optional[Decimal]

class Metrics(BaseModel):
    date: datetime
    sma_50: Optional[Decimal] 
    sma_200: Optional[Decimal]
    week52_high: Optional[Decimal]
    pct_from_high: Optional[Decimal]
    price_to_book: Optional[Decimal]

class SignalEvent(BaseModel):
    ticker: str
    event_date: datetime
    signal_type: Literal["golden_cross","death_cross"]

class ExportSchema(BaseModel):
    ticker: str
    company_name: Optional[str] = None
    market: Optional[str] = None   

    prices: List[OHLCV]  
    fundamentals: List[Fundamentals]  
    metrics: List[Metrics]  
    signals: List[SignalEvent]  

    generated_at: datetime