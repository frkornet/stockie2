import pytest
import pandas as pd
import csv
from unittest.mock import patch, MagicMock

@pytest.fixture
def sample_df():
    df = pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=30),
        "close": range(100, 130)
    })
    df = df.set_index("date")
    return df

@pytest.fixture
def mock_config():
    return {
        "db": {"dbname": "testdb", "user": "user", "password": "pw", "host": "localhost"},
        "indicators": {
            "momentum": {
                "rsi": {"enabled": True, "window": 14}
            },
            "performance": {
                "daily_return": {"enabled": True}
            },
            "risk": {
                "sharpe": {"enabled": True, "window": [21, 63], "risk_free_rate": 0.04}
            }
        },
        "calculate_indicators": {
            "console": True,
            "log_level": "INFO",
            "log_filename": "/tmp/test.log",
            "csv_directory": "/tmp/",
            "save_every_n_tickers": 10,
            "concatenate_dataframes": True,
            "calculate_processes": 1
        }
    }

@pytest.fixture(autouse=True)
def mock_logger():
    with patch("stockie.log.custom_logger.CustomLogger.get_logger", return_value=MagicMock()):
        yield

class TestCalculateIndicators:
    def test_calculate_indicators_calls_all_enabled(self, sample_df, mock_config):
        with patch("stockie.indicators.momentum.MomentumIndicators.rsi") as mock_rsi, \
             patch("stockie.indicators.performance.PerformanceIndicators.daily_return") as mock_daily_returns, \
             patch("stockie.indicators.risk.RiskIndicators.sharpe") as mock_sharpe:

            mock_db_util = MagicMock()
            mock_db_util.fetch_price_data.return_value = sample_df

            from stockie.indicators.calculate_indicators import CalculateIndicators
            runner = CalculateIndicators(mock_db_util, mock_config)
            runner.run(["AAPL"])

            mock_rsi.assert_called_once()
            call_args, call_kwargs = mock_rsi.call_args
            assert call_kwargs["window"] == 14

            mock_daily_returns.assert_called_once()

            assert mock_sharpe.call_count == 2
            mock_sharpe.assert_any_call(window=21, risk_free_rate=0.04)
            mock_sharpe.assert_any_call(window=63, risk_free_rate=0.04)

    def test_calculate_indicators_skips_disabled(self, sample_df, mock_config):
        disabled_config = {
            "indicators": {
                "momentum": {"rsi": {"enabled": False, "window": 14}},
                "performance": {"daily_return": {"enabled": False}},
                "risk": {"sharpe": {"enabled": False, "window": [21, 63], "risk_free_rate": 0.04}}
            },
            "calculate_indicators": {
                "console": True,
                "log_level": "INFO",
                "log_filename": "/tmp/test.log",
                "csv_directory": "/tmp/",
                "save_every_n_tickers": 10,
                "concatenate_dataframes": True
            }
        }
        with patch("stockie.indicators.momentum.MomentumIndicators.rsi") as mock_rsi, \
             patch("stockie.indicators.performance.PerformanceIndicators.daily_return") as mock_daily_return, \
             patch("stockie.indicators.risk.RiskIndicators.sharpe") as mock_sharpe:

            mock_db_util = MagicMock()
            mock_db_util.fetch_price_data.return_value = sample_df

            from stockie.indicators.calculate_indicators import CalculateIndicators
            runner = CalculateIndicators(mock_db_util, disabled_config)
            runner.run(["AAPL"])

            mock_rsi.assert_not_called()
            mock_daily_return.assert_not_called()
            mock_sharpe.assert_not_called()

    def test_run_with_empty_ticker_list(self, mock_config):
        mock_db_util = MagicMock()
        from stockie.indicators.calculate_indicators import CalculateIndicators
        runner = CalculateIndicators(mock_db_util, mock_config)
        runner.run([])

    def test_run_with_missing_close_column(self, sample_df, mock_config):
        df_no_close = sample_df.drop(columns=["close"])
        mock_db_util = MagicMock()
        mock_db_util.fetch_price_data.return_value = df_no_close
        from stockie.indicators.calculate_indicators import CalculateIndicators
        runner = CalculateIndicators(mock_db_util, mock_config)
        runner.run(["AAPL"])

    def test_run_with_mismatched_list_lengths(self, sample_df):
        bad_config = {
            "indicators": {
                "risk": {
                    "sharpe": {"enabled": True, "window": [21, 63], "risk_free_rate": [0.01]}
                }
            },
            "calculate_indicators": {
                "console": True,
                "log_level": "INFO",
                "log_filename": "/tmp/test.log",
                "csv_directory": "/tmp/",
                "save_every_n_tickers": 10,
                "concatenate_dataframes": True
            }
        }
        mock_db_util = MagicMock()
        mock_db_util.fetch_price_data.return_value = sample_df
        from stockie.indicators.calculate_indicators import CalculateIndicators
        runner = CalculateIndicators(mock_db_util, bad_config)
        with pytest.raises(ValueError):
            runner.run(["AAPL"])

    def test_run_with_module_not_found(self, sample_df, mock_config):
        config = mock_config.copy()
        config["indicators"]["fakefamily"] = {
            "fakeindicator": {"enabled": True}
        }
        mock_db_util = MagicMock()
        mock_db_util.fetch_price_data.return_value = sample_df
        from stockie.indicators.calculate_indicators import CalculateIndicators
        runner = CalculateIndicators(mock_db_util, config)
        runner.run(["AAPL"])

    def test_run_with_attribute_error(self, sample_df, mock_config):
        config = mock_config.copy()
        config["indicators"]["momentum"]["fakeindicator"] = {"enabled": True}
        mock_db_util = MagicMock()
        mock_db_util.fetch_price_data.return_value = sample_df
        from stockie.indicators.calculate_indicators import CalculateIndicators
        runner = CalculateIndicators(mock_db_util, config)
        runner.run(["AAPL"])

    def test_calculate_indicators_single_process(self, mock_config):
        mock_db_facade = MagicMock()
        mock_db_facade.get_unique_tickers.return_value = ["AAPL", "GOOG"]
        mock_runner = MagicMock()

        config = mock_config.copy()
        config["calculate_indicators"]["calculate_processes"] = 1

        with patch("stockie.indicators.calculate_indicators.CalculateIndicators", return_value=mock_runner):
            from stockie.indicators.calculate_indicators import calculate_indicators
            calculate_indicators(mock_db_facade, config)
            mock_runner.run.assert_called_once_with(["AAPL", "GOOG"])

    def test_calculate_indicators_multi_process(self, mock_config):
        mock_db_facade = MagicMock()
        mock_db_facade.get_unique_tickers.return_value = ["AAPL", "GOOG"]
        mock_process = MagicMock()

        config = mock_config.copy()
        # Update config to enable multiprocessing
        config["calculate_indicators"]["calculate_processes"] = 2
        config["tickers"] = {"benchmarks": ["SPY"]}

        with patch("stockie.indicators.calculate_indicators.multiprocessing.Process", return_value=mock_process):
            from stockie.indicators.calculate_indicators import calculate_indicators
            calculate_indicators(mock_db_facade, config)
            assert mock_process.start.call_count == 2
            assert mock_process.join.call_count == 2

    def test_calculate_indicators_db_connection_failure(self, mock_config):
        mock_db_facade = MagicMock()
        mock_db_facade.get_unique_tickers.side_effect = Exception("DB fail")
        
        config = mock_config.copy()
        config["calculate_indicators"]["calculate_processes"] = 1

        from stockie.indicators.calculate_indicators import calculate_indicators
        with pytest.raises(Exception, match="DB fail"):
            calculate_indicators(mock_db_facade, config)

    def test_calculate_indicators_no_tickers(self, mock_config):
        mock_db_facade = MagicMock()
        mock_db_facade.get_unique_tickers.return_value = []
        mock_runner = MagicMock()

        config = mock_config.copy()
        config["calculate_indicators"]["calculate_processes"] = 1

        with patch("stockie.indicators.calculate_indicators.CalculateIndicators", return_value=mock_runner):
            from stockie.indicators.calculate_indicators import calculate_indicators
            calculate_indicators(mock_db_facade, config)
            mock_runner.run.assert_called_once_with([])

    def test_worker_function(self, mock_config):
        mock_conn = MagicMock()
        mock_db_util = MagicMock()
        mock_runner = MagicMock()

        config = mock_config.copy()
        config["db"] = {"dbname": "testdb", "user": "user", "password": "pw", "host": "localhost"}

        tickers_chunk = ["AAPL", "GOOG"]
        part = 0

        with patch("stockie.indicators.calculate_indicators.psycopg2.connect", return_value=mock_conn), \
             patch("stockie.indicators.calculate_indicators.DatabaseFacade", return_value=mock_db_util), \
             patch("stockie.indicators.calculate_indicators.CalculateIndicators", return_value=mock_runner):

            from stockie.indicators.calculate_indicators import worker
            worker(tickers_chunk, config, part)
            mock_runner.run.assert_called_once_with(tickers_chunk, part)
            mock_conn.close.assert_called_once()

    def test_vacuum_full_success_integration(self, sample_df, mock_config):
        """Test that VACUUM FULL is executed successfully after indicator calculation"""
        from stockie.indicators.calculate_indicators import CalculateIndicators
        
        # Mock database facade with vacuum method
        mock_db_util = MagicMock()
        mock_db_util.fetch_price_data.return_value = sample_df
        mock_db_util.vacuum_full_table.return_value = {
            'success': True,
            'duration_minutes': 2.5,
            'error_message': None
        }
        
        # Create indicator runner
        runner = CalculateIndicators(mock_db_util, mock_config)
        
        # Mock indicator calculations to avoid complex setup
        with patch.object(runner, '_save_batch_indicators'):
            runner.run(['AAPL'])
        
        # Verify VACUUM FULL was called
        mock_db_util.vacuum_full_table.assert_called_once_with('technical_indicators')

    def test_vacuum_full_failure_integration(self, sample_df, mock_config):
        """Test that VACUUM FULL failure is handled gracefully"""
        from stockie.indicators.calculate_indicators import CalculateIndicators
        
        # Mock database facade with failing vacuum method
        mock_db_util = MagicMock()
        mock_db_util.fetch_price_data.return_value = sample_df
        mock_db_util.vacuum_full_table.return_value = {
            'success': False,
            'duration_minutes': 0,
            'error_message': 'VACUUM failed: disk full'
        }
        
        # Create indicator runner
        runner = CalculateIndicators(mock_db_util, mock_config)
        
        # Mock indicator calculations to avoid complex setup
        with patch.object(runner, '_save_batch_indicators'):
            runner.run(['AAPL'])
        
        # Verify VACUUM FULL was called even though it failed
        mock_db_util.vacuum_full_table.assert_called_once_with('technical_indicators')
