import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_config():
    return {
        "load_stock_prices": {
            "console": True,
            "log_level": "INFO",
            "log_filename": "/tmp/test.log",
            "batch_size": 100,
            "max_consecutive_batch_failures": 10
        },
        "db": {"dbname": "testdb", "user": "user", "password": "pw", "host": "localhost"},
        "start_date": "2020-01-01",
        "delta_threshold": 0.0001,
        "tickers": {
            "benchmarks": ["SPY"],
            "nyse": False,
            "sp500": True
        }
    }

def test_load_stock_prices_success(mock_config):
    mock_db_facade = MagicMock()
    mock_tickers = MagicMock()
    mock_tickers.all_tickers = ["AAPL", "GOOG"]
    mock_ingestor = MagicMock()
    mock_custom_logger = MagicMock()
    mock_logger = MagicMock()
    mock_custom_logger.get_logger.return_value = mock_logger

    with patch("stockie.loaders.load_stock_prices.Tickers", return_value=mock_tickers), \
         patch("stockie.loaders.load_stock_prices.StockPriceIngestor", return_value=mock_ingestor), \
         patch("stockie.loaders.load_stock_prices.CustomLogger", return_value=mock_custom_logger):

        from stockie.loaders.load_stock_prices import load_stock_prices
        load_stock_prices(mock_db_facade, mock_config)
        mock_ingestor.download.assert_called_once_with(["AAPL", "GOOG"])

def test_load_stock_prices_handles_exception(mock_config):
    mock_db_facade = MagicMock()
    mock_tickers = MagicMock()
    mock_tickers.all_tickers = ["AAPL"]
    mock_ingestor = MagicMock()
    mock_ingestor.download.side_effect = Exception("Download failed")
    mock_custom_logger = MagicMock()
    mock_logger = MagicMock()
    mock_custom_logger.get_logger.return_value = mock_logger

    with patch("stockie.loaders.load_stock_prices.Tickers", return_value=mock_tickers), \
         patch("stockie.loaders.load_stock_prices.StockPriceIngestor", return_value=mock_ingestor), \
         patch("stockie.loaders.load_stock_prices.CustomLogger", return_value=mock_custom_logger):

        from stockie.loaders.load_stock_prices import load_stock_prices
        with pytest.raises(SystemExit):
            load_stock_prices(mock_db_facade, mock_config)