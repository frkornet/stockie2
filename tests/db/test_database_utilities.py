import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from stockie.db.database_utilities import DatabaseUtilities


class TestDatabaseUtilities:

    @pytest.fixture
    def mock_conn(self):
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = MagicMock()
        return mock_conn

    def test_single_existing_table(self, mock_conn):
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = [("stock_prices",)]

        db_util = DatabaseUtilities(mock_conn)
        result = db_util.table_exists("stock_prices")

        mock_cursor.execute.assert_called_once()
        assert result is True

    def test_single_missing_table(self, mock_conn):
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = []

        db_util = DatabaseUtilities(mock_conn)
        result = db_util.table_exists("ghost_table")

        assert result is False

    def test_multiple_tables_all_exist(self, mock_conn):
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = [("stock_prices",), ("stock_price_audit",)]

        db_util = DatabaseUtilities(mock_conn)
        result = db_util.table_exists(["stock_prices", "stock_price_audit"])

        assert result is True

    def test_multiple_tables_some_missing(self, mock_conn):
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = [("stock_prices",)]  # only one found

        db_util = DatabaseUtilities(mock_conn)
        result = db_util.table_exists(["stock_prices", "stock_price_audit"])

        assert result is False

    def test_raises_type_error_on_non_iterable(self, mock_conn):
        db_util = DatabaseUtilities(mock_conn)
        with pytest.raises(TypeError):
            db_util.table_exists(42)

    def test_raises_value_error_on_non_string_in_list(self, mock_conn):
        db_util = DatabaseUtilities(mock_conn)
        with pytest.raises(ValueError):
            db_util.table_exists(["stock_prices", 123])

    def test_get_unique_tickers(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [('AAPL',), ('MSFT',), ('NVDA',)]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_util = DatabaseUtilities(mock_conn)
        tickers = db_util.get_unique_tickers()

        mock_cursor.execute.assert_called_once_with("SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker;")
        assert tickers == ["AAPL", "MSFT", "NVDA"]

    def test_get_unique_tickers_empty(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_util = DatabaseUtilities(mock_conn)
        tickers = db_util.get_unique_tickers()

        mock_cursor.execute.assert_called_once_with("SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker;")
        assert tickers == []

    def test_insert_indicator_series(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        series = pd.Series(
            [0.1, 0.2, 0.3],
            index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
            name="sma_3"
        )

        db_util = DatabaseUtilities(mock_conn)

        # ✅ Patch the method inside the class, isolate psycopg2 entirely
        with patch("stockie.db.database_utilities.execute_values") as mock_ev:
            db_util.insert_indicator_series(series, "AAPL", "sma_3")

            assert mock_ev.called
            mock_conn.commit.assert_called_once()

    def test_insert_indicator_series_type_error(self, mock_conn):
        db_util = DatabaseUtilities(mock_conn)
        bad_input = [0.1, 0.2, 0.3]  # Not a Series

        with pytest.raises(TypeError, match="Expected a pandas Series"):
            db_util.insert_indicator_series(bad_input, "AAPL", "sma_3")

    def test_insert_indicator_series_empty_data(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Series with only NaN values → insert logic should skip
        empty_series = pd.Series(
            [float("nan"), float("nan")],
            index=pd.to_datetime(["2023-01-01", "2023-01-02"]),
            name="sma_3"
        )

        db_util = DatabaseUtilities(mock_conn)

        with patch("stockie.db.database_utilities.execute_values") as mock_ev:
            db_util.insert_indicator_series(empty_series, "AAPL", "sma_3")

            mock_ev.assert_not_called()
            mock_conn.commit.assert_not_called()

    def test_fetch_price_data_returns_frame(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("2023-01-01", 150.0),
            ("2023-01-02", 151.5),
            ("2023-01-03", 149.7)
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_util = DatabaseUtilities(mock_conn)
        df = db_util.fetch_price_data("AAPL")

        mock_cursor.execute.assert_called_once_with("""
            SELECT date, close
            FROM stock_prices
            WHERE ticker = %s
            ORDER BY date;
        """, ("AAPL",))

        expected_index = pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"])
        expected_values = [150.0, 151.5, 149.7]

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["close"]
        assert df.index.equals(expected_index)
        assert df["close"].tolist() == expected_values
        assert df.name == "AAPL"

    def test_fetch_price_data_empty_result(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_util = DatabaseUtilities(mock_conn)
        df = db_util.fetch_price_data("ZZZZ")

        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert list(df.columns) == ["close"]
        assert df.index.name == "date"

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))