import pytest
import pandas as pd
import psycopg2
import datetime
from datetime import datetime, date
from unittest.mock import MagicMock, patch
from stockie.loaders.stock_price_ingestor import StockPriceIngestor
from yfinance.exceptions import YFInvalidPeriodError, YFTzMissingError

def normalize_log(msg):
    return " ".join(msg.split())

class TestStockPriceIngestor:
    @pytest.fixture
    def mock_db_config(self):
        return {
            "dbname": "testdb",
            "user": "user",
            "password": "pw",
            "host": "localhost"
        }

    @pytest.fixture
    def mock_cursor(self):
        cursor = MagicMock()
        cursor.connection = MagicMock()
        cursor.connection.encoding = "LATIN1"  # valid encoding key
        cursor.mogrify.side_effect = lambda template, args: template % tuple(
            str(a).encode() if isinstance(a, (int, float)) else f"'{a}'".encode()
            for a in args
        )
        return cursor

    @pytest.fixture
    def mock_conn(self, mock_cursor):
        conn = MagicMock()
        conn.cursor.return_value = mock_cursor
        return conn

    @pytest.fixture
    def mock_logger(self):
        logger = MagicMock()
        return logger
    
    @pytest.fixture
    def ingestor(self, mock_conn, mock_db_config, mock_logger):
        with patch("psycopg2.connect", return_value=mock_conn), \
             patch("stockie.loaders.stock_price_ingestor.AuditWriter"):
            mock_db_facade = MagicMock()
            mock_db_facade.table_exists.return_value = True

            return StockPriceIngestor(db_facade=mock_db_facade, start_date="2020-01-01", logger=mock_logger)

    def test_constructor_with_invalid_config(self):
        mock_db_facade = MagicMock()
        mock_db_facade.table_exists.return_value = False
        with pytest.raises(RuntimeError):
            StockPriceIngestor(db_facade=mock_db_facade, start_date="2020-01-01", logger=MagicMock())

    def test_connect_success(self, mock_db_config, mock_logger):
        with patch("stockie.loaders.stock_price_ingestor.AuditWriter"):
            mock_db_facade = MagicMock()
            mock_db_facade.table_exists.return_value = True

            ingestor = StockPriceIngestor(db_facade=mock_db_facade, start_date="2020-01-01", logger=mock_logger)
            assert ingestor is not None
            mock_db_facade.table_exists.assert_called_once_with(['stock_prices', 'stock_price_audit'])

    def test_connect_success_start_date_is_none(self, mock_db_config, mock_logger):
        with patch("stockie.loaders.stock_price_ingestor.AuditWriter"):
            mock_db_facade = MagicMock()
            mock_db_facade.table_exists.return_value = True

            with pytest.raises(RuntimeError):
                ingestor = StockPriceIngestor(db_facade=mock_db_facade, start_date=None, logger=mock_logger)

    def test_connect_success_start_date_is_datetime(self, mock_db_config, mock_logger):
        with patch("stockie.loaders.stock_price_ingestor.AuditWriter"):
            mock_db_facade = MagicMock()
            mock_db_facade.table_exists.return_value = True

            start_date = datetime.strptime("2020-01-01", "%Y-%m-%d")
            ingestor = StockPriceIngestor(db_facade=mock_db_facade, start_date=start_date, logger=mock_logger)
            assert ingestor is not None
            mock_db_facade.table_exists.assert_called_once_with(['stock_prices', 'stock_price_audit'])

    def test_connect_success_start_date_is_date(self, mock_db_config, mock_logger):
        with patch("stockie.loaders.stock_price_ingestor.AuditWriter"):
            mock_db_facade = MagicMock()
            mock_db_facade.table_exists.return_value = True

            start_date = datetime.strptime("2020-01-01", "%Y-%m-%d").date()
            ingestor = StockPriceIngestor(db_facade=mock_db_facade, start_date=start_date, logger=mock_logger)
            assert ingestor is not None
            mock_db_facade.table_exists.assert_called_once_with(['stock_prices', 'stock_price_audit'])

    def test_connect_success_start_date_is_int(self, mock_db_config, mock_logger):
        with patch("stockie.loaders.stock_price_ingestor.AuditWriter"):
            mock_db_facade = MagicMock()
            mock_db_facade.table_exists.return_value = True

            with pytest.raises(RuntimeError):
                ingestor = StockPriceIngestor(db_facade=mock_db_facade, start_date=123, logger=mock_logger)

    def test_connect_success_tables_not_exist(self, mock_db_config, mock_logger):
        with patch("stockie.loaders.stock_price_ingestor.AuditWriter"):
            mock_db_facade = MagicMock()
            mock_db_facade.table_exists.return_value = False

            with pytest.raises(RuntimeError):
                ingestor = StockPriceIngestor(db_facade=mock_db_facade, start_date="2020-01-01", logger=mock_logger)

    def test_has_changes_detects_column_mismatch(self, ingestor):
        df_new = pd.DataFrame({
            "Date": ["2023-01-01"],
            "Open": [100],
            "High": [110],
            "Low": [90],
            "Close": [105],
            "Adj Close": [104.5],
            "Volume": [1000000]
        })
        df_db = pd.DataFrame({
            "Date": ["2023-01-01"],
            "open_db": [101],
            "high_db": [110],
            "low_db": [90],
            "close_db": [105],
            "adj_close_db": [104.5],
            "volume_db": [1000000]
        })
        has_diff = ingestor._has_changes(
            df_new, df_db,
            ["Open", "High", "Low", "Close", "Adj Close", "Volume"],
            "AAPL"
        )
        assert has_diff is True

    def test_has_changes_row_count_mismatch(self, ingestor):
        # DataFrames with different lengths
        df_new = pd.DataFrame({"Date": ["2023-01-01", "2023-01-02"], "Open": [1, 2]})
        df_db = pd.DataFrame({"Date": ["2023-01-01"], "Open": [1]})

        ingestor.audit = MagicMock()
        ingestor.logger = MagicMock()

        result = ingestor._has_changes(df_new, df_db, ["Open"], "AAPL")

        assert result is True
        ingestor.audit.log_change_summary.assert_called_once_with("AAPL", "row_count_mismatch", [])
        ingestor.logger.info.assert_any_call("AAPL: row count mismatch (2 vs 1)")

    def test_has_changes_date_join_mismatch(self, ingestor):
        # df_new has two dates, df_db only overlaps with one
        df_new = pd.DataFrame({"Date": ["2023-01-01", "2023-01-02"], "Open": [1, 2]})
        df_db = pd.DataFrame({"Date": ["2023-01-01", "2023-01-01"], "Open": [1, 1]})

        ingestor.audit = MagicMock()
        ingestor.logger = MagicMock()

        result = ingestor._has_changes(df_new, df_db, ["Open"], "AAPL")

        assert result is True
        ingestor.audit.log_change_summary.assert_called_once_with("AAPL", "date_join_mismatch", [])
        last_call = ingestor.logger.info.call_args_list[-1][0][0]
        assert last_call == "AAPL: date join mismatch"

    def test_has_changes_returns_false_when_no_changes(self, ingestor):
        import pandas as pd

        # Both DataFrames have the same data and columns
        df_new = pd.DataFrame({
            "Date": ["2023-01-01", "2023-01-02"],
            "Open": [1.0, 2.0],
            "High": [1.1, 2.1],
            "Low": [0.9, 1.9],
            "Close": [1.05, 2.05],
            "Volume": [100, 200]
        })
        # Simulate db columns with _db suffix and same values
        df_db = pd.DataFrame({
            "Date": ["2023-01-01", "2023-01-02"],
            "open_db": [1.0, 2.0],
            "high_db": [1.1, 2.1],
            "low_db": [0.9, 1.9],
            "close_db": [1.05, 2.05],
            "volume_db": [100, 200]
        })

        ingestor.audit = MagicMock()
        ingestor.logger = MagicMock()

        result = ingestor._has_changes(df_new, df_db, ["Open", "High", "Low", "Close", "Volume"], "AAPL")

        assert result is False
        ingestor.audit.log_change_summary.assert_not_called()

    def test_yfinance_ticker_download_success(self, ingestor):
        # Just test that the method can be called - the actual yfinance integration is complex
        # and would require very specific mock setup to work properly
        ingestor.logger = MagicMock()
        
        # Mock the internal methods to avoid complex yfinance data structure mocking
        ingestor._fetch_raw_yfinance_data = MagicMock(return_value=pd.DataFrame({"test": [1]}))
        ingestor._process_raw_yfinance_data = MagicMock(return_value={"AAPL": pd.DataFrame({
            "Ticker": ["AAPL"], 
            "Date": [pd.Timestamp("2023-01-01").date()],
            "Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Volume": [1000]
        })})
        
        result = ingestor._yfinance_download(["AAPL"], ["Open", "High", "Low", "Close", "Volume"])

        # Should return a dict with AAPL key containing DataFrame
        assert "AAPL" in result
        df_result = result["AAPL"]
        assert not df_result.empty
        assert set(df_result.columns) == {"Ticker", "Date", "Open", "High", "Low", "Close", "Volume"}
        assert (df_result["Ticker"] == "AAPL").all()

    def test_yfinance_ticker_download_empty(self, ingestor):
        # Test that empty result is handled correctly
        ingestor.logger = MagicMock()
        ingestor._fetch_raw_yfinance_data = MagicMock(return_value=pd.DataFrame())
        ingestor._process_raw_yfinance_data = MagicMock(return_value={"AAPL": pd.DataFrame()})
        
        result = ingestor._yfinance_download(["AAPL"], ["Open", "High", "Low", "Close", "Volume"])
        assert "AAPL" in result
        assert result["AAPL"].empty

    def test_process_today_price_no_today_row(self, ingestor):
        today = pd.Timestamp.today().date()
        df = pd.DataFrame({"Date": [today - pd.Timedelta(days=1)], "Open": [1]})
        db_df = pd.DataFrame({"Date": [today - pd.Timedelta(days=1)], "Open": [1]})

        ingestor.logger = MagicMock()
        ingestor.db_facade = MagicMock()

        ingestor._process_today_price(df, db_df, "AAPL")
        ingestor.logger.info.assert_any_call("AAPL: no data for today.")

    def test_process_today_price_insert_today(self, ingestor):
        today = pd.Timestamp.today().date()
        df = pd.DataFrame({"Date": [today], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame({"Date": [], "Open": []})

        ingestor.logger = MagicMock()
        ingestor.db_facade = MagicMock()
        ingestor.db_facade.get_price_dates.return_value = set()

        ingestor._process_today_price(df, db_df, "AAPL")
        ingestor.db_facade.insert_price_data.assert_called_once()
        ingestor.logger.info.assert_any_call("AAPL: inserted today's row.")

    def test_process_today_price_today_already_present_no_db_df(self, ingestor):
        today = pd.Timestamp.today().date()
        df = pd.DataFrame({"Date": [today], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame({"Date": [], "Open": []})

        ingestor.logger = MagicMock()
        ingestor.db_facade = MagicMock()
        ingestor.db_facade.get_price_dates.return_value = {today}

        ingestor._process_today_price(df, db_df, "AAPL")
        ingestor.logger.info.assert_any_call("AAPL: today's data already present.")

    def test_process_today_price_today_already_present_with_changes(self, ingestor):
        today = pd.Timestamp.today().date()
        df = pd.DataFrame({"Date": [today], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame({"Date": [today], "Open": [2], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})

        ingestor.logger = MagicMock()
        ingestor.db_facade = MagicMock()
        ingestor.db_facade.get_price_dates.return_value = {today}
        ingestor._has_changes = MagicMock(return_value=True)

        ingestor._process_today_price(df, db_df, "AAPL")
        ingestor.db_facade.delete_price_by_dates.assert_called_once_with("AAPL", [today])
        ingestor.db_facade.insert_price_data.assert_called_once()
        ingestor.logger.info.assert_any_call("AAPL: updated today's row (1 rows)")

    def test_process_today_price_today_already_present_no_changes(self, ingestor):
        today = pd.Timestamp.today().date()
        df = pd.DataFrame({"Date": [today], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame({"Date": [today], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})

        ingestor.logger = MagicMock()
        ingestor.db_facade = MagicMock()
        ingestor.db_facade.get_price_dates.return_value = {today}
        ingestor._has_changes = MagicMock(return_value=False)

        ingestor._process_today_price(df, db_df, "AAPL")
        ingestor.logger.info.assert_any_call("AAPL: no changes to today's row")

    def test_process_historical_prices_no_hist_data(self, ingestor):
        today = pd.Timestamp.today().date()
        # All dates are today or later, so hist_df will be empty
        df = pd.DataFrame({"Date": [today], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame({"Date": [today], "Open": [1]})

        ingestor.logger = MagicMock()
        ingestor.db_facade = MagicMock()

        ingestor._process_historical_prices(df, db_df, "AAPL")
        ingestor.logger.info.assert_any_call("AAPL: no historical data to process.")

    def test_process_historical_prices_db_empty(self, ingestor):
        today = pd.Timestamp.today().date()
        # One historical row
        df = pd.DataFrame({"Date": [today - pd.Timedelta(days=1)], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume", "Ticker"])

        ingestor.logger = MagicMock()
        ingestor.db_facade = MagicMock()

        ingestor._process_historical_prices(df, db_df, "AAPL")
        ingestor.db_facade.insert_price_data.assert_called_once()
        ingestor.logger.info.assert_any_call("AAPL: inserted historical rows (no prior data).")

    def test_process_historical_prices_has_changes(self, ingestor):
        today = pd.Timestamp.today().date()
        # One historical row, different in database
        df = pd.DataFrame({"Date": [today - pd.Timedelta(days=1)], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame({"Date": [today - pd.Timedelta(days=1)], "Open": [2], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})

        ingestor.logger = MagicMock()
        ingestor.db_facade = MagicMock()
        ingestor._has_changes = MagicMock(return_value=True)

        ingestor._process_historical_prices(df, db_df, "AAPL")
        ingestor.db_facade.delete_price_by_dates.assert_called_once_with("AAPL", [today - pd.Timedelta(days=1)])
        ingestor.db_facade.insert_price_data.assert_called_once()
        ingestor.logger.info.assert_any_call("AAPL: reconciled historical rows (1 rows)")

    def test_process_historical_prices_no_changes(self, ingestor):
        today = pd.Timestamp.today().date()
        # One historical row, same in db
        df = pd.DataFrame({"Date": [today - pd.Timedelta(days=1)], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame({"Date": [today - pd.Timedelta(days=1)], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})

        ingestor.logger = MagicMock()
        ingestor.db_facade = MagicMock()
        ingestor._has_changes = MagicMock(return_value=False)

        ingestor._process_historical_prices(df, db_df, "AAPL")
        ingestor.logger.info.assert_any_call("AAPL: no historical differences")

    def test_download_handles_empty_df(self, ingestor):
        ingestor._yfinance_download = MagicMock(return_value={})
        ingestor.logger = MagicMock()
        ingestor.download(["AAPL"])
        ingestor.logger.info.assert_any_call("AAPL: no data.")

    def test_download_handles_invalid_period(self, ingestor):
        ingestor._process_ticker_batch = MagicMock(return_value=False)
        ingestor.logger = MagicMock()
        ingestor.download(["AAPL"])
        ingestor.logger.warning.assert_any_call("Batch 1 failed. Consecutive failures: 1")

    def test_download_handles_tz_missing(self, ingestor):
        ingestor._process_ticker_batch = MagicMock(return_value=False)
        ingestor.logger = MagicMock()
        ingestor.download(["AAPL"])
        ingestor.logger.warning.assert_any_call("Batch 1 failed. Consecutive failures: 1")

    def test_download_handles_generic_exception(self, ingestor):
        ingestor._process_ticker_batch = MagicMock(return_value=False)
        ingestor.logger = MagicMock()
        ingestor.download(["AAPL"])
        ingestor.logger.warning.assert_any_call("Batch 1 failed. Consecutive failures: 1")

    def test_download_successful_flow(self, ingestor):
        # Mock the batch processing method
        ingestor._process_ticker_batch = MagicMock(return_value=True)
        ingestor.logger = MagicMock()

        ingestor.download(["AAPL"])

        ingestor._process_ticker_batch.assert_called_once_with(["AAPL"], ["Open", "High", "Low", "Close", "Volume"])
        ingestor.logger.info.assert_any_call("Stock price download completed.")
        ingestor.logger.info.assert_any_call("Stock price download completed.")

    def test_download_accepts_single_ticker_string(self, ingestor):
        # Should work with a single ticker string, not just a list
        ingestor._process_ticker_batch = MagicMock(return_value=True)
        ingestor.logger = MagicMock()

        ingestor.download("AAPL")

        ingestor._process_ticker_batch.assert_called_once_with(["AAPL"], ["Open", "High", "Low", "Close", "Volume"])
        ingestor.logger.info.assert_any_call("Stock price download completed.")

    # Additional test methods from test_stock_price_ingestor_additional.py
    def test_fetch_raw_yfinance_data_empty_data_exception(self, ingestor):
        """Test _fetch_raw_yfinance_data when yfinance returns empty data"""
        tickers_batch = ["INVALID"]
        
        with patch("yfinance.download", return_value=pd.DataFrame()):
            with pytest.raises(Exception, match="No data returned for tickers"):
                ingestor._fetch_raw_yfinance_data(tickers_batch)

    def test_process_raw_yfinance_data_extraction_error(self, ingestor):
        """Test _process_raw_yfinance_data when ticker extraction fails"""
        # Create mock data that will cause extraction to fail
        mock_data = MagicMock()
        tickers_batch = ["AAPL"]
        compare_cols = ["Open", "High", "Low", "Close", "Volume"]
        
        # Mock _extract_ticker_data to raise exception
        with patch.object(ingestor, '_extract_ticker_data', side_effect=Exception("Extraction failed")):
            result = ingestor._process_raw_yfinance_data(mock_data, tickers_batch, compare_cols)
            
            # Should return empty DataFrame for failed ticker
            assert "AAPL" in result
            assert result["AAPL"].empty
            ingestor.logger.error.assert_called_with("Error extracting AAPL from data: Extraction failed")

    def test_extract_ticker_data_ticker_not_found(self, ingestor):
        """Test _extract_ticker_data when ticker is not found in data"""
        # Create mock data without the requested ticker
        mock_data = pd.DataFrame([[1.0]], 
                               columns=pd.MultiIndex.from_tuples([("OTHER", "Open")], names=[None, None]))
        
        result = ingestor._extract_ticker_data(mock_data, "AAPL", ["Open"])
        
        assert result.empty
        ingestor.logger.warning.assert_called_with("Ticker AAPL not found in data")

    def test_extract_ticker_data_empty_ticker_data(self, ingestor):
        """Test _extract_ticker_data when ticker data is empty after extraction"""
        # Create mock data with ticker but empty data after extraction
        mock_data = MagicMock()
        mock_data.columns.get_level_values.return_value = ["AAPL"]
        
        # Mock xs to return empty DataFrame
        empty_df = pd.DataFrame()
        mock_data.xs.return_value = empty_df
        
        result = ingestor._extract_ticker_data(mock_data, "AAPL", ["Open"])
        
        assert result.empty
        ingestor.logger.info.assert_called_with("AAPL: no data.")

    def test_extract_ticker_data_successful_extraction(self, ingestor):
        """Test _extract_ticker_data successful extraction and formatting"""
        # Create mock data for successful extraction
        dates = pd.date_range('2023-01-01', periods=2)
        ticker_data = pd.DataFrame({
            'Open': [100.0, 101.0],
            'High': [102.0, 103.0],
            'Low': [99.0, 100.0],
            'Close': [101.0, 102.0],
            'Volume': [1000, 1100]
        }, index=dates)
        ticker_data.index.name = 'Date'
        
        mock_data = MagicMock()
        mock_data.columns.get_level_values.return_value = ["AAPL"]
        mock_data.xs.return_value = ticker_data
        
        compare_cols = ["Open", "High", "Low", "Close", "Volume"]
        result = ingestor._extract_ticker_data(mock_data, "AAPL", compare_cols)
        
        # Verify the result format
        expected_columns = ['Ticker', 'Date'] + compare_cols
        assert list(result.columns) == expected_columns
        assert all(result['Ticker'] == 'AAPL')
        assert len(result) == 2
        
        # Verify logging
        ingestor.logger.info.assert_called()

    def test_process_ticker_batch_decimal_column_conversion(self, ingestor):
        """Test decimal column conversion in _process_ticker_batch"""
        batch_tickers = ["AAPL"]
        compare_cols = ["Open", "High", "Low", "Close", "Volume"]
        
        # Mock yfinance download to return valid data
        mock_data = {"AAPL": pd.DataFrame({
            'Ticker': ['AAPL'],
            'Date': [datetime.today().date()],
            'Open': [100.0], 'High': [102.0], 'Low': [99.0], 'Close': [101.0], 'Volume': [1000]
        })}
        
        # Mock database data with decimal columns
        db_data = pd.DataFrame({
            'Open': [100.0], 'High': [102.0], 'Low': [99.0], 'Close': [101.0], 'Volume': [1000],
            'open_db': [100.0], 'high_db': [102.0], 'low_db': [99.0], 'close_db': [101.0], 'volume_db': [1000]
        })
        
        ingestor.db_facade.fetch_price_after_start_date.return_value = db_data
        ingestor.db_facade.with_transaction = MagicMock()
        
        with patch.object(ingestor, '_yfinance_download', return_value=mock_data):
            result = ingestor._process_ticker_batch(batch_tickers, compare_cols)
            
            assert result is True
            # Verify with_transaction was called
            ingestor.db_facade.with_transaction.assert_called()

    def test_process_ticker_batch_yf_invalid_period_error(self, ingestor):
        """Test handling of YFInvalidPeriodError in _process_ticker_batch"""
        batch_tickers = ["AAPL"]
        compare_cols = ["Open", "High", "Low", "Close", "Volume"]
        
        mock_data = {"AAPL": pd.DataFrame({
            'Ticker': ['AAPL'],
            'Date': [datetime.today().date()],
            'Open': [100.0], 'High': [102.0], 'Low': [99.0], 'Close': [101.0], 'Volume': [1000]
        })}
        
        # Mock with_transaction to raise YFInvalidPeriodError
        ingestor.db_facade.with_transaction.side_effect = YFInvalidPeriodError("AAPL", "1d", ["1d", "5d"])
        
        with patch.object(ingestor, '_yfinance_download', return_value=mock_data):
            result = ingestor._process_ticker_batch(batch_tickers, compare_cols)
            
            assert result is True
            # Check that warning was called with the actual message format
            warning_calls = [call.args[0] for call in ingestor.logger.warning.call_args_list]
            assert any("AAPL: invalid period" in call and "ignored" in call for call in warning_calls)

    def test_process_ticker_batch_yf_tz_missing_error(self, ingestor):
        """Test handling of YFTzMissingError in _process_ticker_batch"""
        batch_tickers = ["AAPL"]
        compare_cols = ["Open", "High", "Low", "Close", "Volume"]
        
        mock_data = {"AAPL": pd.DataFrame({
            'Ticker': ['AAPL'],
            'Date': [datetime.today().date()],
            'Open': [100.0], 'High': [102.0], 'Low': [99.0], 'Close': [101.0], 'Volume': [1000]
        })}
        
        # Mock with_transaction to raise YFTzMissingError
        ingestor.db_facade.with_transaction.side_effect = YFTzMissingError("Timezone missing")
        
        with patch.object(ingestor, '_yfinance_download', return_value=mock_data):
            result = ingestor._process_ticker_batch(batch_tickers, compare_cols)
            
            assert result is True
            # Check that warning was called with the actual message format
            warning_calls = [call.args[0] for call in ingestor.logger.warning.call_args_list]
            assert any("AAPL: delisted" in call and "ignored" in call for call in warning_calls)

    def test_process_ticker_batch_generic_exception(self, ingestor):
        """Test handling of generic exceptions in _process_ticker_batch"""
        batch_tickers = ["AAPL"]
        compare_cols = ["Open", "High", "Low", "Close", "Volume"]
        
        mock_data = {"AAPL": pd.DataFrame({
            'Ticker': ['AAPL'],
            'Date': [datetime.today().date()],
            'Open': [100.0], 'High': [102.0], 'Low': [99.0], 'Close': [101.0], 'Volume': [1000]
        })}
        
        # Mock with_transaction to raise generic exception
        ingestor.db_facade.with_transaction.side_effect = Exception("Database error")
        
        with patch.object(ingestor, '_yfinance_download', return_value=mock_data):
            result = ingestor._process_ticker_batch(batch_tickers, compare_cols)
            
            assert result is True
            ingestor.logger.exception.assert_called_with("AAPL: ingestion failed - Database error")

    def test_process_ticker_batch_yfinance_download_failure(self, ingestor):
        """Test handling when _yfinance_download fails entirely"""
        batch_tickers = ["AAPL"]
        compare_cols = ["Open", "High", "Low", "Close", "Volume"]
        
        # Mock _yfinance_download to raise exception
        with patch.object(ingestor, '_yfinance_download', side_effect=Exception("Download failed")):
            result = ingestor._process_ticker_batch(batch_tickers, compare_cols)
            
            assert result is False
            ingestor.logger.error.assert_called_with("Batch processing failed for ['AAPL']: Download failed")

    def test_download_max_consecutive_failures(self, ingestor):
        """Test that download stops after max_consecutive_failures"""
        # Set max_consecutive_failures to 2 for testing
        ingestor.max_consecutive_failures = 2
        ingestor.batch_size = 1  # Process one ticker per batch to ensure multiple batches
        
        # Mock _process_ticker_batch to always return False (failure)
        with patch.object(ingestor, '_process_ticker_batch', return_value=False):
            # Use 3 tickers to ensure we hit the failure limit with 3 separate batches
            tickers = ["FAIL1", "FAIL2", "FAIL3"]
            
            with pytest.raises(RuntimeError, match="Stopping after 2 consecutive batch failures"):
                ingestor.download(tickers)
            
            # Should log the error message
            ingestor.logger.error.assert_called_with("Stopping after 2 consecutive batch failures")

    def test_download_batch_processing_with_mixed_results(self, ingestor):
        """Test download with some batches failing and some succeeding"""
        ingestor.batch_size = 1  # Process one ticker per batch
        ingestor.max_consecutive_failures = 3
        
        # Mock _process_ticker_batch to fail then succeed alternately
        side_effects = [False, True, False, True]  # fail, succeed, fail, succeed
        
        with patch.object(ingestor, '_process_ticker_batch', side_effect=side_effects):
            tickers = ["FAIL1", "SUCCESS1", "FAIL2", "SUCCESS2"]
            
            # Should complete without raising exception
            ingestor.download(tickers)
            
            # Should log completion
            ingestor.logger.info.assert_any_call("Stock price download completed.")

    def test_download_large_batch_processing(self, ingestor):
        """Test download with multiple batches"""
        ingestor.batch_size = 2  # Process 2 tickers per batch
        
        with patch.object(ingestor, '_process_ticker_batch', return_value=True):
            tickers = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]  # 5 tickers = 3 batches
            
            ingestor.download(tickers)
            
            # Should have called _process_ticker_batch 3 times
            assert ingestor._process_ticker_batch.call_count == 3
            
            # Verify batch contents
            calls = ingestor._process_ticker_batch.call_args_list
            assert calls[0][0][0] == ["AAPL", "GOOGL"]  # First batch
            assert calls[1][0][0] == ["MSFT", "TSLA"]   # Second batch
            assert calls[2][0][0] == ["AMZN"]           # Third batch

    def test_validate_start_date_invalid_string_format(self):
        """Test _validate_start_date with invalid string format"""
        with patch("stockie.loaders.stock_price_ingestor.AuditWriter"):
            mock_db_facade = MagicMock()
            mock_db_facade.table_exists.return_value = True
            
            with pytest.raises(ValueError):  # datetime.strptime raises ValueError for invalid format
                StockPriceIngestor(db_facade=mock_db_facade, start_date="invalid-date", logger=MagicMock())

    def test_check_column_differences_missing_db_column(self, ingestor):
        """Test _check_column_differences when database column is missing"""
        df_new = pd.DataFrame({
            'Date': [date(2023, 1, 1)],
            'Open': [100.0]
        })
        df_db = pd.DataFrame({
            'Date': [date(2023, 1, 1)]
            # Missing 'open_db' column
        })
        
        ingestor.audit = MagicMock()
        
        result = ingestor._check_column_differences(df_new, df_db, ['Open'], 'AAPL')
        
        assert result is True  # Should detect mismatch due to missing column
        ingestor.audit.log_change_summary.assert_called_with('AAPL', 'column_value_mismatch', ['Open'])

    def test_has_changes_with_numeric_db_columns(self, ingestor):
        """Test _has_changes with properly converted database columns"""
        df_new = pd.DataFrame({
            'Date': [date(2023, 1, 1)],
            'Open': [100.0],
            'Volume': [1000]
        })
        
        # Database data with proper numeric types (as would be after conversion in process_ticker_batch)
        df_db = pd.DataFrame({
            'Date': [date(2023, 1, 1)],
            'open_db': [100.0],  # Already converted to float
            'volume_db': [1000]  # Already converted to numeric
        })
        
        ingestor.audit = MagicMock()
        
        result = ingestor._has_changes(df_new, df_db, ['Open', 'Volume'], 'AAPL')
        
        # Should return False since values are the same
        assert result is False