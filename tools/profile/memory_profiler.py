#!/usr/bin/env python3
"""
Memory profiling for stockie components.
Requires memory_profiler: pip install memory-profiler psutil
"""

import sys
from pathlib import Path
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from memory_profiler import profile
from stockie.loaders.config_loader import ConfigLoader
from stockie.db.database_facade import DatabaseFacade
from stockie.indicators.calculate_indicators import CalculateIndicators
from stockie.util.tickers import Tickers
from stockie.log.custom_logger import CustomLogger


def setup_test_environment(limit=50):
    """Setup test environment"""
    config_loader = ConfigLoader("/prod/stockie/config")
    config = config_loader.get()
    
    password = os.getenv('STOCKIE_DB_PASSWORD', 'stockie')
    config['db']['password'] = password
    
    import psycopg2
    db_config = config['db']
    conn = psycopg2.connect(**db_config)
    db_facade = DatabaseFacade(conn)
    
    logger = CustomLogger('profiler', log_to_console=True, log_level='INFO').get_logger()
    tickers_util = Tickers(logger, config)
    sample_tickers = tickers_util.all_tickers[:limit]
    
    return db_facade, config, sample_tickers


@profile
def memory_profile_calculate_indicators():
    """Memory profiling of calculate_indicators"""
    print("Starting memory profiling of calculate_indicators...")
    
    db_facade, config, sample_tickers = setup_test_environment(limit=30)
    
    print(f"Processing {len(sample_tickers)} tickers...")
    
    calculator = CalculateIndicators(db_facade, config)
    calculator.run(sample_tickers)
    
    db_facade.conn.close()
    print("Memory profiling completed.")


if __name__ == "__main__":
    print("Memory Profiler for Stockie")
    print("Run with: python -m memory_profiler memory_profiler.py")
    print("Or: mprof run memory_profiler.py && mprof plot")
    
    memory_profile_calculate_indicators()