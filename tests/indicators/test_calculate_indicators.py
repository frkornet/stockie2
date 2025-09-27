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
            "cvs_directory": "/tmp/",
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
                "cvs_directory": "/tmp/",
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
                "cvs_directory": "/tmp/",
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

    def test_save_dfs_to_cvs_non_concatenate(self, tmp_path, sample_df, mock_config):
        # Setup CalculateIndicators with concatenate_dataframes=False
        config = mock_config.copy()
        config["calculate_indicators"]["concatenate_dataframes"] = False
        config["calculate_indicators"]["cvs_directory"] = str(tmp_path) + "/"
        config["calculate_indicators"]["log_filename"] = str(tmp_path / "test.log")

        mock_db_util = MagicMock()
        from stockie.indicators.calculate_indicators import CalculateIndicators
        runner = CalculateIndicators(mock_db_util, config)
        runner.cvs_file_name = str(tmp_path / "indicators_part_0.csv")
        runner.cvs_header = True

        # Prepare ticker_df_cache with two non-empty DataFrames
        runner.ticker_df_cache = {
            "AAPL": sample_df.assign(ticker="AAPL", indicator="rsi", value=1.0).reset_index(),
            "GOOG": sample_df.assign(ticker="GOOG", indicator="rsi", value=2.0).reset_index()
        }

        # Patch to_csv to monitor calls
        with patch.object(pd.DataFrame, "to_csv", autospec=True) as mock_to_csv:
            runner._save_dfs_to_cvs("AAPL", 0)
            # Should call to_csv twice (once for each ticker)
            assert mock_to_csv.call_count == 2
            # Should use the correct file name and header True for first call, False for second
            first_call = mock_to_csv.call_args_list[0]
            second_call = mock_to_csv.call_args_list[1]
            assert first_call.kwargs["header"] is True
            assert second_call.kwargs["header"] is False
            assert first_call.kwargs["mode"] == "a"
            assert second_call.kwargs["mode"] == "a"
            assert first_call.kwargs["encoding"] == "utf-8"
            assert second_call.kwargs["encoding"] == "utf-8"

    def test_save_dfs_to_cvs_else_block(self, tmp_path, sample_df, mock_config):
        # Setup config to use non-concatenate mode
        config = mock_config.copy()
        config["calculate_indicators"]["concatenate_dataframes"] = False
        config["calculate_indicators"]["cvs_directory"] = str(tmp_path) + "/"
        config["calculate_indicators"]["log_filename"] = str(tmp_path / "test.log")

        mock_db_util = MagicMock()
        from stockie.indicators.calculate_indicators import CalculateIndicators
        runner = CalculateIndicators(mock_db_util, config)
        runner.cvs_file_name = str(tmp_path / "indicators_part_0.csv")
        runner.cvs_header = True

        # Create two non-empty DataFrames and one empty DataFrame in the cache
        df1 = sample_df.assign(ticker="AAPL", indicator="rsi", value=1.0).reset_index()
        df2 = sample_df.assign(ticker="GOOG", indicator="rsi", value=2.0).reset_index()
        df_empty = pd.DataFrame(columns=df1.columns)
        runner.ticker_df_cache = {
            "AAPL": df1,
            "GOOG": df2,
            "EMPTY": df_empty
        }

        # Patch to_csv to monitor calls
        with patch.object(pd.DataFrame, "to_csv", autospec=True) as mock_to_csv:
            runner._save_dfs_to_cvs("AAPL", 0)
            # Should call to_csv only for non-empty DataFrames
            assert mock_to_csv.call_count == 2
            # Check that header is True for first call, False for second
            first_call = mock_to_csv.call_args_list[0]
            second_call = mock_to_csv.call_args_list[1]
            assert first_call.kwargs["header"] is True
            assert second_call.kwargs["header"] is False
            # Check file name and mode
            assert first_call.kwargs["mode"] == "a"
            assert second_call.kwargs["mode"] == "a"
            assert first_call.kwargs["encoding"] == "utf-8"
            assert second_call.kwargs["encoding"] == "utf-8"

    def test_calculate_indicators_single_process(self, mock_config):
        mock_conn = MagicMock()
        mock_db_util = MagicMock()
        mock_db_util.get_unique_tickers.return_value = ["AAPL", "GOOG"]
        mock_runner = MagicMock()

        config = mock_config.copy()
        config["calculate_indicators"]["calculate_processes"] = 1

        with patch("stockie.indicators.calculate_indicators.ConfigLoader") as mock_loader, \
             patch("stockie.indicators.calculate_indicators.psycopg2.connect", return_value=mock_conn), \
             patch("stockie.indicators.calculate_indicators.DatabaseUtilities", return_value=mock_db_util), \
             patch("stockie.indicators.calculate_indicators.CalculateIndicators", return_value=mock_runner):

            mock_loader.return_value.get.return_value = config

            from stockie.indicators.calculate_indicators import calculate_indicators
            calculate_indicators("/tmp/")
            mock_runner.run.assert_called_once_with(["AAPL", "GOOG"])
            mock_conn.close.assert_called_once()

    def test_calculate_indicators_multi_process(self, mock_config):
        mock_conn = MagicMock()
        mock_db_util = MagicMock()
        mock_db_util.get_unique_tickers.return_value = ["AAPL", "GOOG"]
        mock_process = MagicMock()

        config = mock_config.copy()
        config["calculate_indicators"]["calculate_processes"] = 2
        config["tickers"] = {"benchmarks": ["SPY"]}

        with patch("stockie.indicators.calculate_indicators.ConfigLoader") as mock_loader, \
             patch("stockie.indicators.calculate_indicators.psycopg2.connect", return_value=mock_conn), \
             patch("stockie.indicators.calculate_indicators.DatabaseUtilities", return_value=mock_db_util), \
             patch("stockie.indicators.calculate_indicators.multiprocessing.Process", return_value=mock_process):

            mock_loader.return_value.get.return_value = config

            from stockie.indicators.calculate_indicators import calculate_indicators
            calculate_indicators("/tmp/")
            assert mock_process.start.call_count == 2
            assert mock_process.join.call_count == 2
            mock_conn.close.assert_called_once()

    def test_calculate_indicators_db_connection_failure(self, mock_config):
        config = mock_config.copy()
        config["calculate_indicators"]["calculate_processes"] = 1

        with patch("stockie.indicators.calculate_indicators.ConfigLoader") as mock_loader, \
             patch("stockie.indicators.calculate_indicators.psycopg2.connect", side_effect=Exception("DB fail")):
            mock_loader.return_value.get.return_value = config

            from stockie.indicators.calculate_indicators import calculate_indicators
            with pytest.raises(Exception, match="DB fail"):
                calculate_indicators("/tmp/")

    def test_calculate_indicators_no_tickers(self, mock_config):
        mock_conn = MagicMock()
        mock_db_util = MagicMock()
        mock_db_util.get_unique_tickers.return_value = []
        mock_runner = MagicMock()

        config = mock_config.copy()
        config["calculate_indicators"]["calculate_processes"] = 1

        with patch("stockie.indicators.calculate_indicators.ConfigLoader") as mock_loader, \
             patch("stockie.indicators.calculate_indicators.psycopg2.connect", return_value=mock_conn), \
             patch("stockie.indicators.calculate_indicators.DatabaseUtilities", return_value=mock_db_util), \
             patch("stockie.indicators.calculate_indicators.CalculateIndicators", return_value=mock_runner):

            mock_loader.return_value.get.return_value = config

            from stockie.indicators.calculate_indicators import calculate_indicators
            calculate_indicators("/tmp/")
            mock_runner.run.assert_called_once_with([])
            mock_conn.close.assert_called_once()

    def test_export_profile_to_csv(self, tmp_path):
        # Create a mock stats object with .stats attribute
        class MockStats:
            def __init__(self):
                # keys are tuples: (filename, line_no, func_name)
                # values are tuples: (cc, nc, tt, ct, callers)
                self.stats = {
                    ("file1.py", 10, "funcA"): (1, 2, 0.1, 0.2, {}),
                    ("file2.py", 20, "funcB"): (3, 4, 0.3, 0.4, {}),
                }

        filename = tmp_path / "profile.csv"
        from stockie.indicators.calculate_indicators import export_profile_to_csv

        stats = MockStats()
        export_profile_to_csv(stats, filename=str(filename))

        # Check file contents
        with open(filename, newline="") as f:
            reader = list(csv.reader(f))
        assert reader[0] == ["Function", "Calls", "Total Time", "Cumulative Time"]
        assert reader[1] == ["file1.py:10(funcA)", "2", "0.1", "0.2"]
        assert reader[2] == ["file2.py:20(funcB)", "4", "0.3", "0.4"]

    def test_worker_function(self, mock_config):
        mock_conn = MagicMock()
        mock_db_util = MagicMock()
        mock_runner = MagicMock()

        config = mock_config.copy()
        config["db"] = {"dbname": "testdb", "user": "user", "password": "pw", "host": "localhost"}

        tickers_chunk = ["AAPL", "GOOG"]
        part = 0

        with patch("stockie.indicators.calculate_indicators.psycopg2.connect", return_value=mock_conn), \
             patch("stockie.indicators.calculate_indicators.DatabaseUtilities", return_value=mock_db_util), \
             patch("stockie.indicators.calculate_indicators.CalculateIndicators", return_value=mock_runner):

            from stockie.indicators.calculate_indicators import worker
            worker(tickers_chunk, config, part)
            mock_runner.run.assert_called_once_with(tickers_chunk, part)
            mock_conn.close.assert_called_once()
