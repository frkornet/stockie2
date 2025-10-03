from stockie.util.tickers import Tickers
import pandas as pd
import os
import sys
from stockie.loaders.stock_price_ingestor import StockPriceIngestor
from stockie.log.custom_logger import CustomLogger

def load_stock_prices(db_facade, full_config: dict) -> None:
    """
    Load stock prices using the provided database facade and configuration.
    
    Args:
        db_facade: DatabaseFacade instance to use
        full_config: Full configuration dictionary
    """
    try:
        stock_config = full_config['load_stock_prices']
        
        # Create logger specific to load_stock_prices
        logger = CustomLogger(
            name=__file__,
            log_to_console=stock_config['console'],
            log_level=stock_config['log_level'],
            log_dir=os.path.dirname(stock_config['log_filename']),
            log_filename=os.path.basename(stock_config['log_filename'])
        ).get_logger()
        
        # Get tickers using the Tickers utility class
        tickers = Tickers(logger, full_config)
        
        logger.info(f"Loading stock prices for {len(tickers.all_tickers)} tickers")
        logger.debug(f"Tickers: {tickers.all_tickers}")
        
        # Create ingestor with provided database facade and config
        ingestor = StockPriceIngestor(
            db_facade=db_facade,
            start_date=full_config['start_date'],
            logger=logger,
            delta_threshold=full_config['delta_threshold'],
            batch_size=stock_config['batch_size'],
            max_consecutive_failures=stock_config['max_consecutive_batch_failures']
        )
        
        ingestor.download(tickers.all_tickers)
    
    except Exception as e:
        logger.error(f"FATAL: Failed to load stock prices: {e}")
        print(f"FATAL: Failed to load stock prices: {e}")
        sys.exit(1)
