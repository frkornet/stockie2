import argparse
import time
import os
import sys
import psycopg2
from datetime import datetime
from stockie.loaders.load_stock_prices import load_stock_prices
from stockie.indicators.calculate_indicators import calculate_indicators
from stockie.loaders.config_loader import ConfigLoader
from stockie.log.custom_logger import CustomLogger
from stockie.db import DatabaseFacade


def _initialize_components(config_dir: str) -> tuple:
    """Initialize logger, database connection, and configuration.
    
    Returns:
        Tuple of (logger, conn, db_facade, full_config)
    """
    try:
        # Load configuration once
        config_loader = ConfigLoader(config_dir)
        full_config = config_loader.get()
        daily_config = full_config['daily_job']
        db_config = full_config['db']
        
        # Add password from environment variable
        db_config['password'] = os.getenv('DB_PASSWORD')
        
        logger = CustomLogger(
            name=__file__,
            log_to_console=daily_config['console'],
            log_level=daily_config['log_level'],
            log_dir=os.path.dirname(daily_config['log_filename']),
            log_filename=os.path.basename(daily_config['log_filename'])
        ).get_logger()
        
        # Create single database connection and facade
        # Remove admin_user from connection params (it's used elsewhere, not by psycopg2)
        conn_params = {k: v for k, v in db_config.items() if k != 'admin_user'}
        conn = psycopg2.connect(**conn_params)
        db_facade = DatabaseFacade(conn)
        logger.info(f"Connected to database: {conn.get_dsn_parameters().get('dbname', 'unknown')}")
        
        return logger, conn, db_facade, full_config
        
    except Exception as e:
        print(f"FATAL: Failed to load configuration, initialize logger, or connect to database: {e}")
        sys.exit(1)


def _cleanup_temp_tables(db_facade: DatabaseFacade, owner: str, logger) -> None:
    """Drop any existing temp tables from previous failed runs."""
    logger.info('Phase 0: Cleaning up any existing leftover temporary tables...')
    db_facade.drop_stockie_tables(
        table_filter=['stock_prices', 'technical_indicators'],
        name_suffix='_temp'
    )
    logger.info('Cleanup complete')


def _create_temp_tables(db_facade: DatabaseFacade, owner: str, logger) -> None:
    """Create fresh temporary tables for stock prices and technical indicators."""
    logger.info('Phase 1: Creating temporary tables...')
    db_facade.create_temp_tables(owner)
    logger.info('Temporary tables created: stock_prices_temp, technical_indicators_temp')


def _load_prices_to_temp(db_facade: DatabaseFacade, full_config: dict, logger) -> None:
    """Load stock prices into temporary table."""
    daily_config = full_config['daily_job']
    if not daily_config['load_stock_prices']:
        logger.info('Phase 2: Stock price loading skipped (disabled in config)')
        return
    
    start_time = time.time()
    logger.info(f'Phase 2: Loading stock prices at {datetime.fromtimestamp(start_time)}')
    load_stock_prices(db_facade, full_config)
    duration = (time.time() - start_time) / 60
    logger.info(f'Stock prices loaded into temp table in {duration:.2f} minutes')


def _calculate_indicators_to_temp(db_facade: DatabaseFacade, full_config: dict, logger) -> None:
    """Calculate technical indicators from temp stock_prices, write to temp technical_indicators."""
    daily_config = full_config['daily_job']
    if not daily_config['calculate_indicators']:
        logger.info('Phase 3: Indicator calculation skipped (disabled in config)')
        return
    
    start_time = time.time()
    logger.info(f'Phase 3: Calculating technical indicators at {datetime.fromtimestamp(start_time)}')
    calculate_indicators(db_facade, full_config, source_table='stock_prices_temp')
    duration = (time.time() - start_time) / 60
    logger.info(f'Technical indicators calculated in {duration:.2f} minutes')


def _atomic_table_swap(db_facade: DatabaseFacade, owner: str, logger) -> None:
    """Perform atomic table swap to make temp tables live."""
    logger.info('Phase 4: Performing atomic table swap...')
    start_time = time.time()
    db_facade.atomic_table_swap()
    duration = time.time() - start_time
    logger.info(f'Atomic swap completed in {duration:.2f} seconds')
    logger.info('New data is now live in production tables')


def _handle_job_failure(e: Exception, logger) -> None:
    """Handle daily job failure with appropriate logging and error messages."""
    error_msg = f"DAILY JOB FAILED: {str(e)}"
    logger.error(error_msg)
    logger.error("Temp tables preserved for debugging. Check:")
    logger.error("  - stock_prices_temp")
    logger.error("  - technical_indicators_temp")
    logger.error("Run DROP TABLE manually after investigating")
    
    # Also print to console
    print(f"\n{error_msg}")
    print("Daily job terminated. Temp tables preserved for debugging.")
    sys.exit(1)


def _cleanup_database_connection(conn, logger) -> None:
    """Close database connection and log result."""
    if conn:
        try:
            conn.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")


def run_daily_job(config_dir: str) -> None:
    """Orchestrate the daily data pipeline: load prices, calculate indicators, swap to production."""
    start_job = time.time()
    
    # Initialize components
    logger, conn, db_facade, full_config = _initialize_components(config_dir)
    logger.info(f'\n\n**** Starting daily job at {datetime.fromtimestamp(start_job)}')
    
    try:
        owner = full_config['db']['user']
        
        # Execute 5-phase workflow
        _cleanup_temp_tables(db_facade, owner, logger)
        _create_temp_tables(db_facade, owner, logger)
        _load_prices_to_temp(db_facade, full_config, logger)
        _calculate_indicators_to_temp(db_facade, full_config, logger)
        _atomic_table_swap(db_facade, owner, logger)
        
        # Log successful completion
        total_duration = (time.time() - start_job) / 60
        logger.info(f'*** Finished daily job successfully in {total_duration:.2f} minutes')
        
    except Exception as e:
        _handle_job_failure(e, logger)
        
    finally:
        _cleanup_database_connection(conn, logger)

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the daily Stockie job.")
    parser.add_argument("--config-dir", required=True, help="Directory containing settings.yaml and .env")
    args = parser.parse_args()
    if not os.path.isdir(args.config_dir):
        print(f"Error: Configuration directory '{args.config_dir}' does not exist")
        sys.exit(1)
    run_daily_job(args.config_dir)

if __name__ == "__main__":
    main()