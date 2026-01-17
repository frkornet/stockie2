# tests/util/test_tickers.py

import pytest
import os
import tempfile
import yaml
import pandas as pd
from unittest.mock import patch, MagicMock
from stockie.util.tickers import Tickers

@pytest.fixture
def default_ticker_config():
    """Default ticker configuration with all sources disabled"""
    return {
        "tickers": {
            "nyse": False,
            "nyse_american": False,
            "nyse_arca": False,
            "sp500": False,
            "dow30": False,
            "nasdaq": False,
            "nasdaq100": False,
            "russell2000": False
        }
    }

@pytest.fixture
def temp_config_dir(default_ticker_config):
    """Create a temporary directory with test config files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create .env file
        env_content = "ENVIRONMENT=dev\nDB_PASSWORD=test_password\n"
        with open(os.path.join(temp_dir, '.env'), 'w') as f:
            f.write(env_content)
        
        # Create settings-dev.yaml with default ticker config
        with open(os.path.join(temp_dir, 'settings-dev.yaml'), 'w') as f:
            yaml.dump(default_ticker_config, f)
        
        yield temp_dir

def test_tickers_init():
    """Test Tickers initialization"""
    mock_logger = MagicMock()
    full_config = {
        "tickers": {
            "benchmarks": ["SPY"],
            "nyse": False,
            "sp500": True
        }
    }
    tickers = Tickers(mock_logger, full_config)
    assert tickers is not None

class TestTickers:

    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def ticker_config_all_true(self):
        return {
            "tickers": {
                "nyse": True,
                "nyse_american": True,
                "nyse_arca": True,
                "sp500": True,
                "dow30": True,
                "russell2000": True,
                "nasdaq": True,
                "nasdaq100": True
            }
        }

    @patch("stockie.util.tickers.pd.read_html")
    def test_get_sp500_tickers(self, mock_read_html, mock_logger, ticker_config_all_true):
        # Mock a table with 503 rows (typical S&P 500 count) that will match our logic
        mock_df = pd.DataFrame({"Symbol": ["AAPL", "MSFT", "GOOGL"] + ["TEST"] * 500})
        # Mock multiple tables like real Wikipedia page - table 1 has the S&P 500 data
        mock_read_html.return_value = [pd.DataFrame(), mock_df]  # Empty table 0, S&P data in table 1

        tickers = Tickers(mock_logger, ticker_config_all_true)
        assert tickers.sp500_tickers == ["AAPL", "MSFT", "GOOGL"] + ["TEST"] * 500

    def test_get_dow30_tickers(self, mock_logger, ticker_config_all_true):
        tickers = Tickers(mock_logger, ticker_config_all_true)
        expected = [
            "AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW", "GS", "HD",
            "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "PG",
            "TRV", "UNH", "V", "VZ", "WBA", "WMT"
        ]
        assert tickers.dow30_tickers == expected

    @patch("stockie.util.tickers.pd.read_csv")
    def test_get_nyse_tickers(self, mock_read_csv, mock_logger):
        config = {
            "tickers": {
                "nyse": True,
                "nyse_american": False,
                "nyse_arca": True,
                "sp500": False,
                "dow30": False,
                "nasdaq": False,
                "nasdaq100": False,
                "russell2000": False
            }
        }
        mock_df = pd.DataFrame({
            "ACT Symbol": ["AAPL", "MSFT", "TSLA"],
            "Exchange": ["N", "N", "P"]
        })
        mock_read_csv.return_value = mock_df

        tickers = Tickers(mock_logger, config)
        assert tickers.nsye_tickers == ["AAPL", "MSFT"]
        assert tickers.nyse_arca_tickers == ["TSLA"]

    @patch("stockie.util.tickers.pd.read_csv")
    def test_get_nasdaq_tickers(self, mock_read_csv, mock_logger):
        config = {
            "tickers": {
                "nyse": False,
                "nyse_american": False,
                "nyse_arca": False,
                "nasdaq": True,
                "nasdaq100": False,
                "sp500": False,
                "dow30": False,
                "russell2000": False
            }
        }
        mock_df = pd.DataFrame({"Symbol": ["AAPL", "TSLA", None]})
        mock_read_csv.return_value = mock_df

        tickers = Tickers(mock_logger, config)
        assert tickers.nasdaq_tickers == ["AAPL", "TSLA"]

    @patch("stockie.util.tickers.requests.get")
    def test_get_nasdaq100_tickers(self, mock_requests_get, mock_logger, ticker_config_all_true):

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "data": {
                    "rows": [
                        {"symbol": "AAPL"},
                        {"symbol": "TSLA"}
                    ]
                }
            }
        }
        mock_requests_get.return_value = mock_response

        tickers = Tickers(mock_logger, ticker_config_all_true)
        assert tickers.nasdaq100_tickers == ["AAPL", "TSLA"]

    def test_get_all_tickers(self, mock_logger):
        config = {
            "tickers": {
                "nyse": False,
                "nyse_american": False,
                "nyse_arca": False,
                "sp500": False,
                "dow30": True,
                "nasdaq": False,
                "nasdaq100": False,
                "russell2000": False
            }
        }
        tickers = Tickers(mock_logger, config)
        assert tickers.all_tickers == tickers.dow30_tickers

    def test_cryptocurrencies(self, mock_logger):
        """Test that cryptocurrencies property returns configured crypto tickers"""
        config = {
            "tickers": {
                "benchmarks": ["SPY"],
                "cryptocurrencies": ["BTC-USD", "ETH-USD", "SOL-USD"],
                "nyse": False,
                "nyse_american": False,
                "nyse_arca": False,
                "sp500": False,
                "dow30": False,
                "nasdaq": False,
                "nasdaq100": False,
                "russell2000": False
            }
        }
        tickers = Tickers(mock_logger, config)
        assert tickers.cryptocurrencies == ["BTC-USD", "ETH-USD", "SOL-USD"]
