import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from stockie.loaders.stock_price_ingestor import StockPriceIngestor

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
    def ingestor(self, mock_conn, mock_db_config):
        with patch("psycopg2.connect", return_value=mock_conn), \
             patch("stockie.loaders.stock_price_ingestor.DatabaseUtilities") as mock_util_class, \
             patch("stockie.loaders.stock_price_ingestor.AuditWriter"), \
             patch("stockie.loaders.stock_price_ingestor.CustomLogger"):

            mock_util = MagicMock()
            mock_util.table_exists.return_value = True
            mock_util_class.return_value = mock_util

            return StockPriceIngestor(db_config=mock_db_config, start_date="2020-01-01")

    def test_init_sets_attributes(self, ingestor):
        assert hasattr(ingestor, "start_date")
        assert hasattr(ingestor, "conn")
        assert hasattr(ingestor, "cur")

    def test_fetch_db_prices(self, ingestor):
        ingestor.cur.fetchall.return_value = [
            ("2023-01-01", 100, 110, 90, 105, 104.5, 1000000)
        ]
        df = ingestor._fetch_db_prices("AAPL", "2023-01-01")
        assert df.shape == (1, 7)
        assert list(df.columns) == [
            "Date", "open_db", "high_db", "low_db",
            "close_db", "adj_close_db", "volume_db"
        ]
        ingestor.cur.execute.assert_called_once()

    def test_insert_and_delete_rows(self, ingestor):
        sample_rows = [("AAPL", "2023-01-01", 100, 110, 90, 105, 104.5, 1000000)]
        ingestor._insert_rows(sample_rows)
        ingestor._delete_rows("AAPL", ["2023-01-01"])
        assert ingestor.cur.execute.call_count == 2
        assert ingestor.conn.commit.call_count == 2

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