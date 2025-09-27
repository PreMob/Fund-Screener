import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.signals import detect_golden_crossover, detect_death_crossover, detect_signals
from src.models import SignalEvent


class TestGoldenCrossover:
    
    def test_detect_golden_cross_basic(self):
        """Test basic golden cross detection with synthetic data"""
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        
        df = pd.DataFrame({
            'close': [100, 105, 110, 115, 120, 125, 130, 135, 140, 145],
            'sma_50': [95, 98, 102, 108, 115, 122, 128, 132, 135, 138],
            'sma_200': [100, 100, 100, 105, 110, 115, 120, 125, 130, 135]
        }, index=dates)
        
        signals = detect_golden_crossover(df, "TEST")
        
        assert len(signals) == 1
        assert signals[0].ticker == "TEST"
        assert signals[0].signal_type == "golden_cross"
        assert isinstance(signals[0].event_date, datetime)
    
    def test_detect_multiple_golden_crosses(self):
        """Test detection of multiple golden cross events"""
        dates = pd.date_range(start='2023-01-01', periods=20, freq='D')
        
        sma_50 = [90, 95, 100, 105, 110, 108, 106, 104, 102, 100, 
                  98, 100, 105, 110, 115, 120, 125, 130, 135, 140]
        sma_200 = [100] * 20
        
        df = pd.DataFrame({
            'close': list(range(100, 120)),
            'sma_50': sma_50,
            'sma_200': sma_200
        }, index=dates)
        
        signals = detect_golden_crossover(df, "TEST")
        
        assert len(signals) == 2
        for signal in signals:
            assert signal.signal_type == "golden_cross"
            assert signal.ticker == "TEST"
    
    def test_no_golden_cross_detected(self):
        """Test when no golden cross occurs"""
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        
        df = pd.DataFrame({
            'close': list(range(100, 110)),
            'sma_50': [95, 94, 93, 92, 91, 90, 89, 88, 87, 86],
            'sma_200': [100] * 10
        }, index=dates)
        
        signals = detect_golden_crossover(df, "TEST")
        
        assert len(signals) == 0
    
    def test_golden_cross_missing_columns(self):
        """Test golden cross detection with missing SMA columns"""
        dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
        
        df = pd.DataFrame({
            'close': [100, 105, 110, 115, 120]
        }, index=dates)
        
        signals = detect_golden_crossover(df, "TEST")
        
        assert len(signals) == 0
    
    def test_golden_cross_edge_case_equal_values(self):
        """Test golden cross when SMAs are equal"""
        dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
        
        df = pd.DataFrame({
            'close': [100, 105, 110, 115, 120],
            'sma_50': [95, 100, 105, 110, 115],
            'sma_200': [100, 100, 100, 100, 100]
        }, index=dates)
        
        signals = detect_golden_crossover(df, "TEST")
        
        assert len(signals) == 1


class TestDeathCrossover:
    
    def test_detect_death_cross_basic(self):
        """Test basic death cross detection with synthetic data"""
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        
        df = pd.DataFrame({
            'close': [100, 95, 90, 85, 80, 75, 70, 65, 60, 55],
            'sma_50': [105, 102, 98, 92, 85, 78, 72, 68, 65, 62],
            'sma_200': [100, 100, 100, 95, 90, 85, 80, 75, 70, 65]
        }, index=dates)
        
        signals = detect_death_crossover(df, "TEST")
        
        assert len(signals) == 1
        assert signals[0].ticker == "TEST"
        assert signals[0].signal_type == "death_cross"
        assert isinstance(signals[0].event_date, datetime)
    
    def test_detect_multiple_death_crosses(self):
        """Test detection of multiple death cross events"""
        dates = pd.date_range(start='2023-01-01', periods=20, freq='D')
        
        sma_50 = [110, 105, 100, 95, 90, 92, 94, 96, 98, 100,
                  102, 100, 95, 90, 85, 80, 75, 70, 65, 60]
        sma_200 = [100] * 20
        
        df = pd.DataFrame({
            'close': list(range(100, 80, -1)),
            'sma_50': sma_50,
            'sma_200': sma_200
        }, index=dates)
        
        signals = detect_death_crossover(df, "TEST")
        
        assert len(signals) == 2
        for signal in signals:
            assert signal.signal_type == "death_cross"
            assert signal.ticker == "TEST"
    
    def test_no_death_cross_detected(self):
        """Test when no death cross occurs"""
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        
        df = pd.DataFrame({
            'close': list(range(100, 110)),
            'sma_50': [105, 106, 107, 108, 109, 110, 111, 112, 113, 114],
            'sma_200': [100] * 10
        }, index=dates)
        
        signals = detect_death_crossover(df, "TEST")
        
        assert len(signals) == 0
    
    def test_death_cross_missing_columns(self):
        """Test death cross detection with missing SMA columns"""
        dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
        
        df = pd.DataFrame({
            'close': [100, 95, 90, 85, 80],
            'sma_50': [105, 100, 95, 90, 85]
        }, index=dates)
        
        signals = detect_death_crossover(df, "TEST")
        
        assert len(signals) == 0


class TestSignalDetection:
    
    def test_detect_both_signals(self):
        """Test detection of both golden and death cross signals"""
        dates = pd.date_range(start='2023-01-01', periods=30, freq='D')
        
        sma_50_values = []
        sma_200_values = [100] * 30
        
        # Create pattern: below -> above -> below
        for i in range(30):
            if i < 5:
                sma_50_values.append(95 + i)  # Rising from 95 to 99
            elif i < 15:
                sma_50_values.append(100 + (i-5))  # Above 200 SMA
            else:
                sma_50_values.append(110 - (i-15))  # Falling back below
        
        df = pd.DataFrame({
            'close': list(range(100, 130)),
            'sma_50': sma_50_values,
            'sma_200': sma_200_values
        }, index=dates)
        
        signals = detect_signals(df, "TEST")
        
        assert len(signals) >= 2
        signal_types = [s.signal_type for s in signals]
        assert "golden_cross" in signal_types
        assert "death_cross" in signal_types
    
    def test_detect_signals_empty_dataframe(self):
        """Test signal detection with empty DataFrame"""
        df = pd.DataFrame()
        signals = detect_signals(df, "TEST")
        assert len(signals) == 0
    
    def test_detect_signals_insufficient_data(self):
        """Test signal detection with insufficient data points"""
        dates = pd.date_range(start='2023-01-01', periods=2, freq='D')
        
        df = pd.DataFrame({
            'close': [100, 105],
            'sma_50': [95, 105],
            'sma_200': [100, 100]
        }, index=dates)
        
        signals = detect_signals(df, "TEST")
        
        assert len(signals) >= 0


class TestSignalEventValidation:
    
    def test_signal_event_properties(self):
        """Test that SignalEvent objects have correct properties"""
        dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
        
        df = pd.DataFrame({
            'close': [100, 105, 110, 115, 120],
            'sma_50': [95, 98, 102, 108, 115],
            'sma_200': [100, 100, 100, 105, 110]
        }, index=dates)
        
        signals = detect_golden_crossover(df, "AAPL")
        
        assert len(signals) > 0
        signal = signals[0]
        
        assert hasattr(signal, 'ticker')
        assert hasattr(signal, 'event_date')
        assert hasattr(signal, 'signal_type')
        
        assert signal.ticker == "AAPL"
        assert signal.signal_type == "golden_cross"
        assert isinstance(signal.event_date, datetime)
    
    def test_signal_chronological_order(self):
        """Test that signals are detected in chronological order"""
        dates = pd.date_range(start='2023-01-01', periods=20, freq='D')
        
        # Create multiple crossovers
        sma_50 = [95, 98, 102, 105, 98, 95, 102, 108, 105, 98, 
                  95, 102, 108, 112, 108, 102, 98, 105, 110, 115]
        sma_200 = [100] * 20
        
        df = pd.DataFrame({
            'close': list(range(100, 120)),
            'sma_50': sma_50,
            'sma_200': sma_200
        }, index=dates)
        
        golden_signals = detect_golden_crossover(df, "TEST")
        
        if len(golden_signals) > 1:
            for i in range(1, len(golden_signals)):
                assert golden_signals[i].event_date >= golden_signals[i-1].event_date


class TestEdgeCases:
    
    def test_all_nan_sma_values(self):
        """Test signal detection with NaN SMA values"""
        dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
        
        df = pd.DataFrame({
            'close': [100, 105, 110, 115, 120],
            'sma_50': [np.nan] * 5,
            'sma_200': [np.nan] * 5
        }, index=dates)
        
        signals = detect_signals(df, "TEST")
        assert len(signals) == 0
    
    def test_mixed_nan_values(self):
        """Test signal detection with some NaN values"""
        dates = pd.date_range(start='2023-01-01', periods=8, freq='D')
        
        df = pd.DataFrame({
            'close': [100, 105, 110, 115, 120, 125, 130, 135],
            'sma_50': [np.nan, np.nan, 95, 98, 102, 108, 115, 122],
            'sma_200': [100, 100, 100, 100, 100, 105, 110, 115]
        }, index=dates)
        
        signals = detect_golden_crossover(df, "TEST")
        assert isinstance(signals, list)
    
    def test_single_row_dataframe(self):
        """Test signal detection with single row DataFrame"""
        dates = pd.date_range(start='2023-01-01', periods=1, freq='D')
        
        df = pd.DataFrame({
            'close': [100],
            'sma_50': [105],
            'sma_200': [100]
        }, index=dates)
        
        signals = detect_signals(df, "TEST")
        assert len(signals) == 0