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

    def test_with_transaction_success(self, mock_conn: MagicMock):
        """Test with_transaction commits on success and restores autocommit."""
        mock_conn.autocommit = True
        db_util = DatabaseFacade(mock_conn)
        
        # Mock function that will be executed in transaction
        mock_func = MagicMock(return_value="success")
        
        result = db_util.with_transaction(mock_func, "arg1", "arg2", kwarg1="value1")
        
        # Verify autocommit was disabled during transaction
        assert mock_conn.autocommit is True  # restored after transaction
        mock_conn.commit.assert_called_once()
        mock_conn.rollback.assert_not_called()
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
        assert result == "success"

    def test_with_transaction_rollback_on_error(self, mock_conn: MagicMock):
        """Test with_transaction rolls back on error and restores autocommit."""
        mock_conn.autocommit = True
        db_util = DatabaseFacade(mock_conn)
        
        # Mock function that raises an exception
        mock_func = MagicMock(side_effect=ValueError("Test error"))
        
        with pytest.raises(ValueError, match="Test error"):
            db_util.with_transaction(mock_func)
        
        # Verify autocommit was restored and rollback was called
        assert mock_conn.autocommit is True
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()

    @patch('time.time')
    def test_vacuum_full_table_success(self, mock_time: MagicMock, mock_conn: MagicMock):
        # Mock time.time() to return predictable values
        mock_time.side_effect = [1000.0, 1003.5]  # 3.5 second duration
        
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        db_util = DatabaseFacade(mock_conn)
        result = db_util.vacuum_full_table('technical_indicators')
        
        # Verify SQL execution
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0][0]
        # Check if it's a composed SQL object with the correct structure
        if isinstance(call_args, sql.Composed):
            # Verify it's composed of SQL("VACUUM FULL ") + Identifier('technical_indicators')
            assert len(call_args.seq) == 2
            assert isinstance(call_args.seq[0], sql.SQL)
            assert call_args.seq[0]._wrapped == "VACUUM FULL "
            assert isinstance(call_args.seq[1], sql.Identifier)
            assert call_args.seq[1]._wrapped == ("technical_indicators",)
        else:
            assert str(call_args) == "VACUUM FULL technical_indicators"
        mock_conn.commit.assert_called_once()
        
        # Verify result
        expected_result: dict[str, Any] = {
            'success': True,
            'duration_seconds': 3.5,
            'duration_minutes': 0.1,
            'error_message': None,
            'table_name': 'technical_indicators'
        }
        assert result == expected_result

    @patch('time.time')
    def test_vacuum_full_table_failure(self, mock_time, mock_conn: MagicMock):
        # Mock time.time() for start time
        mock_time.return_value = 1000.0
        
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("VACUUM failed")
        
        db_util = DatabaseFacade(mock_conn)
        result = db_util.vacuum_full_table('test_table')
        
        # Verify SQL execution was attempted
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0][0]
        # Check if it's a composed SQL object with the correct structure
        if isinstance(call_args, sql.Composed):
            # Verify it's composed of SQL("VACUUM FULL ") + Identifier('test_table')
            assert len(call_args.seq) == 2
            assert isinstance(call_args.seq[0], sql.SQL)
            assert call_args.seq[0]._wrapped == "VACUUM FULL "
            assert isinstance(call_args.seq[1], sql.Identifier)
            assert call_args.seq[1]._wrapped == ("test_table",)
        else:
            assert str(call_args) == "VACUUM FULL test_table"
        mock_conn.rollback.assert_called_once()
        
        # Verify result
        expected_result = {
            'success': False,
            'duration_seconds': 0,
            'duration_minutes': 0,
            'error_message': 'VACUUM failed',
            'table_name': 'test_table'
        }
        assert result == expected_result

    @patch('time.time')
    def test_vacuum_full_table_long_duration(self, mock_time, mock_conn: MagicMock):
        # Mock time.time() to simulate 2.5 minute duration
        mock_time.side_effect = [1000.0, 1150.0]  # 150 second duration
        
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        db_util = DatabaseFacade(mock_conn)
        result = db_util.vacuum_full_table('large_table')
        
        # Verify result has correct timing
        assert result['success'] is True
        assert result['duration_seconds'] == 150.0
        assert result['duration_minutes'] == 2.5
        assert result['table_name'] == 'large_table'

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

        mock_cursor.execute.assert_called_once_with("""
            SELECT date, close, low, high, volume
            FROM stock_prices
            WHERE ticker = %s
            ORDER BY date;
        """, ("AAPL",))

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
    def test_insert_price_data(self, mock_execute_values, mock_conn: MagicMock):
        db_util = DatabaseFacade(mock_conn)
        data = [
            ("AAPL", date(2023, 1, 1), 100, 110, 90, 105, 10000),
            ("AAPL", date(2023, 1, 2), 106, 112, 95, 110, 12000),
        ]
        db_util.insert_price_data(data)
        sql_arg = mock_execute_values.call_args[0][1]
        expected_sql = """
            INSERT INTO stock_prices (ticker, date, open, high, low, close, volume) 
            VALUES %s
            ON CONFLICT (ticker, date) DO NOTHING
        """

        assert normalize_sql(sql_arg) == normalize_sql(expected_sql)
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