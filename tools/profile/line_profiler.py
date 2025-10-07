#!/usr/bin/env python3
"""
Line-by-line profiler for detailed indicator performance analysis.
Requires line_profiler: pip install line_profiler
"""

import sys
from pathlib import Path
import time
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stockie.loaders.config_loader import ConfigLoader
from stockie.db.database_facade import DatabaseFacade
from stockie.indicators.calculate_indicators import CalculateIndicators
from stockie.util.tickers import Tickers
from stockie.log.custom_logger import CustomLogger


def setup_test_environment():
    """Setup test environment with sample tickers"""
    config_loader = ConfigLoader("/prod/stockie/config")
    config = config_loader.get()
    
    # Add password
    password = os.getenv('STOCKIE_DB_PASSWORD', 'stockie')
    config['db']['password'] = password
    
    # Get database connection
    import psycopg2
    db_config = config['db']
    conn = psycopg2.connect(**db_config)
    db_facade = DatabaseFacade(conn)
    
    # Get sample tickers (small set for detailed profiling)
    logger = CustomLogger('profiler', log_to_console=True, log_level='INFO').get_logger()
    tickers_util = Tickers(logger, config)
    sample_tickers = tickers_util.all_tickers[:20]  # Just 20 tickers for detailed analysis
    
    return db_facade, config, sample_tickers


@profile  # This decorator is added by line_profiler
def profile_calculate_indicators_detailed():
    """Detailed line-by-line profiling of calculate_indicators"""
    db_facade, config, sample_tickers = setup_test_environment()
    
    calculator = CalculateIndicators(db_facade, config)
    calculator.run(sample_tickers)
    
    db_facade.conn.close()


# Also profile individual indicator methods
@profile
def profile_single_ticker_calculation():
    """Profile calculation for a single ticker in detail"""
    db_facade, config, sample_tickers = setup_test_environment()
    
    calculator = CalculateIndicators(db_facade, config)
    
    # Get data for one ticker
    ticker = sample_tickers[0]
    df = db_facade.fetch_price_data(ticker)
    
    if not df.empty and "close" in df.columns:
        # Profile each indicator family
        for family, indicators in config.get("indicators", {}).items():
            try:
                from importlib import import_module
                module = import_module(f"stockie.indicators.{family}")
                cls = getattr(module, f"{family.capitalize()}Indicators")
                
                # This is where the actual computation happens
                indicator_instance = cls(df, indicators)
                results = indicator_instance.calculate()
                
            except Exception as e:
                print(f"Error with {family}: {e}")
    
    db_facade.conn.close()


if __name__ == "__main__":
    print("This script should be run with line_profiler:")
    print("kernprof -l -v line_profiler.py")
    print("")
    print("To install line_profiler:")
    print("pip install line_profiler")
    
    # Run the functions (they won't be profiled without kernprof)
    profile_calculate_indicators_detailed()