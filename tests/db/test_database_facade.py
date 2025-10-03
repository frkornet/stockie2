import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, call, mock_open
from stockie.db.database_facade import DatabaseFacade
from datetime import date

def normalize_sql(sql):
    return "\n".join(line.strip() for line in sql.strip().splitlines())

class TestDatabaseFacade:

    @pytest.fixture
    def mock_conn(self):
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = MagicMock()
        return mock_conn

    #############################################################
    ###                Common database methods                ###
    #############################################################


    def test_single_existing_table(self, mock_conn):
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = [("stock_prices",)]

        db_util = DatabaseFacade(mock_conn)
        result = db_util.table_exists("stock_prices")

        mock_cursor.execute.assert_called_once()
        assert result is True

    def test_single_missing_table(self, mock_conn):
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = []

        db_util = DatabaseFacade(mock_conn)
        result = db_util.table_exists("ghost_table")

        assert result is False

    def test_multiple_tables_all_exist(self, mock_conn):
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = [("stock_prices",), ("stock_price_audit",)]

        db_util = DatabaseFacade(mock_conn)
        result = db_util.table_exists(["stock_prices", "stock_price_audit"])

        assert result is True

    def test_multiple_tables_some_missing(self, mock_conn):
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = [("stock_prices",)]  # only one found

        db_util = DatabaseFacade(mock_conn)
        result = db_util.table_exists(["stock_prices", "stock_price_audit"])

        assert result is False

    def test_raises_type_error_on_non_iterable(self, mock_conn):
        db_util = DatabaseFacade(mock_conn)
        with pytest.raises(TypeError):
            db_util.table_exists(42)

    def test_raises_value_error_on_non_string_in_list(self, mock_conn):
        db_util = DatabaseFacade(mock_conn)
        with pytest.raises(ValueError):
            db_util.table_exists(["stock_prices", 123])

    def test_table_exists_with_string(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [("stock_prices",)]

        db_util = DatabaseFacade(mock_conn)
        result = db_util.table_exists("stock_prices")

        mock_cursor.execute.assert_called_once()
        assert result is True

    def test_table_exists_with_list(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [("stock_prices",), ("stock_price_audit",)]

        db_util = DatabaseFacade(mock_conn)
        result = db_util.table_exists(["stock_prices", "stock_price_audit"])

        mock_cursor.execute.assert_called_once()
        assert result is True

    def test_table_exists_returns_false_when_table_missing(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        db_util = DatabaseFacade(mock_conn)
        result = db_util.table_exists("nonexistent_table")

        mock_cursor.execute.assert_called_once()
        assert result is False

    def test_truncate_table_success(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_util = DatabaseFacade(mock_conn)
        db_util.truncate_table("my_table")

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_truncate_table_type_error(self, mock_conn):
        db_util = DatabaseFacade(mock_conn)
        with pytest.raises(TypeError):
            db_util.truncate_table(123)

    def test_truncate_table_raises_runtime_error_on_exception(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB error")

        db_util = DatabaseFacade(mock_conn)
        with pytest.raises(RuntimeError, match="Failed to truncate table 'my_table'"):
            db_util.truncate_table("my_table")
        mock_conn.rollback.assert_called_once()

    #############################################################
    ### Methods for interacting with stock_price_audit table  ###
    #############################################################

    def test_write_audit_message(self, mock_conn):
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

    def test_get_unique_tickers(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [('AAPL',), ('MSFT',), ('NVDA',)]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_util = DatabaseFacade(mock_conn)
        tickers = db_util.get_unique_tickers()

        mock_cursor.execute.assert_called_once_with("SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker;")
        assert tickers == ["AAPL", "MSFT", "NVDA"]

    def test_get_unique_tickers_empty(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_util = DatabaseFacade(mock_conn)
        tickers = db_util.get_unique_tickers()

        mock_cursor.execute.assert_called_once_with("SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker;")
        assert tickers == []

    def test_fetch_price_data_returns_frame(self, mock_conn):
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

    def test_fetch_price_data_empty_result(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_util = DatabaseFacade(mock_conn)
        df = db_util.fetch_price_data("ZZZZ")

        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert list(df.columns) == ['close', 'low', 'high', 'volume']
        assert df.index.name == "date"

    def test_fetch_price_after_start_date(self, mock_conn):
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

    def test_get_price_dates(self, mock_conn):
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

    def test_delete_price_by_dates(self, mock_conn):
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
    def test_insert_price_data(self, mock_execute_values, mock_conn):
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

    def test_insert_indicator_series(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        series = pd.Series(
            [0.1, 0.2, 0.3],
            index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
            name="sma_3"
        )

        db_util = DatabaseFacade(mock_conn)

        # Patch the method inside the class, isolate psycopg2 entirely
        with patch("stockie.db.database_facade.execute_values") as mock_ev:
            db_util.insert_indicator_series(series, "AAPL", "sma_3")

            assert mock_ev.called
            mock_conn.commit.assert_called_once()

    def test_insert_indicator_series_type_error(self, mock_conn):
        db_util = DatabaseFacade(mock_conn)
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

        db_util = DatabaseFacade(mock_conn)

        with patch("stockie.db.database_facade.execute_values") as mock_ev:
            db_util.insert_indicator_series(empty_series, "AAPL", "sma_3")

            mock_ev.assert_not_called()
            mock_conn.commit.assert_not_called()

    def test_copy_from_file_success(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
        db_util = DatabaseFacade(mock_conn)
        file_path = "/tmp/test.csv"
    
        # Mock the file operations
        mock_file_content = "ticker,indicator,date,value\nAAPL,RSI,2023-01-01,65.5\n"
    
        with patch("builtins.open", mock_open(read_data=mock_file_content)) as mock_file:
            db_util.copy_from_file(file_path)
        
            # Verify file was opened
            mock_file.assert_called_once_with(file_path, 'r')
        
            # Verify copy_expert was called correctly (changed from copy_from)
            mock_cursor.copy_expert.assert_called_once()
        
            # Check the SQL command and file object
            call_args = mock_cursor.copy_expert.call_args
            sql_command = call_args[0][0]
            file_obj = call_args[0][1]
        
            # Verify the SQL contains the expected COPY command
            assert "COPY technical_indicators" in sql_command
            assert "FORMAT csv" in sql_command
            assert "HEADER true" in sql_command
        
            # Verify commit was called
            mock_conn.commit.assert_called_once()

    def test_copy_from_file_error(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.copy_expert.side_effect = Exception("Database error")  # Changed from copy_from
    
        db_util = DatabaseFacade(mock_conn)
        file_path = "/tmp/test.csv"
    
        mock_file_content = "ticker,indicator,date,value\nAAPL,RSI,2023-01-01,65.5\n"
    
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            with pytest.raises(RuntimeError, match="Failed to load /tmp/test.csv"):
                db_util.copy_from_file(file_path)
            
            # Verify rollback was called
            mock_conn.rollback.assert_called_once()

    def test_copy_from_file_raises_runtime_error(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.copy_expert.side_effect = Exception("fail")  # Changed from execute to copy_expert

        db_util = DatabaseFacade(mock_conn)
        file_path = "/tmp/test.csv"
        
        mock_file_content = "ticker,indicator,date,value\nAAPL,RSI,2023-01-01,65.5\n"
        
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            with pytest.raises(RuntimeError, match="Failed to load /tmp/test.csv: fail"):
                db_util.copy_from_file(file_path)
            mock_conn.rollback.assert_called_once()

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))