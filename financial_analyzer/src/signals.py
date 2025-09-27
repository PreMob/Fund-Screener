import pandas as pd
from typing import List
from .models import SignalEvent
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def detect_golden_crossover(df: pd.DataFrame, ticker: str) -> List[SignalEvent]:
    """
    Detect Golden Cross events (50-day SMA crossing above 200-day SMA).
    
    Args:
        df (pd.DataFrame): Processed DataFrame with sma_50 and sma_200 columns
        ticker (str): Stock ticker symbol

    Returns:
        List[SignalEvent]: Golden Cross signal events
    """
    signals = []

    if "sma_50" not in df.columns or "sma_200" not in df.columns:
        logger.warning("SMA columns missing, cannot detect golden cross")
        return signals

    # Shift to detect crossovers
    df["sma_diff"] = df["sma_50"] - df["sma_200"]
    df["sma_diff_prev"] = df["sma_diff"].shift(1)

    crossover_points = df[
        (df["sma_diff"] > 0) & (df["sma_diff_prev"] <= 0)
    ].index

    for date in crossover_points:
        signals.append(
            SignalEvent(
                ticker=ticker,
                event_date=pd.to_datetime(date).to_pydatetime(),
                signal_type="golden_cross"
            )
        )

    logger.info(f"Detected {len(signals)} golden cross events for {ticker}")
    return signals


def detect_death_crossover(df: pd.DataFrame, ticker: str) -> List[SignalEvent]:
    """
    Detect Death Cross events (50-day SMA crossing below 200-day SMA).
    """
    signals = []

    if "sma_50" not in df.columns or "sma_200" not in df.columns:
        logger.warning("SMA columns missing, cannot detect death cross")
        return signals

    df["sma_diff"] = df["sma_50"] - df["sma_200"]
    df["sma_diff_prev"] = df["sma_diff"].shift(1)

    crossover_points = df[
        (df["sma_diff"] < 0) & (df["sma_diff_prev"] >= 0)
    ].index

    for date in crossover_points:
        signals.append(
            SignalEvent(
                ticker=ticker,
                event_date=pd.to_datetime(date).to_pydatetime(),
                signal_type="death_cross"
            )
        )

    logger.info(f"Detected {len(signals)} death cross events for {ticker}")
    return signals


def detect_signals(df: pd.DataFrame, ticker: str) -> List[SignalEvent]:
    """
    Wrapper to detect all supported signals.
    """
    golden_crosses = detect_golden_crossover(df, ticker)
    death_crosses = detect_death_crossover(df, ticker)
    return golden_crosses + death_crosses
