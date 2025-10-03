import argparse
import time
import os
import sys
import psycopg2
from datetime import datetime
from stockie.loaders.load_stock_prices import load_stock_prices
from stockie.loaders.load_indicators import load_technical_indicators
from stockie.indicators.calculate_indicators import calculate_indicators
from stockie.loaders.config_loader import ConfigLoader
from stockie.log.custom_logger import CustomLogger
from stockie.db import DatabaseFacade

def run_daily_job(config_dir):
    start_job = time.time()
    logger = None
    conn = None
    
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
        conn = psycopg2.connect(**db_config)
        db_facade = DatabaseFacade(conn)
        logger.info(f"Connected to database: {conn.get_dsn_parameters().get('dbname', 'unknown')}")
        
    except Exception as e:
        print(f"FATAL: Failed to load configuration, initialize logger, or connect to database: {e}")
        sys.exit(1)

    logger.info(f'\n\n**** Starting daily job at {datetime.fromtimestamp(start_job)}')

    try:
        if daily_config['load_stock_prices']:
            start_stock_prices = time.time()
            logger.info(f'Running load stock prices at {datetime.fromtimestamp(start_stock_prices)}')
            load_stock_prices(db_facade, full_config)
            duration = (time.time() - start_stock_prices)/60
            logger.info(f'Load stock prices finished after {duration} minutes')

        if daily_config['calculate_indicators']:
            start_calculate = time.time()
            logger.info(f'Running calculate technical indicators at {datetime.fromtimestamp(start_calculate)}')
            calculate_indicators(db_facade, full_config)
            duration = (time.time() - start_calculate)/60
            logger.info(f'Calculate technical indicators finished after {duration} minutes')

        if daily_config['load_indicators']:
            start_load = time.time()
            logger.info(f'Running load technical indicators at {datetime.fromtimestamp(start_load)}')
            load_technical_indicators(db_facade, full_config)
            duration = (time.time() - start_load)/60
            logger.info(f'Load technical indicators finished after {duration} minutes')

        duration = (time.time() - start_job) / 60
        logger.info(f'*** Finished daily job successfully in {duration} minutes')
        
    except Exception as e:
        error_msg = f"DAILY JOB FAILED: {str(e)}"
        logger.error(error_msg)
        logger.error("Check the logs above for detailed error information")
        
        # Also print to console so user sees it even if logging fails
        print(f"\n{error_msg}")
        print("Daily job terminated due to error. Check logs for details.")
        sys.exit(1)
        
    finally:
        # Clean up database connection
        if conn:
            try:
                conn.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")

def main():
    parser = argparse.ArgumentParser(description="Run the daily Stockie job.")
    parser.add_argument("--config-dir", required=True, help="Directory containing settings.yaml and .env")
    args = parser.parse_args()
    if not os.path.isdir(args.config_dir):
        print(f"Error: Configuration directory '{args.config_dir}' does not exist")
        sys.exit(1)
    run_daily_job(args.config_dir)

if __name__ == "__main__":
    main()