import pytest
import pandas as pd
from datetime import datetime
from decimal import Decimal
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import OHLCV, Fundamentals
from src.database import Base, init_db
from src.config import load_config

@pytest.fixture
def sample_prices():
    """Sample OHLCV price data for testing"""
    return [
        OHLCV(date=datetime(2024, 1, 1), open=Decimal("100"), high=Decimal("105"),
              low=Decimal("95"), close=Decimal("102"), volume=1000),
        OHLCV(date=datetime(2024, 1, 2), open=Decimal("102"), high=Decimal("108"),
              low=Decimal("101"), close=Decimal("107"), volume=1200),
        OHLCV(date=datetime(2024, 1, 3), open=Decimal("107"), high=Decimal("110"),
              low=Decimal("106"), close=Decimal("109"), volume=1500),
    ]

@pytest.fixture
def sample_fundamentals():
    """Sample fundamental data for testing"""
    return [
        Fundamentals(
            report_date=datetime(2024, 1, 1),
            total_assets=Decimal("500000"),
            total_liabilities=Decimal("200000"),
            book_value=Decimal("300000"),
            revenue=Decimal("100000"),
        )
    ]

@pytest.fixture
def golden_cross_df():
    """DataFrame where sma_50 crosses above sma_200"""
    return pd.DataFrame({
        "sma_50": [10, 12, 15, 25],
        "sma_200": [20, 18, 16, 17]
    })

@pytest.fixture
def death_cross_df():
    """DataFrame where sma_50 crosses below sma_200"""
    return pd.DataFrame({
        "sma_50": [30, 28, 20, 15],
        "sma_200": [25, 26, 27, 28]
    })

@pytest.fixture
def test_db():
    """In-memory SQLite database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = f"sqlite:///{tmp.name}"
        engine = create_engine(db_path, echo=False)
        Base.metadata.create_all(engine)
        SessionFactory = sessionmaker(bind=engine)
        yield SessionFactory
        Path(tmp.name).unlink(missing_ok=True)

@pytest.fixture
def test_config():
    """Test configuration"""
    return {
        "database": {"path": "sqlite:///:memory:"},
        "logging": {"level": "INFO"},
        "data_settings": {
            "historical_period": "5y",
            "min_trading_days_for_sma": 200
        }
    }

@pytest.fixture
def sample_processed_df():
    """Processed DataFrame with technical and fundamental indicators"""
    dates = pd.date_range(start='2024-01-01', periods=10, freq='D')
    return pd.DataFrame({
        'close': [100 + i for i in range(10)],
        'sma_50': [95 + i for i in range(10)],
        'sma_200': [90 + i for i in range(10)],
        'week52_high': [105 + i for i in range(10)],
        'pct_from_high': [-5.0 + i * 0.5 for i in range(10)],
        'price_to_book': [2.0 + i * 0.1 for i in range(10)]
    }, index=dates)
