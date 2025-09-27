# Financial Analyzer

A comprehensive financial analysis system that fetches stock data, calculates technical indicators, detects trading signals, and stores results in a database.

## Project Overview

The Financial Analyzer provides:
- **Data Fetching**: Stock prices and fundamentals from Yahoo Finance
- **Technical Analysis**: SMA 50/200, 52-week highs, percentage from high
- **Fundamental Analysis**: Price-to-book ratios, enterprise value calculations
- **Signal Detection**: Golden cross and death cross patterns
- **Database Storage**: SQLite with ORM for persistent data
- **JSON Export**: Structured analysis results
- **CLI Interface**: Command-line tools for analysis and database management

## Setup Instructions

### Prerequisites
- Python 3.9+
- Poetry (recommended) or pip

### Installation
```bash
# Clone repository
git clone <repository-url>
cd financial_analyzer

# Install with Poetry
poetry install

# Or install with pip
pip install -r requirements.txt
```

### Configuration
Copy and customize configuration:
```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml`:
```yaml
database:
  path: "sqlite:///financial_data.db"
logging:
  level: "INFO"
data_settings:
  historical_period: "5y"
  min_trading_days_for_sma: 200
```

## Usage Examples

### Analyze Single Stock
```bash
# Basic analysis
python -m src.main analyze NVDA

# With JSON export
python -m src.main analyze AAPL --output exports/aapl_analysis.json

# Custom database
python -m src.main analyze TSLA --db sqlite:///custom.db
```

### Database Management
```bash
# Initialize database
python -m src.main init-database

# Validate database integrity
python -m src.main validate-db
```

### Batch Analysis
```bash
# Analyze multiple tickers
for ticker in NVDA AAPL MSFT GOOGL; do
    python -m src.main analyze $ticker --output exports/${ticker}_analysis.json
done
```

## Database Schema

### Tables Structure

**tickers**
- `id`: Primary key
- `symbol`: Stock ticker (unique)
- `company_name`: Company name
- `market`: Market designation

**daily_metrics**
- `id`: Primary key
- `ticker_id`: Foreign key to tickers
- `date`: Trading date
- `close`: Closing price
- `sma_50`: 50-day simple moving average
- `sma_200`: 200-day simple moving average
- `week52_high`: 52-week rolling maximum
- `pct_from_high`: Percentage from 52-week high
- `price_to_book`: Price-to-book ratio

**signal_events**
- `id`: Primary key
- `ticker_id`: Foreign key to tickers
- `event_date`: Signal occurrence date
- `signal_type`: "golden_cross" or "death_cross"

### Constraints
- Unique constraint on (ticker_id, date) for daily_metrics
- Unique constraint on (ticker_id, event_date, signal_type) for signal_events

## Design Decisions

### Forward-Fill Strategy
Fundamental data (quarterly) is forward-filled to match daily price data frequency. Latest fundamental values apply until next reporting period.

### Missing Data Handling
- **Price Data**: Skip analysis if unavailable
- **Fundamental Data**: Continue with price-only analysis
- **Technical Indicators**: Use `min_periods=1` for small datasets

### Idempotency
Database operations are idempotent:
- Duplicate tickers update existing records
- Daily metrics replace existing entries for same ticker/date
- Signal events prevent duplicates with unique constraints

### Ticker Handling
- Automatic symbol normalization to uppercase
- Company metadata stored separately from metrics
- Support for multiple markets (US, India, etc.)

## Data Quality Notes

### Yahoo Finance Limitations
- **Rate Limiting**: 2000 requests/hour, implement delays for batch processing
- **Data Gaps**: Weekends, holidays, delisted stocks may have missing data
- **Fundamental Data**: Quarterly reporting with potential delays

### Data Validation
- OHLCV validation ensures High >= Low
- Decimal precision maintained for financial calculations
- Timezone handling for price data

### Known Issues
- Historical data availability varies by ticker age
- Indian stocks may have different data availability patterns
- Delisted stocks have limited historical access

## Testing Instructions

### Run Test Suite
```bash
# All tests
pytest

# Specific modules
pytest tests/test_processor.py
pytest tests/test_signals.py

# With coverage
pytest --cov=src
```

### Test with Sample Tickers

**US Stocks (Recommended)**
```bash
# Large cap, reliable data
python -m src.main analyze AAPL
python -m src.main analyze MSFT
python -m src.main analyze GOOGL

# Recent IPOs (test data limitations)
python -m src.main analyze SNOW
python -m src.main analyze PLTR
```

**Indian Stocks**
```bash
# Large cap Indian stocks
python -m src.main analyze RELIANCE.NS
python -m src.main analyze TCS.NS
python -m src.main analyze INFY.NS

# Mid/small cap (test data quality)
python -m src.main analyze HDFCBANK.NS
python -m src.main analyze ICICIBANK.NS
```

**Old vs Recent Stocks Testing**
```bash
# Established companies (rich historical data)
python -m src.main analyze IBM
python -m src.main analyze GE
python -m src.main analyze KO

# Newer companies (limited history)
python -m src.main analyze UBER
python -m src.main analyze SWIGGY.NS
```

### Validate Results
1. Check database for stored metrics
2. Verify JSON export structure
3. Confirm signal detection accuracy
4. Test edge cases with insufficient data

### Performance Testing
Monitor execution time and memory usage for large datasets:
```bash
time python -m src.main analyze AAPL
```