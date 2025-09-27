import typer
import logging
import json
from datetime import datetime
from pathlib import Path

from .config import load_config, get_database_url, get_logging_level
from .data_fetcher import fetch_stock_data
from .processor import process_data
from .signals import detect_signals
from .database import init_db, save_complete_data, validate_data_integrity
from .models import ExportSchema

# Load configuration
config = load_config()
db_url = get_database_url(config)

# Configure logging
logging.basicConfig(level=get_logging_level(config))
logger = logging.getLogger(__name__)

app = typer.Typer(help="Financial Analyzer CLI")


@app.command()
def analyze(
    ticker: str = typer.Argument(..., help="Stock ticker symbol to analyze"),
    output: str = typer.Option(None, "--output", "-o", help="Path to save JSON export"),
    db_path: str = typer.Option(db_url, "--db", help="Database connection string")
):
    """
    Run full pipeline for a given ticker:
    Fetch → Process → Detect signals → Save to DB → Export JSON
    """
    logger.info(f"Starting analysis for {ticker.upper()}")
    ticker = ticker.upper()

    Session = init_db(db_path)
    session = Session()

    try:
        logger.info("Step 1: Fetching raw data...")
        raw_data = fetch_stock_data(ticker)
        
        if not raw_data.get("prices"):
            logger.error(f"No price data available for {ticker}")
            return
        
        logger.info("Step 2: Processing data...")
        processed_df = process_data(raw_data)
        
        if processed_df.empty:
            logger.error(f"Processing failed - empty DataFrame for {ticker}")
            return

        logger.info("Step 3: Detecting signals...")
        signals = detect_signals(processed_df, ticker)
        logger.info(f"Detected {len(signals)} signals")

        logger.info("Step 4: Saving to database...")
        save_complete_data(
            session,
            ticker=ticker,
            df=processed_df,
            signals=signals,
            company_name=raw_data["metadata"].get("company_name"),
            market=raw_data["metadata"].get("market")
        )

        if output:
            logger.info("Step 5: Exporting to JSON...")
            try:
                from .models import Metrics
                
                latest_metrics = []
                if not processed_df.empty:
                    latest_row = processed_df.iloc[-1]
                    latest_metrics = [Metrics(
                        date=processed_df.index[-1],
                        sma_50=latest_row.get('sma_50'),
                        sma_200=latest_row.get('sma_200'),
                        week52_high=latest_row.get('week52_high'),
                        pct_from_high=latest_row.get('pct_from_high'),
                        price_to_book=latest_row.get('price_to_book')
                    )]
                
                export_data = ExportSchema(
                    ticker=ticker,
                    company_name=raw_data["metadata"].get("company_name"),
                    market=raw_data["metadata"].get("market"),
                    prices=raw_data["prices"],
                    fundamentals=raw_data["fundamentals"],
                    metrics=latest_metrics,
                    signals=signals,
                    generated_at=datetime.now()
                )
                
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(export_data.model_dump_json(indent=2))
                logger.info(f"Exported analysis to {output}")
                
            except Exception as e:
                logger.error(f"Export failed: {e}")

        logger.info(f"Pipeline completed successfully for {ticker}")

    except Exception as e:
        logger.error(f"Pipeline failed for {ticker}: {e}")
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def validate_db(
    db_path: str = typer.Option(db_url, "--db", help="Database connection string")
):
    """
    Validate database integrity and constraints
    """
    logger.info("Validating database integrity...")
    
    Session = init_db(db_path)
    session = Session()
    
    try:
        is_valid = validate_data_integrity(session)
        if is_valid:
            logger.info("Database validation passed")
        else:
            logger.error("Database validation failed")
            raise typer.Exit(1)
    finally:
        session.close()


@app.command()
def init_database(
    db_path: str = typer.Option(db_url, "--db", help="Database connection string")
):
    """
    Initialize database with required tables
    """
    logger.info(f"Initializing database at {db_path}")
    
    try:
        Session = init_db(db_path)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
