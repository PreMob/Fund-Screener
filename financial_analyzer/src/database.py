from sqlalchemy import (
    create_engine, Column, String, Date, Float, Integer, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from typing import Optional, List
import pandas as pd
from .models import SignalEvent
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


"""
ORM Table Models
"""
class Ticker(Base):
    __tablename__ = "tickers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, unique=True, nullable=False)
    company_name = Column(String)
    market = Column(String)

    metrics = relationship("DailyMetric", back_populates="ticker_rel")
    signals = relationship("SignalEventDB", back_populates="ticker_rel")


class DailyMetric(Base):
    __tablename__ = "daily_metrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"))
    date = Column(Date, nullable=False)
    close = Column(Float)
    sma_50 = Column(Float)
    sma_200 = Column(Float)
    week52_high = Column(Float)
    pct_from_high = Column(Float)
    price_to_book = Column(Float)

    ticker_rel = relationship("Ticker", back_populates="metrics")

    __table_args__ = (UniqueConstraint("ticker_id", "date", name="_unique_ticker_date"),)


class SignalEventDB(Base):
    __tablename__ = "signal_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"))
    event_date = Column(Date, nullable=False)
    signal_type = Column(String, nullable=False)

    ticker_rel = relationship("Ticker", back_populates="signals")

    __table_args__ = (UniqueConstraint("ticker_id", "event_date", "signal_type", name="_unique_signal"),)

"""
Database Utility Functions
"""

def init_db(db_path: str = "sqlite:///financial_data.db"):
    """Initialize SQLite database and return session factory"""
    engine = create_engine(db_path, echo=False, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def save_ticker(session, ticker: str, company_name: Optional[str] = None, market: Optional[str] = None):
    """Insert or update ticker info"""
    obj = session.query(Ticker).filter_by(symbol=ticker).first()
    if not obj:
        obj = Ticker(symbol=ticker, company_name=company_name, market=market)
        session.add(obj)
        session.commit()
    else:
        if company_name:
            obj.company_name = company_name
        if market:
            obj.market = market
        session.commit()
    return obj


def save_daily_metrics(session, ticker_obj: Ticker, df: pd.DataFrame):
    """Save metrics DataFrame into DB (idempotent insert/replace)"""
    if df.empty:
        logger.warning("Empty DataFrame provided for daily metrics")
        return
    
    for date, row in df.iterrows():
        existing = session.query(DailyMetric).filter_by(
            ticker_id=ticker_obj.id, date=date
        ).first()
        
        if existing:
            existing.close = row.get("close")
            existing.sma_50 = row.get("sma_50")
            existing.sma_200 = row.get("sma_200")
            existing.week52_high = row.get("week52_high")
            existing.pct_from_high = row.get("pct_from_high")
            existing.price_to_book = row.get("price_to_book")
        else:
            metric = DailyMetric(
                ticker_id=ticker_obj.id,
                date=date,
                close=row.get("close"),
                sma_50=row.get("sma_50"),
                sma_200=row.get("sma_200"),
                week52_high=row.get("week52_high"),
                pct_from_high=row.get("pct_from_high"),
                price_to_book=row.get("price_to_book")
            )
            session.add(metric)
    
    session.commit()
    logger.info(f"Saved {len(df)} daily metrics for ticker {ticker_obj.symbol}")


def save_signals(session, ticker_obj: Ticker, signals: List[SignalEvent]):
    """Save SignalEvent objects into DB"""
    if not signals:
        logger.info("No signals to save")
        return
    
    for s in signals:
        existing = session.query(SignalEventDB).filter_by(
            ticker_id=ticker_obj.id,
            event_date=s.event_date,
            signal_type=s.signal_type
        ).first()
        
        if not existing:
            signal = SignalEventDB(
                ticker_id=ticker_obj.id,
                event_date=s.event_date,
                signal_type=s.signal_type
            )
            session.add(signal)
    
    session.commit()
    logger.info(f"Saved {len(signals)} signals for ticker {ticker_obj.symbol}")


def save_complete_data(session, ticker: str, df: pd.DataFrame, signals: List[SignalEvent], 
                      company_name: Optional[str] = None, market: Optional[str] = None):
    """Complete save operation for ticker data, metrics, and signals"""
    try:
        ticker_obj = save_ticker(session, ticker, company_name, market)
        save_daily_metrics(session, ticker_obj, df)
        save_signals(session, ticker_obj, signals)
        logger.info(f"Successfully saved complete data for {ticker}")
    except Exception as e:
        logger.error(f"Failed to save complete data for {ticker}: {e}")
        session.rollback()
        raise


def get_ticker_metrics(session, ticker: str, start_date=None, end_date=None) -> pd.DataFrame:
    """Retrieve daily metrics for a ticker as DataFrame"""
    ticker_obj = session.query(Ticker).filter_by(symbol=ticker).first()
    if not ticker_obj:
        return pd.DataFrame()
    
    query = session.query(DailyMetric).filter_by(ticker_id=ticker_obj.id)
    
    if start_date:
        query = query.filter(DailyMetric.date >= start_date)
    if end_date:
        query = query.filter(DailyMetric.date <= end_date)
    
    metrics = query.order_by(DailyMetric.date).all()
    
    if not metrics:
        return pd.DataFrame()
    
    data = []
    for m in metrics:
        data.append({
            'date': m.date,
            'close': m.close,
            'sma_50': m.sma_50,
            'sma_200': m.sma_200,
            'week52_high': m.week52_high,
            'pct_from_high': m.pct_from_high,
            'price_to_book': m.price_to_book
        })
    
    return pd.DataFrame(data).set_index('date')


def get_ticker_signals(session, ticker: str) -> List[SignalEvent]:
    """Retrieve signals for a ticker"""
    ticker_obj = session.query(Ticker).filter_by(symbol=ticker).first()
    if not ticker_obj:
        return []
    
    signals = session.query(SignalEventDB).filter_by(ticker_id=ticker_obj.id).all()
    
    return [
        SignalEvent(
            ticker=ticker,
            event_date=s.event_date,
            signal_type=s.signal_type
        )
        for s in signals
    ]


def validate_data_integrity(session) -> bool:
    """Validate database constraints and data integrity"""
    try:
        duplicate_tickers = session.query(Ticker.symbol).group_by(Ticker.symbol).having(
            session.query(Ticker.symbol).count() > 1
        ).all()
        
        if duplicate_tickers:
            logger.error(f"Found duplicate tickers: {duplicate_tickers}")
            return False
        
        duplicate_metrics = session.query(
            DailyMetric.ticker_id, DailyMetric.date
        ).group_by(
            DailyMetric.ticker_id, DailyMetric.date
        ).having(
            session.query(DailyMetric.ticker_id).count() > 1
        ).all()
        
        if duplicate_metrics:
            logger.error(f"Found duplicate metrics: {len(duplicate_metrics)} entries")
            return False
        
        logger.info("Database integrity validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Data integrity validation failed: {e}")
        return False
