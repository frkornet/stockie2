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
             patch("stockie.loaders.stock_price_ingestor.DatabaseUtilities") as mock_util_class, \
             patch("stockie.loaders.stock_price_ingestor.AuditWriter"):

            mock_util = MagicMock()
            mock_util.table_exists.return_value = True
            mock_util_class.return_value = mock_util

            return StockPriceIngestor(db_config=mock_db_config, start_date="2020-01-01", logger=mock_logger)

    def test_constructor_with_invalid_config(self):
        with patch("psycopg2.connect") as mock_connect:
            mock_connect.side_effect = psycopg2.OperationalError("no password supplied")
            with pytest.raises(psycopg2.OperationalError):
                StockPriceIngestor(db_config={}, start_date="2020-01-01", logger=MagicMock())

    def test_connect_success(self, mock_db_config, mock_logger):
        with patch("psycopg2.connect") as mock_connect, \
            patch("stockie.loaders.stock_price_ingestor.DatabaseUtilities") as mock_util_class, \
            patch("stockie.loaders.stock_price_ingestor.AuditWriter"):
            mock_util = MagicMock()
            mock_util.table_exists.return_value = True
            mock_util_class.return_value = mock_util

            ingestor = StockPriceIngestor(db_config=mock_db_config, start_date="2020-01-01", logger=mock_logger)
            mock_connect.assert_called_once()

    def test_connect_success_start_date_is_none(self, mock_db_config, mock_logger):
        with patch("psycopg2.connect") as mock_connect, \
            patch("stockie.loaders.stock_price_ingestor.DatabaseUtilities") as mock_util_class, \
            patch("stockie.loaders.stock_price_ingestor.AuditWriter"):
            mock_util = MagicMock()
            mock_util.table_exists.return_value = True
            mock_util_class.return_value = mock_util

            with pytest.raises(RuntimeError):
                ingestor = StockPriceIngestor(db_config=mock_db_config, start_date=None, logger=mock_logger)
                mock_connect.assert_called_once()

    def test_connect_success_start_date_is_datetime(self, mock_db_config, mock_logger):
        with patch("psycopg2.connect") as mock_connect, \
            patch("stockie.loaders.stock_price_ingestor.DatabaseUtilities") as mock_util_class, \
            patch("stockie.loaders.stock_price_ingestor.AuditWriter"):
            mock_util = MagicMock()
            mock_util.table_exists.return_value = True
            mock_util_class.return_value = mock_util

            start_date = datetime.strptime("2020-01-01", "%Y-%m-%d")
            ingestor = StockPriceIngestor(db_config=mock_db_config, start_date=start_date, logger=mock_logger)
            mock_connect.assert_called_once()

    def test_connect_success_start_date_is_date(self, mock_db_config, mock_logger):
        with patch("psycopg2.connect") as mock_connect, \
            patch("stockie.loaders.stock_price_ingestor.DatabaseUtilities") as mock_util_class, \
            patch("stockie.loaders.stock_price_ingestor.AuditWriter"):
            mock_util = MagicMock()
            mock_util.table_exists.return_value = True
            mock_util_class.return_value = mock_util

            start_date = datetime.strptime("2020-01-01", "%Y-%m-%d").date()
            ingestor = StockPriceIngestor(db_config=mock_db_config, start_date=start_date, logger=mock_logger)
            mock_connect.assert_called_once()

    def test_connect_success_start_date_is_int(self, mock_db_config, mock_logger):
        with patch("psycopg2.connect") as mock_connect, \
            patch("stockie.loaders.stock_price_ingestor.DatabaseUtilities") as mock_util_class, \
            patch("stockie.loaders.stock_price_ingestor.AuditWriter"):
            mock_util = MagicMock()
            mock_util.table_exists.return_value = True
            mock_util_class.return_value = mock_util

            with pytest.raises(RuntimeError):
                ingestor = StockPriceIngestor(db_config=mock_db_config, start_date=123, logger=mock_logger)
                mock_connect.assert_called_once()

    def test_connect_success_tables_not_exist(self, mock_db_config, mock_logger):
        with patch("psycopg2.connect") as mock_connect, \
            patch("stockie.loaders.stock_price_ingestor.DatabaseUtilities") as mock_util_class, \
            patch("stockie.loaders.stock_price_ingestor.AuditWriter"):
            mock_util = MagicMock()
            mock_util.table_exists.return_value = False
            mock_util_class.return_value = mock_util

            with pytest.raises(RuntimeError):
                ingestor = StockPriceIngestor(db_config=mock_db_config, start_date="2020-01-01", logger=mock_logger)
                mock_connect.assert_called_once()

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
        # Mock yfinance.download to return a non-empty DataFrame with MultiIndex columns
        columns = pd.MultiIndex.from_tuples([('Open', ''), ('High', ''), ('Low', ''), ('Close', ''), ('Volume', '')])
        data = [[1.0, 2.0, 0.5, 1.5, 1000], [2.0, 3.0, 1.5, 2.5, 2000]]
        df = pd.DataFrame(data, columns=columns)
        df.index = pd.to_datetime(['2023-01-01', '2023-01-02'])
        df = df.reset_index().rename(columns={"index": "Date"}) 

        with patch("stockie.loaders.stock_price_ingestor.yf.download", return_value=df):
            ingestor.logger = MagicMock()
            result = ingestor._yfinance_ticker_download("AAPL", ["Open", "High", "Low", "Close", "Volume"])

        # Should return a DataFrame with the expected columns and not be empty
        assert not result.empty
        assert set(result.columns) == {"Ticker", "Date", "Open", "High", "Low", "Close", "Volume"}
        assert (result["Ticker"] == "AAPL").all()
        assert pd.api.types.is_datetime64_any_dtype(result["Date"]) or pd.api.types.is_object_dtype(result["Date"])

    def test_yfinance_ticker_download_empty(self, ingestor):
        # Mock yfinance.download to return an empty DataFrame
        df = pd.DataFrame()
        with patch("stockie.loaders.stock_price_ingestor.yf.download", return_value=df):
            ingestor.logger = MagicMock()
            result = ingestor._yfinance_ticker_download("AAPL", ["Open", "High", "Low", "Close", "Volume"])

        assert result.empty

    def test_process_today_price_no_today_row(self, ingestor):
        today = pd.Timestamp.today().date()
        df = pd.DataFrame({"Date": [today - pd.Timedelta(days=1)], "Open": [1]})
        db_df = pd.DataFrame({"Date": [today - pd.Timedelta(days=1)], "Open": [1]})

        ingestor.logger = MagicMock()
        ingestor.db_util = MagicMock()

        ingestor._process_today_price(df, db_df, "AAPL")
        ingestor.logger.info.assert_any_call("AAPL: no data for today.")

    def test_process_today_price_insert_today(self, ingestor):
        today = pd.Timestamp.today().date()
        df = pd.DataFrame({"Date": [today], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame({"Date": [], "Open": []})

        ingestor.logger = MagicMock()
        ingestor.db_util = MagicMock()
        ingestor.db_util.get_price_dates.return_value = set()

        ingestor._process_today_price(df, db_df, "AAPL")
        ingestor.db_util.insert_price_data.assert_called_once()
        ingestor.logger.info.assert_any_call("AAPL: inserted today's row.")

    def test_process_today_price_today_already_present_no_db_df(self, ingestor):
        today = pd.Timestamp.today().date()
        df = pd.DataFrame({"Date": [today], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame({"Date": [], "Open": []})

        ingestor.logger = MagicMock()
        ingestor.db_util = MagicMock()
        ingestor.db_util.get_price_dates.return_value = {today}

        ingestor._process_today_price(df, db_df, "AAPL")
        ingestor.logger.info.assert_any_call("AAPL: today's data already present.")

    def test_process_today_price_today_already_present_with_changes(self, ingestor):
        today = pd.Timestamp.today().date()
        df = pd.DataFrame({"Date": [today], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame({"Date": [today], "Open": [2], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})

        ingestor.logger = MagicMock()
        ingestor.db_util = MagicMock()
        ingestor.db_util.get_price_dates.return_value = {today}
        ingestor._has_changes = MagicMock(return_value=True)

        ingestor._process_today_price(df, db_df, "AAPL")
        ingestor.db_util.delete_price_by_dates.assert_called_once_with("AAPL", [today])
        ingestor.db_util.insert_price_data.assert_called_once()
        ingestor.logger.info.assert_any_call("AAPL: updated today's row.")

    def test_process_today_price_today_already_present_no_changes(self, ingestor):
        today = pd.Timestamp.today().date()
        df = pd.DataFrame({"Date": [today], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame({"Date": [today], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})

        ingestor.logger = MagicMock()
        ingestor.db_util = MagicMock()
        ingestor.db_util.get_price_dates.return_value = {today}
        ingestor._has_changes = MagicMock(return_value=False)

        ingestor._process_today_price(df, db_df, "AAPL")
        ingestor.logger.info.assert_any_call("AAPL: no changes to today's row.")

    def test_process_historical_prices_no_hist_data(self, ingestor):
        today = pd.Timestamp.today().date()
        # All dates are today or later, so hist_df will be empty
        df = pd.DataFrame({"Date": [today], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame({"Date": [today], "Open": [1]})

        ingestor.logger = MagicMock()
        ingestor.db_util = MagicMock()

        ingestor._process_historical_prices(df, db_df, "AAPL")
        ingestor.logger.info.assert_any_call("AAPL: no historical data to process.")

    def test_process_historical_prices_db_empty(self, ingestor):
        today = pd.Timestamp.today().date()
        # One historical row
        df = pd.DataFrame({"Date": [today - pd.Timedelta(days=1)], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume", "Ticker"])

        ingestor.logger = MagicMock()
        ingestor.db_util = MagicMock()

        ingestor._process_historical_prices(df, db_df, "AAPL")
        ingestor.db_util.insert_price_data.assert_called_once()
        ingestor.logger.info.assert_any_call("AAPL: inserted historical rows (no prior data).")

    def test_process_historical_prices_has_changes(self, ingestor):
        today = pd.Timestamp.today().date()
        # One historical row, different in database
        df = pd.DataFrame({"Date": [today - pd.Timedelta(days=1)], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame({"Date": [today - pd.Timedelta(days=1)], "Open": [2], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})

        ingestor.logger = MagicMock()
        ingestor.db_util = MagicMock()
        ingestor._has_changes = MagicMock(return_value=True)

        ingestor._process_historical_prices(df, db_df, "AAPL")
        ingestor.db_util.delete_price_by_dates.assert_called_once_with("AAPL", [today - pd.Timedelta(days=1)])
        ingestor.db_util.insert_price_data.assert_called_once()
        ingestor.logger.info.assert_any_call("AAPL: reconciled 1 historical rows.")

    def test_process_historical_prices_no_changes(self, ingestor):
        today = pd.Timestamp.today().date()
        # One historical row, same in db
        df = pd.DataFrame({"Date": [today - pd.Timedelta(days=1)], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})
        db_df = pd.DataFrame({"Date": [today - pd.Timedelta(days=1)], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100], "Ticker": ["AAPL"]})

        ingestor.logger = MagicMock()
        ingestor.db_util = MagicMock()
        ingestor._has_changes = MagicMock(return_value=False)

        ingestor._process_historical_prices(df, db_df, "AAPL")
        ingestor.logger.info.assert_any_call("AAPL: no historical differences.")

    def test_download_handles_empty_df(self, ingestor):
        ingestor._yfinance_ticker_download = MagicMock(return_value=pd.DataFrame())
        ingestor.logger = MagicMock()
        ingestor.download(["AAPL"])
        ingestor.logger.info.assert_any_call("AAPL: no data.")

    def test_download_handles_invalid_period(self, ingestor):
        exc = YFInvalidPeriodError("bad period", "1d", ["1mo", "3mo"])
        ingestor._yfinance_ticker_download = MagicMock(side_effect=exc)
        ingestor.logger = MagicMock()
        ingestor.download(["AAPL"])
        assert any(
            "AAPL: invalid period - bad period" in normalize_log(str(call[0][0]))
            for call in ingestor.logger.warning.call_args_list
        )

    def test_download_handles_tz_missing(self, ingestor):
        ingestor._yfinance_ticker_download = MagicMock(side_effect=YFTzMissingError("AAPL"))
        ingestor.logger = MagicMock()
        ingestor.download(["AAPL"])
        assert any(
            "AAPL: delisted - $AAPL: possibly delisted; no timezone found" in normalize_log(str(call[0][0]))
            for call in ingestor.logger.warning.call_args_list
        )

    def test_download_handles_generic_exception(self, ingestor):
        ingestor._yfinance_ticker_download = MagicMock(side_effect=Exception("fail"))
        ingestor.logger = MagicMock()
        ingestor.download(["AAPL"])
        assert any("AAPL: ingestion failed - fail" in str(call[0][0]) for call in ingestor.logger.exception.call_args_list)

    def test_download_successful_flow(self, ingestor):
        # Simulate a non-empty DataFrame from yfinance
        today = pd.Timestamp.today().date()
        df = pd.DataFrame({
            "Ticker": ["AAPL", "AAPL"],
            "Date": [today, today - pd.Timedelta(days=1)],
            "Open": [1, 2],
            "High": [2, 3],
            "Low": [0, 1],
            "Close": [1.5, 2.5],
            "Volume": [100, 200]
        })
        ingestor._yfinance_ticker_download = MagicMock(return_value=df)
        ingestor.db_util.fetch_price_after_start_date = MagicMock(return_value=df)
        ingestor._process_today_price = MagicMock()
        ingestor._process_historical_prices = MagicMock()
        ingestor.logger = MagicMock()

        ingestor.download(["AAPL"])

        ingestor._process_today_price.assert_called_once()
        ingestor._process_historical_prices.assert_called_once()
        ingestor.logger.info.assert_any_call("Stock price download completed.")

    def test_download_accepts_single_ticker_string(self, ingestor):
        # Should work with a single ticker string, not just a list
        df = pd.DataFrame({"Ticker": ["AAPL"], "Date": [pd.Timestamp.today().date()], "Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100]})
        ingestor._yfinance_ticker_download = MagicMock(return_value=df)
        ingestor.db_util.fetch_price_after_start_date = MagicMock(return_value=df)
        ingestor._process_today_price = MagicMock()
        ingestor._process_historical_prices = MagicMock()
        ingestor.logger = MagicMock()

        ingestor.download("AAPL")

        ingestor._process_today_price.assert_called_once()
        ingestor._process_historical_prices.assert_called_once()