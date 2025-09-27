import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_config():
    return {
        "load_stock_prices": {
            "console": True,
            "log_level": "INFO",
            "log_filename": "/tmp/test.log"
        },
        "db": {"dbname": "testdb", "user": "user", "password": "pw", "host": "localhost"},
        "start_date": "2020-01-01"
    }

def test_load_stock_prices_success(monkeypatch, mock_config):
    mock_logger = MagicMock()
    mock_market_calendar = MagicMock()
    mock_market_calendar.is_trading_day.return_value = True
    mock_tickers = MagicMock()
    mock_tickers.all_tickers = ["AAPL", "GOOG"]
    mock_tickers.nsye_tickers = []
    mock_tickers.nyse_american_tickers = []
    mock_tickers.nyse_arca_tickers = []
    mock_tickers.sp500_tickers = []
    mock_tickers.dow30_tickers = []
    mock_tickers.russell2000_tickers = []
    mock_tickers.nasdaq_tickers = []
    mock_tickers.nasdaq100_tickers = []

    mock_ingestor = MagicMock()

    with patch("stockie.loaders.load_stock_prices.ConfigLoader") as mock_loader, \
         patch("stockie.loaders.load_stock_prices.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_stock_prices.MarketCalendar", return_value=mock_market_calendar), \
         patch("stockie.loaders.load_stock_prices.Tickers", return_value=mock_tickers), \
         patch("stockie.loaders.load_stock_prices.StockPriceIngestor", return_value=mock_ingestor):

        mock_loader.return_value.get.return_value = mock_config
        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.loaders.load_stock_prices import load_stock_prices
        load_stock_prices("/tmp/")
        mock_ingestor.download.assert_called_once_with(tickers=["AAPL", "GOOG"])

def test_load_stock_prices_not_trading_day(monkeypatch, mock_config):
    mock_logger = MagicMock()
    mock_market_calendar = MagicMock()
    mock_market_calendar.is_trading_day.return_value = False

    with patch("stockie.loaders.load_stock_prices.ConfigLoader") as mock_loader, \
         patch("stockie.loaders.load_stock_prices.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_stock_prices.MarketCalendar", return_value=mock_market_calendar):

        mock_loader.return_value.get.return_value = mock_config
        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.loaders.load_stock_prices import load_stock_prices
        load_stock_prices("/tmp/")
        assert any(
            "is not a trading day. Exiting without processing." in str(call.args[0])
            for call in mock_logger.info.call_args_list
        )
        mock_logger.info.assert_any_call('*** Finished load stock prices job.')

def test_load_stock_prices_trading_day(monkeypatch, mock_config):
    with patch("stockie.loaders.load_stock_prices.ConfigLoader") as mock_config_loader, \
         patch("stockie.loaders.load_stock_prices.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_stock_prices.MarketCalendar") as mock_market_calendar_class, \
         patch("stockie.loaders.load_stock_prices.Tickers") as mock_tickers_class, \
         patch("stockie.loaders.load_stock_prices.StockPriceIngestor") as mock_ingestor_class:
        mock_config_loader.return_value.get.return_value = mock_config
        mock_logger = MagicMock()
        mock_logger_class.return_value.get_logger.return_value = mock_logger
        mock_market_calendar = MagicMock()
        mock_market_calendar.is_trading_day.return_value = True
        mock_market_calendar_class.return_value = mock_market_calendar

        mock_tickers = MagicMock()
        mock_tickers.all_tickers = ["AAPL", "GOOG"]
        mock_tickers.nsye_tickers = []
        mock_tickers.nyse_american_tickers = []
        mock_tickers.nyse_arca_tickers = []
        mock_tickers.sp500_tickers = []
        mock_tickers.dow30_tickers = []
        mock_tickers.russell2000_tickers = []
        mock_tickers.nasdaq_tickers = []
        mock_tickers.nasdaq100_tickers = []
        mock_tickers_class.return_value = mock_tickers

        mock_ingestor = MagicMock()
        mock_ingestor_class.return_value = mock_ingestor

        from stockie.loaders.load_stock_prices import load_stock_prices
        load_stock_prices("/tmp/")
        mock_ingestor.download.assert_called_once_with(tickers=["AAPL", "GOOG"])
        mock_logger.info.assert_any_call('*** Finished load stock prices job.')

def test_load_stock_prices_handles_exception(monkeypatch, mock_config):
    with patch("stockie.loaders.load_stock_prices.ConfigLoader") as mock_config_loader, \
         patch("stockie.loaders.load_stock_prices.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_stock_prices.MarketCalendar") as mock_market_calendar_class, \
         patch("stockie.loaders.load_stock_prices.Tickers") as mock_tickers_class, \
         patch("stockie.loaders.load_stock_prices.StockPriceIngestor") as mock_ingestor_class:
        mock_config_loader.return_value.get.return_value = mock_config
        mock_logger = MagicMock()
        mock_logger_class.return_value.get_logger.return_value = mock_logger
        mock_market_calendar = MagicMock()
        mock_market_calendar.is_trading_day.return_value = True
        mock_market_calendar_class.return_value = mock_market_calendar

        mock_tickers = MagicMock()
        mock_tickers.all_tickers = ["AAPL"]
        mock_tickers.nsye_tickers = []
        mock_tickers.nyse_american_tickers = []
        mock_tickers.nyse_arca_tickers = []
        mock_tickers.sp500_tickers = []
        mock_tickers.dow30_tickers = []
        mock_tickers.russell2000_tickers = []
        mock_tickers.nasdaq_tickers = []
        mock_tickers.nasdaq100_tickers = []
        mock_tickers_class.return_value = mock_tickers

        mock_ingestor = MagicMock()
        mock_ingestor.download.side_effect = Exception("Download failed")
        mock_ingestor_class.return_value = mock_ingestor

        from stockie.loaders.load_stock_prices import load_stock_prices
        with pytest.raises(Exception, match="Download failed"):
            load_stock_prices("/tmp/")