import yfinance as yf
import pandas as pd
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from pydantic import ValidationError
from models import OHLCV, Fundamentals

logger = logging.getLogger(__name__)

def fetch_stock_data(ticker: str) -> dict:
    """
    Fetch raw data from yfinance and validate with schemas.
    
    Returns:
        dict: {
            "prices": List[OHLCV],
            "fundamentals": List[Fundamentals], 
            "metadata": {...}
        }
    """
    logger.info(f"Fetching data for ticker: {ticker}")
    
    result = {
        "prices": [],
        "fundamentals": [],
        "metadata": {
            "ticker": ticker,
            "fetch_timestamp": datetime.now(),
            "data_sources": {},
            "errors": []
        }
    }
    
    try:
        ticker_obj = yf.Ticker(ticker)
        
        prices_data = _fetch_ohlcv_data(ticker_obj, ticker)
        result["prices"] = prices_data["prices"]
        result["metadata"]["data_sources"]["prices"] = prices_data["source"]
        if prices_data.get("errors"):
            result["metadata"]["errors"].extend(prices_data["errors"])
        
        fundamentals_data = _fetch_fundamentals_data(ticker_obj, ticker)
        result["fundamentals"] = fundamentals_data["fundamentals"]
        result["metadata"]["data_sources"]["fundamentals"] = fundamentals_data["source"]
        result["metadata"]["source_used"] = fundamentals_data["source"]
        if fundamentals_data.get("errors"):
            result["metadata"]["errors"].extend(fundamentals_data["errors"])
            
        try:
            info = ticker_obj.info
            result["metadata"]["company_name"] = info.get("longName") or info.get("shortName")
            result["metadata"]["market"] = info.get("exchange")
            result["metadata"]["sector"] = info.get("sector")
        except Exception as e:
            logger.warning(f"Failed to fetch ticker info for {ticker}: {e}")
            result["metadata"]["errors"].append(f"Failed to fetch ticker info: {e}")
        
    except Exception as e:
        logger.error(f"Critical error fetching data for {ticker}: {e}")
        result["metadata"]["errors"].append(f"Critical error: {e}")
    
    logger.info(f"Completed data fetch for {ticker}. Prices: {len(result['prices'])}, Fundamentals: {len(result['fundamentals'])}")
    return result

def _fetch_ohlcv_data(ticker_obj: yf.Ticker, ticker: str) -> dict:
    """Fetch daily OHLCV data for 5 years."""
    result = {
        "prices": [],
        "source": None,
        "errors": []
    }
    
    try:
        # Fetch 5 years of daily data
        hist = ticker_obj.history(period="5y")
        result["source"] = "yfinance_history_5y"
        
        if hist.empty:
            logger.warning(f"No historical data found for {ticker}")
            result["errors"].append("No historical data available")
            return result
        
        for date, row in hist.iterrows():
            try:
                if pd.isna(row['Open']) or pd.isna(row['Close']):
                    continue
                
                try:
                    if isinstance(date, pd.Timestamp):
                        date_obj = date.to_pydatetime()
                    elif isinstance(date, datetime):
                        date_obj = date
                    else:
                        date_obj = pd.Timestamp(str(date)).to_pydatetime()
                except:
                    date_obj = datetime.now()
                
                try:
                    ohlcv = OHLCV(
                        date=date_obj,
                        open=Decimal(str(row['Open'])),
                        high=Decimal(str(row['High'])),
                        low=Decimal(str(row['Low'])),
                        close=Decimal(str(row['Close'])),
                        volume=int(row['Volume']) if not pd.isna(row['Volume']) else 0
                    )
                    result["prices"].append(ohlcv)
                except ValidationError as ve:
                    logger.warning(f"Pydantic validation failed for OHLCV {ticker} on {date}: {ve}")
                    result["errors"].append(f"OHLCV validation error for {date}: {ve}")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to create OHLCV data for {ticker} on {date}: {e}")
                    result["errors"].append(f"OHLCV creation error for {date}: {e}")
                    continue
                    
            except Exception as e:
                logger.warning(f"Failed to process row for {ticker} on {date}: {e}")
                result["errors"].append(f"Row processing error for {date}: {e}")
                continue
        
        logger.info(f"Successfully fetched {len(result['prices'])} price records for {ticker}")
        
    except Exception as e:
        logger.warning(f"Failed to fetch OHLCV data for {ticker}: {e}")
        result["errors"].append(f"OHLCV fetch error: {e}")
    
    return result

def _fetch_fundamentals_data(ticker_obj: yf.Ticker, ticker: str) -> dict:
    """Fetch fundamentals with fallback strategy."""
    result = {
        "fundamentals": [],
        "source": None,
        "errors": []
    }
    
    quarterly_df = pd.DataFrame()
    income_df = pd.DataFrame()
    
    try:
        quarterly_df = ticker_obj.quarterly_balance_sheet
        if not quarterly_df.empty:
            result["source"] = "quarterly_balance_sheet"
            logger.info(f"Using quarterly balance sheet for {ticker}")
    except Exception as e:
        logger.warning(f"Failed to fetch quarterly fundamentals for {ticker}: {e}")
        result["errors"].append(f"Quarterly balance sheet error: {e}")
    
    if quarterly_df.empty:
        try:
            quarterly_df = ticker_obj.balance_sheet
            if not quarterly_df.empty:
                result["source"] = "annual_balance_sheet"
                logger.info(f"Using annual balance sheet for {ticker}")
        except Exception as e:
            logger.warning(f"Failed to fetch annual fundamentals for {ticker}: {e}")
            result["errors"].append(f"Annual balance sheet error: {e}")
    
    try:
        if result["source"] == "quarterly_balance_sheet":
            income_df = ticker_obj.quarterly_financials
        else:
            income_df = ticker_obj.financials
        logger.info(f"Fetched income statement for {ticker}")
    except Exception as e:
        logger.warning(f"Failed to fetch income statement for {ticker}: {e}")
        result["errors"].append(f"Income statement error: {e}")
    
    if quarterly_df.empty:
        try:
            info = ticker_obj.info
            if info:
                result["source"] = "ticker_info"
                logger.info(f"Using ticker info for {ticker}")
                fundamental = _create_fundamental_from_info(info)
                if fundamental:
                    result["fundamentals"].append(fundamental)
        except Exception as e:
            logger.warning(f"Failed to fetch ticker info for {ticker}: {e}")
            result["errors"].append(f"Ticker info error: {e}")
    
    if not quarterly_df.empty:
        try:
            result["fundamentals"] = _process_balance_sheet(quarterly_df, income_df, ticker)
        except Exception as e:
            logger.warning(f"Failed to process balance sheet for {ticker}: {e}")
            result["errors"].append(f"Balance sheet processing error: {e}")
    
    logger.info(f"Successfully fetched {len(result['fundamentals'])} fundamental records for {ticker} using {result['source']}")
    return result

def _process_balance_sheet(df: pd.DataFrame, income_df: pd.DataFrame, ticker: str) -> List[Fundamentals]:
    """Process balance sheet DataFrame into Fundamentals objects."""
    fundamentals = []
    
    for date_col in df.columns:
        try:
            period_data = df[date_col]
            
            total_assets = None
            total_liabilities = None
            book_value = None
            revenue = None
            
            assets_keys = ['Total Assets', 'TotalAssets', 'Total Stockholder Equity']
            liabilities_keys = ['Total Liabilities', 'TotalLiabilities', 'Total Liab']
            equity_keys = ['Stockholders Equity', 'Total Stockholder Equity', 'ShareholderEquity']
            
            for key in assets_keys:
                if key in period_data.index and not pd.isna(period_data[key]):
                    total_assets = Decimal(str(period_data[key]))
                    break
                    
            for key in liabilities_keys:
                if key in period_data.index and not pd.isna(period_data[key]):
                    total_liabilities = Decimal(str(period_data[key]))
                    break
                    
            for key in equity_keys:
                if key in period_data.index and not pd.isna(period_data[key]):
                    book_value = Decimal(str(period_data[key]))
                    break
            
            if not income_df.empty and date_col in income_df.columns:
                try:
                    income_data = income_df[date_col]
                    revenue_keys = ['Total Revenue', 'TotalRevenue', 'Revenue', 'Net Sales']
                    for key in revenue_keys:
                        if key in income_data.index and not pd.isna(income_data[key]):
                            revenue = Decimal(str(income_data[key]))
                            break
                except Exception as e:
                    logger.warning(f"Failed to extract revenue for {ticker} on {date_col}: {e}")
            
            try:
                if isinstance(date_col, pd.Timestamp):
                    report_date = date_col.to_pydatetime()
                elif isinstance(date_col, datetime):
                    report_date = date_col
                else:
                    report_date = pd.Timestamp(str(date_col)).to_pydatetime()
            except:
                report_date = datetime.now()
                
            try:
                fundamental = Fundamentals(
                    report_date=report_date,
                    total_assets=total_assets,
                    total_liabilities=total_liabilities,
                    book_value=book_value,
                    revenue=revenue
                )
                fundamentals.append(fundamental)
            except ValidationError as ve:
                logger.warning(f"Pydantic validation failed for Fundamentals {ticker} on {date_col}: {ve}")
                continue
            except Exception as e:
                logger.warning(f"Failed to create Fundamentals for {ticker} on {date_col}: {e}")
                continue
            
        except Exception as e:
            logger.warning(f"Failed to process fundamental data for {ticker} on {date_col}: {e}")
            continue
    
    return fundamentals

def _create_fundamental_from_info(info: dict) -> Optional[Fundamentals]:
    """Create a single Fundamentals record from ticker info."""
    try:
        total_assets = None
        book_value = None
        revenue = None
        
        if 'totalAssets' in info and info['totalAssets']:
            total_assets = Decimal(str(info['totalAssets']))
            
        if 'bookValue' in info and info['bookValue']:
            book_value = Decimal(str(info['bookValue']))
            
        if 'totalRevenue' in info and info['totalRevenue']:
            revenue = Decimal(str(info['totalRevenue']))
        
        try:
            return Fundamentals(
                report_date=datetime.now(),
                total_assets=total_assets,
                total_liabilities=None,
                book_value=book_value,
                revenue=revenue
            )
        except ValidationError as ve:
            logger.warning(f"Pydantic validation failed for Fundamentals from info: {ve}")
            return None
        
    except Exception as e:
        logger.warning(f"Failed to create fundamental from info: {e}")
        return None
