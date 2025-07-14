import pytest
from unittest.mock import MagicMock
from stockie.db.database_utilities import DatabaseUtilities

class TestDatabaseUtilities:

    # @pytest.fixture
    # def mock_conn():
    #     mock_cursor = MagicMock()
    #     mock_conn = MagicMock()
    #     mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    #     return mock_conn, mock_cursor

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

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))