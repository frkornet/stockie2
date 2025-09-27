import argparse
from stockie.loaders.stock_price_ingestor import StockPriceIngestor
from stockie.loaders.config_loader import ConfigLoader
from stockie.log.custom_logger import CustomLogger
from stockie.util.market_calendar import MarketCalendar
from stockie.util.tickers import Tickers
import pandas as pd
import os

def load_stock_prices(config_dir):
    """
    Main function to load stock prices.
    This function initializes the logger, loads tickers, and starts the ingestion process.
    """

    # Load configuration
    config = ConfigLoader(
        config_path=os.path.join(config_dir, "settings.yaml"),
        dotenv_path=os.path.join(config_dir, ".env")
    ).get()

    # Initialize custom logger
    prices_config = config['load_stock_prices']
    logger = CustomLogger(
        name=__name__,        
        log_to_console=prices_config['console'],
        log_level=prices_config['log_level'], 
        log_dir=os.path.dirname(prices_config['log_filename']), 
        log_filename=prices_config['log_filename'], 
    ).get_logger()
    today = pd.Timestamp.today().normalize().date()
    logger.info(f"\n\n *** Starting stock price ingestion process for {today}...")

    # skip processing if today is not a trading day
    market_calendar = MarketCalendar(market='NYSE')
    if not market_calendar.is_trading_day():        
        logger.info(f"Today {today} is not a trading day. Exiting without processing.")
        logger.info(f'*** Finished load stock prices job.')
        return

    # Load tickers for which we need to download prices
    tickers = Tickers(logger)
    logger.info(len(tickers.all_tickers))
    logger.info(f'{len(tickers.nsye_tickers)=} {tickers.nsye_tickers=}')
    logger.info(f'{len(tickers.nyse_american_tickers)=} {tickers.nyse_american_tickers=}')
    logger.info(f'{len(tickers.nyse_arca_tickers)=} {tickers.nyse_arca_tickers=}')
    logger.info(f'{len(tickers.sp500_tickers)=} {tickers.sp500_tickers=}')
    logger.info(f'{len(tickers.dow30_tickers)=} {tickers.dow30_tickers=}')
    logger.info(f'{len(tickers.russell2000_tickers)=} {tickers.russell2000_tickers=}')
    logger.info(f'{len(tickers.nasdaq_tickers)=} {tickers.nasdaq_tickers=}')
    logger.info(f'{len(tickers.nasdaq100_tickers)=} {tickers.nasdaq100_tickers=}')
    logger.info(f'{len(tickers.all_tickers)=} {tickers.all_tickers=}')

    # Normalize tickers (i.e. replace '.' with '-' and '$' with '-')
    all_tickers = tickers.all_tickers
    normalized_tickers = [t.replace(".", "-") for t in all_tickers]
    normalized_tickers = [t.replace("$", "-") for t in normalized_tickers]
    logger.info(f'{len(normalized_tickers)=} {normalized_tickers=}')

    # Call StockPriceIngestor to download prices for normalized tickers
    db_config = config['db']
    start_date = config['start_date']
    ingestor = StockPriceIngestor(
        db_config=db_config,
        start_date=start_date,
        logger=logger,
    )
    ingestor.download(tickers=normalized_tickers)
    logger.info(f'*** Finished load stock prices job.')

def main():
    parser = argparse.ArgumentParser(description="Load stock prices from configured tickers.")
    parser.add_argument("--config-dir", default="/mnt/repos/stockie/config/", help="Directory containing settings.yaml and .env")
    args = parser.parse_args()
    load_stock_prices(args.config_dir)

if __name__ == "__main__":
    main()
