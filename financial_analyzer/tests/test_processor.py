import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from src.processor import _add_technical_indicators, _add_fundamental_ratios
from src.models import OHLCV, Fundamentals

class TestTechnicalIndicators:
    
    def test_sma_50_calculation(self):
        """Test 50-day SMA calculation"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        close_prices = list(range(1, 101))
        
        df = pd.DataFrame({
            'close': close_prices,
            'open': close_prices,
            'high': [x + 1 for x in close_prices],
            'low': [x - 1 for x in close_prices],
            'volume': [1000] * 100
        }, index=dates)
        
        result_df = _add_technical_indicators(df)
        
        assert 'sma_50' in result_df.columns
        assert result_df['sma_50'].iloc[49] == 25.5  # Average of 1-50
        assert result_df['sma_50'].iloc[99] == 75.5  # Average of 51-100
    
    def test_sma_200_calculation(self):
        """Test 200-day SMA calculation"""
        dates = pd.date_range(start='2023-01-01', periods=250, freq='D')
        close_prices = list(range(1, 251))
        
        df = pd.DataFrame({
            'close': close_prices,
            'open': close_prices,
            'high': [x + 1 for x in close_prices],
            'low': [x - 1 for x in close_prices],
            'volume': [1000] * 250
        }, index=dates)
        
        result_df = _add_technical_indicators(df)
        
        assert 'sma_200' in result_df.columns
        assert result_df['sma_200'].iloc[199] == 100.5  # Average of 1-200
        assert result_df['sma_200'].iloc[249] == 150.5  # Average of 51-250
    
    def test_week52_high_calculation(self):
        """Test 52-week high calculation (252 trading days)"""
        dates = pd.date_range(start='2023-01-01', periods=300, freq='D')
        close_prices = [50] * 100 + [75] * 100 + [60] * 100
        
        df = pd.DataFrame({
            'close': close_prices,
            'open': close_prices,
            'high': [x + 5 for x in close_prices],
            'low': [x - 5 for x in close_prices],
            'volume': [1000] * 300
        }, index=dates)
        
        result_df = _add_technical_indicators(df)
        
        assert 'week52_high' in result_df.columns
        assert result_df['week52_high'].iloc[251] == 75  # Max in 252-day window
        assert result_df['week52_high'].iloc[299] == 75  # Still 75 as max
    
    def test_pct_from_high_calculation(self):
        """Test percentage from 52-week high calculation"""
        dates = pd.date_range(start='2023-01-01', periods=300, freq='D')
        close_prices = [100] * 100 + [120] * 100 + [90] * 100
        
        df = pd.DataFrame({
            'close': close_prices,
            'open': close_prices,
            'high': [x + 5 for x in close_prices],
            'low': [x - 5 for x in close_prices],
            'volume': [1000] * 300
        }, index=dates)
        
        result_df = _add_technical_indicators(df)
        
        assert 'pct_from_high' in result_df.columns
        # At index 299: current price 90, 52-week high 120
        # (90 - 120) / 120 * 100 = -25%
        assert abs(result_df['pct_from_high'].iloc[299] - (-25.0)) < 0.01
    
    def test_technical_indicators_with_small_dataset(self):
        """Test technical indicators with dataset smaller than windows"""
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        close_prices = list(range(10, 20))
        
        df = pd.DataFrame({
            'close': close_prices,
            'open': close_prices,
            'high': [x + 1 for x in close_prices],
            'low': [x - 1 for x in close_prices],
            'volume': [1000] * 10
        }, index=dates)
        
        result_df = _add_technical_indicators(df)
        
        assert 'sma_50' in result_df.columns
        assert 'sma_200' in result_df.columns
        assert 'week52_high' in result_df.columns
        assert 'pct_from_high' in result_df.columns
        
        # With min_periods=1, should still calculate values
        assert not pd.isna(result_df['sma_50'].iloc[0])
        assert result_df['sma_50'].iloc[0] == 10.0  # First value
        assert result_df['sma_50'].iloc[9] == 14.5   # Average of all 10 values


class TestFundamentalRatios:
    
    def test_book_value_per_share_calculation(self):
        """Test book value per share calculation"""
        dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
        
        df = pd.DataFrame({
            'close': [100, 110, 105, 120, 115],
            'book_value': [Decimal('50'), Decimal('55'), Decimal('52'), Decimal('60'), Decimal('58')],
            'total_assets': [1000, 1100, 1050, 1200, 1150],
            'total_liabilities': [400, 450, 420, 500, 480]
        }, index=dates)
        
        result_df = _add_fundamental_ratios(df)
        
        assert 'book_value_per_share' in result_df.columns
        assert result_df['book_value_per_share'].iloc[0] == Decimal('50')
        assert result_df['book_value_per_share'].iloc[4] == Decimal('58')
    
    def test_price_to_book_calculation(self):
        """Test price-to-book ratio calculation"""
        dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
        
        df = pd.DataFrame({
            'close': [100, 110, 105, 120, 115],
            'book_value': [Decimal('50'), Decimal('55'), Decimal('52'), Decimal('60'), Decimal('58')],
            'total_assets': [1000, 1100, 1050, 1200, 1150],
            'total_liabilities': [400, 450, 420, 500, 480]
        }, index=dates)
        
        result_df = _add_fundamental_ratios(df)
        
        assert 'price_to_book' in result_df.columns
        # P/B = close / book_value_per_share
        # 100 / 50 = 2.0
        assert result_df['price_to_book'].iloc[0] == 2.0
        # 120 / 60 = 2.0
        assert result_df['price_to_book'].iloc[3] == 2.0
    
    def test_enterprise_value_calculation(self):
        """Test enterprise value calculation"""
        dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
        
        df = pd.DataFrame({
            'close': [100, 110, 105, 120, 115],
            'book_value': [Decimal('50'), Decimal('55'), Decimal('52'), Decimal('60'), Decimal('58')],
            'total_assets': [1000, 1100, 1050, 1200, 1150],
            'total_liabilities': [400, 450, 420, 500, 480]
        }, index=dates)
        
        result_df = _add_fundamental_ratios(df)
        
        assert 'enterprise_value' in result_df.columns
        # EV = total_liabilities (simplified approximation)
        assert result_df['enterprise_value'].iloc[0] == 400
        assert result_df['enterprise_value'].iloc[4] == 480
    
    def test_price_to_book_with_zero_book_value(self):
        """Test price-to-book calculation when book value is zero"""
        dates = pd.date_range(start='2023-01-01', periods=3, freq='D')
        
        df = pd.DataFrame({
            'close': [100, 110, 105],
            'book_value': [Decimal('50'), Decimal('0'), Decimal('52')],
            'total_assets': [1000, 1100, 1050],
            'total_liabilities': [400, 450, 420]
        }, index=dates)
        
        result_df = _add_fundamental_ratios(df)
        
        assert 'price_to_book' in result_df.columns
        assert result_df['price_to_book'].iloc[0] == 2.0  # 100/50
        assert pd.isna(result_df['price_to_book'].iloc[1])  # Division by zero -> NaN
        assert abs(result_df['price_to_book'].iloc[2] - Decimal('105') / Decimal('52')) < Decimal('0.001')  # 105/52
    
    def test_fundamental_ratios_missing_columns(self):
        """Test fundamental ratios when required columns are missing"""
        dates = pd.date_range(start='2023-01-01', periods=3, freq='D')
        
        df = pd.DataFrame({
            'close': [100, 110, 105],
            'open': [95, 105, 100]
        }, index=dates)
        
        result_df = _add_fundamental_ratios(df)
        
        assert 'book_value_per_share' in result_df.columns
        assert 'price_to_book' in result_df.columns
        assert 'enterprise_value' in result_df.columns
        
        assert pd.isna(result_df['book_value_per_share'].iloc[0])
        assert pd.isna(result_df['price_to_book'].iloc[0])
        assert pd.isna(result_df['enterprise_value'].iloc[0])
    
    def test_fundamental_ratios_exception_handling(self):
        """Test fundamental ratios exception handling"""
        dates = pd.date_range(start='2023-01-01', periods=3, freq='D')
        
        # Create DataFrame with problematic data that might cause exceptions
        df = pd.DataFrame({
            'close': [100, np.inf, 105],
            'book_value': [Decimal('50'), Decimal('55'), None],
        }, index=dates)
        
        result_df = _add_fundamental_ratios(df)
        
        assert 'book_value_per_share' in result_df.columns
        assert 'price_to_book' in result_df.columns
        assert 'enterprise_value' in result_df.columns


class TestIntegratedCalculations:
    
    def test_combined_technical_and_fundamental_indicators(self):
        """Test that both technical and fundamental indicators work together"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        close_prices = list(range(100, 200))
        
        df = pd.DataFrame({
            'close': close_prices,
            'open': [x - 1 for x in close_prices],
            'high': [x + 2 for x in close_prices],
            'low': [x - 2 for x in close_prices],
            'volume': [1000] * 100,
            'book_value': [Decimal('50')] * 100,
            'total_assets': [2000] * 100,
            'total_liabilities': [800] * 100
        }, index=dates)
        
        df = _add_technical_indicators(df)
        df = _add_fundamental_ratios(df)
        
        expected_columns = [
            'sma_50', 'sma_200', 'week52_high', 'pct_from_high',
            'book_value_per_share', 'price_to_book', 'enterprise_value'
        ]
        
        for col in expected_columns:
            assert col in df.columns
        
        assert df['sma_50'].iloc[99] == 174.5  # Average of 150-199
        assert df['price_to_book'].iloc[0] == 2.0  # 100/50
        assert df['enterprise_value'].iloc[0] == 800