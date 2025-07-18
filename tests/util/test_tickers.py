import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from stockie.util import Tickers

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

    @patch("stockie.util.tickers.ConfigLoader")
    def test_get_dow30_tickers(self, mock_config_loader, mock_logger, ticker_config_all_true):
        mock_config_loader().get.return_value = ticker_config_all_true
        tickers = Tickers(mock_logger)
        expected = [
            "AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW", "GS", "HD",
            "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "PG",
            "TRV", "UNH", "V", "VZ", "WBA", "WMT"
        ]
        assert tickers.dow30_tickers == expected

    @patch("stockie.util.tickers.pd.read_html")
    @patch("stockie.util.tickers.ConfigLoader")
    def test_get_sp500_tickers(self, mock_config_loader, mock_read_html, mock_logger, ticker_config_all_true):
        mock_config_loader().get.return_value = ticker_config_all_true
        mock_df = pd.DataFrame({"Symbol": ["AAPL", "MSFT", "GOOGL"]})
        mock_read_html.return_value = [mock_df]

        tickers = Tickers(mock_logger)
        assert tickers.sp500_tickers == ["AAPL", "MSFT", "GOOGL"]

    @patch("stockie.util.tickers.pd.read_csv")
    @patch("stockie.util.tickers.ConfigLoader")
    def test_get_nyse_tickers(self, mock_config_loader, mock_read_csv, mock_logger):
        config = {
            "tickers": {
                "nyse":  True,  "nyse_american": False, "nyse_arca": True,
                "sp500": False, "dow30": False, "nasdaq": False, "nasdaq100": False, "russell2000": False
            }
        }
        mock_config_loader().get.return_value = config

        mock_df = pd.DataFrame({
            "ACT Symbol": ["AAPL", "MSFT", "TSLA"],
            "Exchange": ["N", "N", "P"]
        })
        mock_read_csv.return_value = mock_df
        tickers = Tickers(mock_logger)

        assert tickers.nsye_tickers == ["AAPL", "MSFT"]
        assert tickers.nyse_arca_tickers == ["TSLA"]

    @patch("stockie.util.tickers.pd.read_csv")
    @patch("stockie.util.tickers.ConfigLoader")
    def test_get_nasdaq_tickers(self, mock_config_loader, mock_read_csv, mock_logger, ticker_config_all_true):
        config = {
            "tickers": {
                "nyse":  False,  "nyse_american": False, "nyse_arca": False,
                "nasdaq": True, "nasdaq100": True,
                "sp500": False, "dow30": False,  "russell2000": False
            }
        }
        mock_config_loader().get.return_value = config
        mock_df = pd.DataFrame({
            "Symbol": ["AAPL", "TSLA", None]
        })
        mock_read_csv.return_value = mock_df

        tickers = Tickers(mock_logger)
        assert tickers.nasdaq_tickers == ["AAPL", "TSLA"]

    @patch("stockie.util.tickers.requests.get")
    @patch("stockie.util.tickers.ConfigLoader")
    def test_get_nasdaq100_tickers(self, mock_config_loader, mock_requests_get, mock_logger, ticker_config_all_true):
        mock_config_loader().get.return_value = ticker_config_all_true
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

        tickers = Tickers(mock_logger)
        assert tickers.nasdaq100_tickers == ["AAPL", "TSLA"]

    @patch("stockie.util.tickers.ConfigLoader")
    def test_get_all_tickers(self, mock_config_loader, mock_logger):
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
        mock_config_loader().get.return_value = config
        tickers = Tickers(mock_logger)
        assert tickers.get_all_tickers() == tickers.dow30_tickers