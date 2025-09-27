import argparse
import time
import os
from datetime import datetime
from stockie.loaders.load_stock_prices import load_stock_prices
from stockie.loaders.load_indicators import load_technical_indicators
from stockie.indicators.calculate_indicators import calculate_indicators
from stockie.loaders.config_loader import ConfigLoader
from stockie.log.custom_logger import CustomLogger

def run_daily_job(config_dir):
    start_job = time.time()
    config = ConfigLoader(
        config_path=os.path.join(config_dir, "settings.yaml"),
        dotenv_path=os.path.join(config_dir, ".env")
    ).get()['daily_job']

    logger = CustomLogger(
        name=__file__,
        log_to_console=config['console'],
        log_level=config['log_level'],
        log_dir=os.path.dirname(config['log_filename']),
        log_filename=os.path.basename(config['log_filename'])
    ).get_logger()
    logger.info(f'\n\n**** Starting daily job at {datetime.fromtimestamp(start_job)}')

    if config['load_stock_prices']:
        start_stock_prices = time.time()
        logger.info(f'Running load stock prices at {datetime.fromtimestamp(start_stock_prices)}')
        load_stock_prices(config_dir)
        duration = (time.time() - start_stock_prices)/60
        logger.info(f'Load stock prices finished after {duration} minutes')

    if config['calculate_indicators']:
        start_calculate = time.time()
        logger.info(f'Running calculate technical indicators at {datetime.fromtimestamp(start_calculate)}')
        calculate_indicators(config_dir)
        duration = (time.time() - start_calculate)/60
        logger.info(f'Calculate technical indicators finished after {duration} minutes')

    if config['load_indicators']:
        start_load = time.time()
        logger.info(f'Running load technical indicators at {datetime.fromtimestamp(start_load)}')
        load_technical_indicators(config_dir)
        duration = (time.time() - start_load)/60
        logger.info(f'Load technical indicators finished after {duration} minutes')

    duration = (time.time() - start_job) / 60
    logger.info(f'*** Finished daily job in {duration} minutes')

def main():
    parser = argparse.ArgumentParser(description="Run the daily Stockie job.")
    parser.add_argument("--config-dir", default="/mnt/repos/stockie/config/", help="Directory containing settings.yaml and .env")
    args = parser.parse_args()
    run_daily_job(args.config_dir)

if __name__ == "__main__":
    main()