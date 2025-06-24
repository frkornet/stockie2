from stockie.stock_price_ingestor import StockPriceIngestor
from stockie.config_loader import ConfigLoader
from stockie.custom_logger import CustomLogger
from stockie.market_calendar import MarketCalendar
from stockie.tickers import Tickers
import pandas as pd

def load_stock_prices():
    """
    Main function to load stock prices.
    This function initializes the logger, loads tickers, and starts the ingestion process.
    """

    # Load configuration
    config = ConfigLoader().get()

    # Initialize custom logger
    custom_logger = CustomLogger(
        name='stock_price_logger', 
        log_to_console=config['log']['console'],
        log_level=config['log']['level'], 
        log_dir=config['log']['dir'], 
        log_filename=config['log']['filename'], 
    )
    logger = custom_logger.get_logger()
    today = pd.Timestamp.today().normalize().date()
    logger.info(f"Starting stock price ingestion process for {today}...")

    # skip processing if today is not a trading day
    market_calendar = MarketCalendar(market='NYSE')
    if not market_calendar.is_trading_day():        
        logger.info(f"Today {today} is not a trading day. Exiting without processing.")
        return

    # Load tickers for which we need to download prices
    tickers = Tickers(logger)
    logger.info(len(tickers.get_all_tickers()))
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

if __name__ == "__main__":
    load_stock_prices()
