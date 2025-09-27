import pandas as pd
from typing import Dict
from .models import OHLCV, Fundamentals, Metrics
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

def process_data(raw_data: Dict) -> pd.DataFrame:
    """
    Process raw stock data (prices + fundamentals).
    
    Steps:
    1. Convert validated Pydantic models → DataFrames
    2. Merge daily prices with quarterly fundamentals (forward-fill)
    3. Calculate technical indicators (SMAs, 52-week high, % diff from high)
    4. Calculate fundamental ratios (Book Value/share, P/B, EV)
    5. Return processed DataFrame
    """
    logger.info(f"Processing data for ticker {raw_data['metadata']['ticker']}")

    # 1. Convert OHLCV list → DataFrame
    prices_df = _prices_to_df(raw_data["prices"])
    
    # 2. Convert fundamentals list → DataFrame
    fundamentals_df = _fundamentals_to_df(raw_data["fundamentals"])

    # 3. Merge (forward-fill fundamentals)
    merged_df = _merge_data(prices_df, fundamentals_df)

    # 4. Add technical indicators
    merged_df = _add_technical_indicators(merged_df)

    # 5. Add fundamental ratios
    merged_df = _add_fundamental_ratios(merged_df)

    logger.info(f"Processed DataFrame shape: {merged_df.shape}")
    return merged_df

def _prices_to_df(prices: list[OHLCV]) -> pd.DataFrame:
    """Convert OHLCV Pydantic models → pandas DataFrame"""
    df = pd.DataFrame([p.model_dump() for p in prices])
    df.set_index("date", inplace=True)
    return df


def _fundamentals_to_df(fundamentals: list[Fundamentals]) -> pd.DataFrame:
    """Convert Fundamentals models → pandas DataFrame"""
    if not fundamentals:
        return pd.DataFrame()
    
    df = pd.DataFrame([f.model_dump() for f in fundamentals])
    df.set_index("report_date", inplace=True)
    return df


def _merge_data(prices_df: pd.DataFrame, fundamentals_df: pd.DataFrame) -> pd.DataFrame:
    """Merge daily prices with fundamentals (forward-fill quarterly data)"""
    if fundamentals_df.empty:
        logger.warning("No fundamentals available, continuing with price-only data")
        return prices_df
    
    if prices_df.empty:
        logger.warning("No price data available")
        return prices_df

    if not isinstance(prices_df.index, pd.DatetimeIndex):
        prices_df.index = pd.to_datetime(prices_df.index)
    if not isinstance(fundamentals_df.index, pd.DatetimeIndex):
        fundamentals_df.index = pd.to_datetime(fundamentals_df.index)
    
    prices_df = prices_df.sort_index()
    fundamentals_df = fundamentals_df.sort_index()
    
    fundamentals_reindexed = fundamentals_df.reindex(prices_df.index, method="ffill")
    merged = prices_df.join(fundamentals_reindexed, how="left")
    
    logger.info(f"Merged data: {len(prices_df)} price rows, {len(fundamentals_df)} fundamental rows")
    return merged


def _add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add 50-day SMA, 200-day SMA, 52-week high, % diff from high"""
    df["sma_50"] = df["close"].rolling(window=50, min_periods=1).mean()
    df["sma_200"] = df["close"].rolling(window=200, min_periods=1).mean()
    df["week52_high"] = df["close"].rolling(window=252, min_periods=1).max()
    df["pct_from_high"] = ((df["close"] - df["week52_high"]) / df["week52_high"]) * 100
    return df


def _add_fundamental_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """Add Book Value per Share, Price-to-Book, Enterprise Value (simplified)"""
    try:
        if "book_value" in df.columns:
            df["book_value_per_share"] = df["book_value"]
        else:
            df["book_value_per_share"] = None
            
        if "book_value_per_share" in df.columns and "close" in df.columns:
            df["price_to_book"] = df["close"] / df["book_value_per_share"].replace({0: None})
        else:
            df["price_to_book"] = None
            
        if "total_assets" in df.columns and "total_liabilities" in df.columns:
            df["enterprise_value"] = df["total_liabilities"]
        else:
            df["enterprise_value"] = None
            
    except Exception as e:
        logger.warning(f"Failed to compute fundamental ratios: {e}")
        df["price_to_book"] = None
        df["book_value_per_share"] = None
        df["enterprise_value"] = None
    
    return df
