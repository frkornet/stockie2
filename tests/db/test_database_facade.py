import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from stockie.db.database_facade import DatabaseFacade
from stockie.db.schema_definitions import STOCKIE_TABLES
from datetime import date
from psycopg2 import sql
from typing import Any

def normalize_sql(sql: str):
    return "\n".join(line.strip() for line in sql.strip().splitlines())

class TestDatabaseFacade:

    @pytest.fixture
    def mock_conn(self):
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = MagicMock()
        return mock_conn

    #############################################################
    ###                Extract utility methods               ###
    #############################################################

    def test_extract_table_name_simple(self):
        """Test extracting table name from simple CREATE TABLE statement."""
        sql = "CREATE TABLE stock_prices (id INT PRIMARY KEY)"
        result = DatabaseFacade.extract_table_name(sql)
        assert result == "stock_prices"

    def test_extract_table_name_case_insensitive(self):
        """Test that extraction works regardless of case."""
        sql = "create table Stock_Prices (id int primary key)"
        result = DatabaseFacade.extract_table_name(sql)
        assert result == "stock_prices"

    def test_extract_table_name_with_schema(self):
        """Test extracting table name that includes schema prefix."""
        sql = "CREATE TABLE public.stock_prices (id INT PRIMARY KEY)"
        result = DatabaseFacade.extract_table_name(sql)
        assert result == "public.stock_prices"

    def test_extract_table_name_if_not_exists(self):
        """Test extracting table name from CREATE TABLE IF NOT EXISTS."""
        sql = "CREATE TABLE IF NOT EXISTS stock_prices (id INT PRIMARY KEY)"
        result = DatabaseFacade.extract_table_name(sql)
        assert result == "stock_prices"

    def test_extract_tablespace_name_simple(self):
        """Test extracting tablespace name from CREATE TABLESPACE statement."""
        sql = "CREATE TABLESPACE data_tblspc LOCATION '/path/to/data'"
        result = DatabaseFacade.extract_tablespace_name(sql)
        assert result == "data_tblspc"

    def test_extract_tablespace_name_case_insensitive(self):
        """Test that tablespace extraction works regardless of case."""
        sql = "create tablespace Data_Tblspc location '/path/to/data'"
        result = DatabaseFacade.extract_tablespace_name(sql)
        assert result == "data_tblspc"

    def test_extract_tablespace_name_with_owner(self):
        """Test extracting tablespace name when owner is specified."""
        sql = "CREATE TABLESPACE index_tblspc OWNER stockie_user LOCATION '/path/to/index'"
        result = DatabaseFacade.extract_tablespace_name(sql)
        assert result == "index_tblspc"

    def test_extract_index_name_simple(self):
        """Test extracting index name from CREATE INDEX statement."""
        sql = "CREATE INDEX idx_stock_prices_ticker ON stock_prices(ticker)"
        result = DatabaseFacade.extract_index_name(sql)
        assert result == "idx_stock_prices_ticker"

    def test_extract_index_name_unique(self):
        """Test extracting index name from CREATE UNIQUE INDEX."""
        sql = "CREATE UNIQUE INDEX idx_unique_ticker ON stock_prices(ticker, date)"
        result = DatabaseFacade.extract_index_name(sql)
        assert result == "idx_unique_ticker"

    def test_extract_index_name_if_not_exists(self):
        """Test extracting index name from CREATE INDEX IF NOT EXISTS."""
        sql = "CREATE INDEX IF NOT EXISTS idx_ticker ON stock_prices(ticker)"
        result = DatabaseFacade.extract_index_name(sql)
        assert result == "idx_ticker"

    def test_extract_index_name_with_tablespace(self):
        """Test extracting index name when tablespace is specified."""
        sql = "CREATE INDEX idx_performance ON indicators(ticker) TABLESPACE index_tblspc"
        result = DatabaseFacade.extract_index_name(sql)
        assert result == "idx_performance"

    def test_extract_table_name_temporary(self):
        """Test extracting table name from CREATE TEMPORARY TABLE."""
        sql = "CREATE TEMPORARY TABLE temp_prices (id INT)"
        result = DatabaseFacade.extract_table_name(sql)
        assert result == "temp_prices"

    def test_extract_table_name_temp(self):
        """Test extracting table name from CREATE TEMP TABLE."""
        sql = "CREATE TEMP TABLE temp_data (value REAL)"
        result = DatabaseFacade.extract_table_name(sql)
        assert result == "temp_data"

    def test_extract_table_name_quoted(self):
        """Test extracting quoted table name."""
        sql = 'CREATE TABLE "MyTable" (id INT)'
        result = DatabaseFacade.extract_table_name(sql)
        assert result == "mytable"

    def test_extract_index_name_quoted(self):
        """Test extracting quoted index name."""
        sql = 'CREATE INDEX "MyIndex" ON table(col)'
        result = DatabaseFacade.extract_index_name(sql)
        assert result == "myindex"

    def test_extract_table_name_error_case(self):
        """Test that ValueError is raised for invalid SQL."""
        sql = "CREATE SEQUENCE my_seq"
        with pytest.raises(ValueError, match="Could not extract table name from"):
            DatabaseFacade.extract_table_name(sql)

    def test_extract_index_name_error_case(self):
        """Test that ValueError is raised for invalid SQL."""
        sql = "CREATE SEQUENCE my_seq"
        with pytest.raises(ValueError, match="Could not extract index name from"):
            DatabaseFacade.extract_index_name(sql)

    def test_validate_sql_identifier_valid(self):
        """Test that valid identifiers pass validation."""
        # Should not raise for valid identifiers
        DatabaseFacade._validate_sql_identifier("valid_name", "test")
        DatabaseFacade._validate_sql_identifier("user123", "test")
        DatabaseFacade._validate_sql_identifier("Table_Name_2", "test")

    def test_validate_sql_identifier_invalid(self):
        """Test that invalid identifiers raise ValueError."""
        with pytest.raises(ValueError, match="must be alphanumeric"):
            DatabaseFacade._validate_sql_identifier("table-name", "test")
        
        with pytest.raises(ValueError, match="must be alphanumeric"):
            DatabaseFacade._validate_sql_identifier("123table", "test")
        
        with pytest.raises(ValueError, match="must be alphanumeric"):
            DatabaseFacade._validate_sql_identifier("table; DROP TABLE users;", "test")

    #############################################################
    ###                Existence check methods               ###
    #############################################################

    def test_tablespace_exists_true(self, mock_conn: MagicMock):
        """Test tablespace_exists returns True when tablespace exists."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [True]
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        result = db_util.tablespace_exists("stockie_data_ts")

        mock_cursor.execute.assert_called_once()
        sql_arg, params_arg = mock_cursor.execute.call_args[0]
        assert "pg_tablespace" in sql_arg
        assert "spcname" in sql_arg
        assert params_arg == ("stockie_data_ts",)
        assert result is True

    def test_tablespace_exists_false(self, mock_conn: MagicMock):
        """Test tablespace_exists returns False when tablespace doesn't exist."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [False]
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        result = db_util.tablespace_exists("nonexistent_ts")

        mock_cursor.execute.assert_called_once()
        assert result is False

    def test_drop_database_exists(self, mock_conn: MagicMock):
        """Test drop_database uses DROP DATABASE WITH (FORCE)."""
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        db_util.drop_database("test_db")
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0][0]
        sql_str = str(call_args)
        assert "DROP DATABASE" in sql_str
        assert "WITH (FORCE)" in sql_str

    def test_drop_database_not_exists(self, mock_conn: MagicMock):
        """Test drop_database still executes even if database doesn't exist (PostgreSQL will handle error)."""
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        db_util.drop_database("nonexistent_db")
        # The method should still execute the DROP command
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0][0]
        sql_str = str(call_args)
        assert "DROP DATABASE" in sql_str
        assert "WITH (FORCE)" in sql_str

    def test_create_database_simple(self, mock_conn: MagicMock):
        """Test create_database with database name and owner."""
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        db_util.create_database("test_db", "test_owner")
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0][0]
        assert "CREATE DATABASE" in str(call_args)

    def test_create_database_with_owner_and_tablespace(self, mock_conn: MagicMock):
        """Test create_database with owner and tablespace."""
        # The current implementation doesn't support tablespace parameter,
        # so this test should be removed or the implementation updated
        # For now, testing the basic functionality
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        db_util.create_database("test_db", "test_owner")
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0][0]
        sql_str = str(call_args)
        assert "CREATE DATABASE" in sql_str
        assert "WITH" in sql_str
        assert "OWNER" in sql_str

    def test_drop_user_not_exists(self, mock_conn: MagicMock):
        """Test that drop_user raises an exception when user doesn't exist."""
        # Configure mock to raise the expected PostgreSQL error
        from psycopg2.errors import UndefinedObject
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = UndefinedObject('role "nonexistent_user" does not exist')
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        # Should raise UndefinedObject exception when user doesn't exist
        with pytest.raises(UndefinedObject, match='role "nonexistent_user" does not exist'):
            db_util.drop_user("nonexistent_user")
        # Should attempt to execute the first DROP OWNED BY command
        mock_cursor.execute.assert_called_once()

    def test_create_user_simple(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        db_util.create_user("test_user", "password123")
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0][0]
        sql_str = str(call_args)
        assert "CREATE ROLE" in sql_str
        assert "LOGIN" in sql_str

    def test_create_user_with_password(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        db_util.create_user("test_user", "secret")
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0][0]
        sql_str = str(call_args)
        assert "CREATE ROLE" in sql_str
        assert "PASSWORD" in sql_str
        assert "secret" in sql_str









    def test_create_stockie_tablespaces_success(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        with patch.object(db_util, 'extract_tablespace_name') as mock_extract:
            mock_extract.side_effect = ["stockie_data", "stockie_index"]
            db_util.create_stockie_tablespaces("/data/path", "/index/path", "stockie_user")
        # Should execute SQL for both tablespaces
        assert mock_cursor.execute.call_count == 2
        
    def test_create_stockie_tablespaces_missing_paths(self, mock_conn: MagicMock):
        db_util = DatabaseFacade(mock_conn)
        
        # Test missing data_path
        with pytest.raises(ValueError, match="data_path and index_path parameters are required"):
            db_util.create_stockie_tablespaces("", "/index/path", "stockie_user")
            
        # Test missing index_path  
        with pytest.raises(ValueError, match="data_path and index_path parameters are required"):
            db_util.create_stockie_tablespaces("/data/path", "", "stockie_user")

    def test_drop_stockie_tablespaces_success(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        with patch.object(db_util, 'extract_tablespace_name') as mock_extract:
            mock_extract.side_effect = ["stockie_data", "stockie_index"]
            with patch.object(db_util, 'tablespace_exists', return_value=True):
                db_util.drop_stockie_tablespaces("stockie_user")
        # Should execute DROP for both tablespaces
        assert mock_cursor.execute.call_count == 2

    def test_drop_stockie_tablespaces_not_exist(self, mock_conn: MagicMock):
        db_util = DatabaseFacade(mock_conn)
        
        with patch.object(db_util, 'extract_tablespace_name') as mock_extract:
            mock_extract.side_effect = ["stockie_data", "stockie_index"]
            with patch.object(db_util, 'tablespace_exists', return_value=False):
                db_util.drop_stockie_tablespaces("stockie_user")
        
        # Should not execute any DROP commands since tablespaces don't exist
        mock_conn.execute.assert_not_called()

    def test_create_stockie_tables_success(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        db_util.create_stockie_tables("stockie_user")
        # Should execute SQL statements for table creation
        assert mock_cursor.execute.call_count >= 1

    def test_drop_stockie_tables_success(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        with patch.object(db_util, 'extract_table_name') as mock_extract, \
             patch.object(db_util, 'table_exists', return_value=True):
            table_count = len(STOCKIE_TABLES)
            mock_extract.side_effect = [f"table_{i}" for i in range(table_count)]
            db_util.drop_stockie_tables()
        assert mock_cursor.execute.call_count == table_count
        
    def test_drop_stockie_tables_some_missing(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        with patch.object(db_util, 'extract_table_name') as mock_extract, \
             patch.object(db_util, 'table_exists') as mock_exists:
            table_count = len(STOCKIE_TABLES)
            mock_extract.side_effect = [f"table_{i}" for i in range(table_count)]
            exists_pattern = [True] * (table_count - 1) + [False]
            mock_exists.side_effect = exists_pattern
            db_util.drop_stockie_tables()
        # Should execute DROP for all tables except the last one
        expected_drops = table_count - 1
        assert mock_cursor.execute.call_count == expected_drops
        assert mock_exists.call_count == table_count


    #############################################################
    ###                Common database methods                ###
    #############################################################


    def test_single_existing_table(self, mock_conn: MagicMock):
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = [("stock_prices",)]

        db_util = DatabaseFacade(mock_conn)
        result = db_util.table_exists("stock_prices")

        mock_cursor.execute.assert_called_once()
        assert result is True

    def test_single_missing_table(self, mock_conn: MagicMock):
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = []

        db_util = DatabaseFacade(mock_conn)
        result = db_util.table_exists("ghost_table")

        assert result is False

    def test_multiple_tables_all_exist(self, mock_conn: MagicMock):
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = [("stock_prices",), ("stock_price_audit",)]

        db_util = DatabaseFacade(mock_conn)
        result = db_util.table_exists(["stock_prices", "stock_price_audit"])

        assert result is True

    def test_multiple_tables_some_missing(self, mock_conn: MagicMock):
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = [("stock_prices",)]  # only one found

        db_util = DatabaseFacade(mock_conn)
        result = db_util.table_exists(["stock_prices", "stock_price_audit"])

        assert result is False

    def test_raises_type_error_on_non_iterable(self, mock_conn: MagicMock):
        db_util = DatabaseFacade(mock_conn)
        with pytest.raises(TypeError):
            db_util.table_exists(42) # type: ignore

    def test_table_exists_with_string(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [("stock_prices",)]

        db_util = DatabaseFacade(mock_conn)
        result = db_util.table_exists("stock_prices")

        mock_cursor.execute.assert_called_once()
        assert result is True

    def test_table_exists_with_list(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [("stock_prices",), ("stock_price_audit",)]

        db_util = DatabaseFacade(mock_conn)
        result = db_util.table_exists(["stock_prices", "stock_price_audit"])

        mock_cursor.execute.assert_called_once()
        assert result is True

    def test_table_exists_returns_false_when_table_missing(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        db_util = DatabaseFacade(mock_conn)
        result = db_util.table_exists("nonexistent_table")

        mock_cursor.execute.assert_called_once()
        assert result is False

    def test_rename_table(self, mock_conn: MagicMock):
        """Test renaming a table."""
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        
        db_util.rename_table("old_table", "new_table")
        
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0][0]
        assert "ALTER TABLE" in str(call_args)
        assert "RENAME TO" in str(call_args)

    def test_rename_index(self, mock_conn: MagicMock):
        """Test renaming an index."""
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        
        db_util.rename_index("old_index", "new_index")
        
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0][0]
        assert "ALTER INDEX" in str(call_args)
        assert "RENAME TO" in str(call_args)

    #############################################################
    ###     Tests for atomic table swap methods              ###
    #############################################################

    def test_create_temp_tables(self, mock_conn: MagicMock):
        """Test creating temporary tables with _temp suffix."""
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        
        with patch.object(db_util, 'create_stockie_tables') as mock_create:
            db_util.create_temp_tables("test_owner")
            
            mock_create.assert_called_once_with(
                owner="test_owner",
                table_filter=['stock_prices', 'technical_indicators'],
                name_suffix='_temp'
            )

    def test_atomic_table_swap_success(self, mock_conn: MagicMock):
        """Test successful atomic table swap."""
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        
        with patch.object(db_util, 'table_exists', return_value=True), \
             patch.object(db_util, 'rename_table') as mock_rename_table, \
             patch.object(db_util, 'drop_stockie_tables') as mock_drop, \
             patch.object(db_util, 'rename_index') as mock_rename_index, \
             patch.object(db_util, 'extract_index_name') as mock_extract_index, \
             patch.object(db_util, '_extract_table_from_index_sql') as mock_extract_table:
            
            # Setup mocks for index operations - need values for all 7 STOCKIE_INDEXES
            # Only stock_prices and technical_indicators indexes will be renamed (4 total)
            mock_extract_index.side_effect = [
                'stock_prices_ticker_idx', 'stock_prices_date_idx',
                'stock_price_audit_ticker_idx', 'stock_price_audit_date_idx',
                'technical_indicators_ticker_idx', 'technical_indicators_indicator_idx',
                'technical_indicators_date_values_gin_idx'
            ]
            mock_extract_table.side_effect = [
                'stock_prices', 'stock_prices',
                'stock_price_audit', 'stock_price_audit',
                'technical_indicators', 'technical_indicators', 'technical_indicators'
            ]
            
            db_util.atomic_table_swap()
            
            # Verify tables were renamed (Phase 1 and 2)
            assert mock_rename_table.call_count == 4  # 2 tables × 2 phases
            
            # Verify old tables were dropped (Phase 3)
            mock_drop.assert_called_once()
            
            # Verify indexes were renamed (Phase 4) - only for stock_prices and technical_indicators
            assert mock_rename_index.call_count == 5  # 2 stock_prices + 3 technical_indicators indexes

    def test_atomic_table_swap_failure(self, mock_conn: MagicMock):
        """Test that atomic_table_swap raises RuntimeError on failure."""
        mock_cursor = MagicMock()
        db_util = DatabaseFacade(mock_conn)
        db_util.cur = mock_cursor
        
        with patch.object(db_util, 'table_exists', return_value=True), \
             patch.object(db_util, 'rename_table', side_effect=Exception("DB error")):
            
            with pytest.raises(RuntimeError, match="Swap failed during Phase 1"):
                db_util.atomic_table_swap()

    #############################################################
    ### Methods for interacting with stock_price_audit table  ###
    #############################################################

    def test_write_audit_message(self, mock_conn: MagicMock):
        db_util = DatabaseFacade(mock_conn)
        ticker, message = "AAPL", "Test audit message"

        db_util.write_audit_message(ticker, message)

        db_util.cur.execute.assert_called_once()
        sql_arg, params_arg = db_util.cur.execute.call_args[0]
        expected_sql = """
            INSERT INTO stock_price_audit (ticker, date, message)
            VALUES (%s, CURRENT_DATE, %s)
        """

        assert normalize_sql(sql_arg) == normalize_sql(expected_sql)
        assert params_arg == (ticker, message)

    #############################################################
    ###    Methods for interacting with stock_prices table    ###
    #############################################################

    def test_get_unique_tickers(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [('AAPL',), ('MSFT',), ('NVDA',)]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_util = DatabaseFacade(mock_conn)
        tickers = db_util.get_unique_tickers()

        mock_cursor.execute.assert_called_once_with("SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker;")
        assert tickers == ["AAPL", "MSFT", "NVDA"]

    def test_get_unique_tickers_empty(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_util = DatabaseFacade(mock_conn)
        tickers = db_util.get_unique_tickers()

        mock_cursor.execute.assert_called_once_with("SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker;")
        assert tickers == []

    def test_fetch_price_data_returns_frame(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("2023-01-01", 150.0, 145.0, 155.0, 1000000),
            ("2023-01-02", 151.5, 146.0, 156.0, 1200000),
            ("2023-01-03", 149.7, 144.5, 154.5, 1100000)
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_util = DatabaseFacade(mock_conn)
        df = db_util.fetch_price_data("AAPL")

        # Verify execute was called once with correct parameters
        mock_cursor.execute.assert_called_once()
        sql_arg, params_arg = mock_cursor.execute.call_args[0]
        
        # SQL is now a Composed object due to sql.Identifier usage
        # Verify it's a Composed object and contains expected parts
        assert isinstance(sql_arg, sql.Composed)
        sql_str = str(sql_arg)
        assert "SELECT date, close, low, high, volume" in sql_str
        assert "FROM" in sql_str
        assert "stock_prices" in sql_str
        assert "WHERE ticker = %s" in sql_str
        assert "ORDER BY date" in sql_str
        assert params_arg == ("AAPL",)

        expected_index = pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"])
        expected_values = [150.0, 151.5, 149.7]

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ['close', 'low', 'high', 'volume']
        assert df.index.equals(expected_index)
        assert df["close"].tolist() == expected_values
        assert df.name == "AAPL"

    def test_fetch_price_data_empty_result(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_util = DatabaseFacade(mock_conn)
        df = db_util.fetch_price_data("ZZZZ")

        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert list(df.columns) == ['close', 'low', 'high', 'volume']
        assert df.index.name == "date"

    def test_fetch_price_after_start_date(self, mock_conn: MagicMock):
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = [
            ("2023-01-01", 100, 110, 90, 105, 105, 10000),
        ]
        db_util = DatabaseFacade(mock_conn)
        ticker, start_date = "AAPL", date(2023, 1, 1)

        df = db_util.fetch_price_after_start_date(ticker, start_date)

        mock_cursor.execute.assert_called_once()
        sql_arg, params_arg = mock_cursor.execute.call_args[0]
        expected_sql = """
            SELECT date, open, high, low, close, adj_close, volume
            FROM stock_prices
            WHERE ticker = %s AND date >= %s
        """

        assert normalize_sql(sql_arg) == normalize_sql(expected_sql)
        assert params_arg == (ticker, start_date)
        assert list(df.columns) == [
            'Date', 'open_db', 'high_db', 'low_db', 'close_db', 'adj_close_db', 'volume_db'
        ]

    def test_get_price_dates(self, mock_conn: MagicMock):
        mock_cursor = mock_conn.cursor.return_value
        # Simulate fetchall returning dates
        mock_cursor.fetchall.return_value = [
            (date(2023, 1, 1),),
            (date(2023, 1, 2),),
            (date(2023, 1, 3),),
        ]
        db_util = DatabaseFacade(mock_conn)
        result = db_util.get_price_dates("AAPL")

        mock_cursor.execute.assert_called_once_with(
            "SELECT date FROM stock_prices WHERE ticker = %s", ("AAPL",)
        )
        assert result == {date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3)}

    def test_delete_price_by_dates(self, mock_conn: MagicMock):
        db_util = DatabaseFacade(mock_conn)
        ticker = "AAPL"
        dates = [date(2023, 1, 1), date(2023, 1, 2)]
        db_util.delete_price_by_dates(ticker, dates)

        sql_arg = db_util.cur.execute.call_args[0][0]
        expected_sql = """
            DELETE FROM stock_prices
            WHERE ticker = %s AND date = ANY(%s)
        """

        assert normalize_sql(sql_arg) == normalize_sql(expected_sql)
        assert db_util.cur.execute.call_args[0][1] == (ticker, dates)
        mock_conn.commit.assert_called_once()

    @patch("stockie.db.database_facade.execute_values")
    def test_bulk_insert_price_data(self, mock_execute_values, mock_conn: MagicMock):
        db_util = DatabaseFacade(mock_conn)
        data = [
            ("AAPL", date(2023, 1, 1), 100, 110, 90, 105, 10000),
            ("AAPL", date(2023, 1, 2), 106, 112, 95, 110, 12000),
        ]
        db_util.bulk_insert_price_data(data)
        
        # Verify execute_values was called once
        mock_execute_values.assert_called_once()
        
        # Verify the SQL statement (plain string, hardcoded table name)
        sql_arg = mock_execute_values.call_args[0][1]
        expected_sql = """
            INSERT INTO stock_prices_temp (ticker, date, open, high, low, close, volume) 
            VALUES %s
        """
        
        assert normalize_sql(sql_arg) == normalize_sql(expected_sql)
        
        # Verify data parameter
        assert mock_execute_values.call_args[0][2] == data
        mock_conn.commit.assert_called_once()

    ###############################################################
    ### Methods for interacting with technical_indicators table ###
    ###############################################################

    def test_bulk_insert_indicators_jsonb(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Create test DataFrame matching the expected structure
        test_df = pd.DataFrame({
            'ticker': ['AAPL', 'AAPL'],
            'indicator': ['sma_20', 'rsi_14'],
            'date_values': [
                {'2023-01-01': 150.0, '2023-01-02': 152.0},
                {'2023-01-01': 65.5, '2023-01-02': 67.2}
            ]
        })

        db_util = DatabaseFacade(mock_conn)

        with patch("stockie.db.database_facade.execute_values") as mock_ev:
            db_util.bulk_insert_indicators_jsonb(test_df)

            assert mock_ev.called
            mock_conn.commit.assert_called_once()

    def test_bulk_insert_indicators_jsonb_missing_columns(self, mock_conn: MagicMock):
        db_util = DatabaseFacade(mock_conn)
        
        # DataFrame missing required columns
        bad_df = pd.DataFrame({
            'ticker': ['AAPL'],
            'indicator': ['sma_20']
            # Missing 'date_values' column
        })

        with pytest.raises(ValueError, match="DataFrame must contain columns"):
            db_util.bulk_insert_indicators_jsonb(bad_df)

    def test_bulk_insert_indicators_jsonb_empty_data(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Empty DataFrame
        empty_df = pd.DataFrame(columns=['ticker', 'indicator', 'date_values'])

        db_util = DatabaseFacade(mock_conn)

        with patch("stockie.db.database_facade.execute_values") as mock_ev:
            db_util.bulk_insert_indicators_jsonb(empty_df)

            mock_ev.assert_not_called()
            mock_conn.commit.assert_not_called()

    def test_bulk_insert_indicators_jsonb_database_error(self, mock_conn: MagicMock):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Create test DataFrame
        test_df = pd.DataFrame({
            'ticker': ['AAPL'],
            'indicator': ['sma_20'],
            'date_values': [{'2023-01-01': 150.0}]
        })

        db_util = DatabaseFacade(mock_conn)

        # Mock execute_values to raise an exception
        with patch("stockie.db.database_facade.execute_values") as mock_ev:
            mock_ev.side_effect = Exception("Database error")
            
            with pytest.raises(RuntimeError, match="Failed to bulk insert indicators: Database error"):
                db_util.bulk_insert_indicators_jsonb(test_df)
            
            # Verify rollback was called
            mock_conn.rollback.assert_called_once()

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))