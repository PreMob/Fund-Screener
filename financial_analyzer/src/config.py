import yaml
import logging
from pathlib import Path

# Default config values (fallbacks)
DEFAULT_CONFIG = {
    "database": {
        "path": "sqlite:///financial_data.db"
    },
    "logging": {
        "level": "INFO"
    },
    "data_settings": {
        "historical_period": "5y",
        "min_trading_days_for_sma": 200
    }
}

def load_config(config_file: str = "config.yaml") -> dict:
    """
    Load configuration from YAML file with fallbacks.
    
    Args:
        config_file (str): Path to YAML config file
    
    Returns:
        dict: Configuration dictionary
    """
    config_path = Path(config_file)
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
            # Merge defaults with loaded config
            merged = DEFAULT_CONFIG.copy()
            for k, v in config.items():
                if k in merged and isinstance(merged[k], dict):
                    merged[k].update(v or {})
                else:
                    merged[k] = v
            return merged
        except Exception as e:
            logging.warning(f"Failed to load config file {config_file}: {e}, using defaults")
            return DEFAULT_CONFIG
    else:
        logging.info(f"No config file found at {config_file}, using defaults")
        return DEFAULT_CONFIG


def get_database_url(config: dict) -> str:
    return config.get("database", {}).get("path", DEFAULT_CONFIG["database"]["path"])


def get_logging_level(config: dict) -> str:
    return config.get("logging", {}).get("level", DEFAULT_CONFIG["logging"]["level"])


def get_data_settings(config: dict) -> dict:
    return config.get("data_settings", DEFAULT_CONFIG["data_settings"])
