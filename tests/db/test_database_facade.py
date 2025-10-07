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

    @patch('time.time')
    def test_vacuum_full_table_success(self, mock_time, mock_conn):
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
        from psycopg2 import sql
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
        expected_result = {
            'success': True,
            'duration_seconds': 3.5,
            'duration_minutes': 0.1,
            'error_message': None,
            'table_name': 'technical_indicators'
        }
        assert result == expected_result

    @patch('time.time')
    def test_vacuum_full_table_failure(self, mock_time, mock_conn):
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
        from psycopg2 import sql
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
    def test_vacuum_full_table_long_duration(self, mock_time, mock_conn):
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

    def test_bulk_insert_indicators_jsonb(self, mock_conn):
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

    def test_bulk_insert_indicators_jsonb_type_error(self, mock_conn):
        db_util = DatabaseFacade(mock_conn)
        bad_input = [{'ticker': 'AAPL', 'indicator': 'sma_20'}]  # Not a DataFrame

        with pytest.raises(TypeError, match="Expected a pandas DataFrame"):
            db_util.bulk_insert_indicators_jsonb(bad_input)

    def test_bulk_insert_indicators_jsonb_missing_columns(self, mock_conn):
        db_util = DatabaseFacade(mock_conn)
        
        # DataFrame missing required columns
        bad_df = pd.DataFrame({
            'ticker': ['AAPL'],
            'indicator': ['sma_20']
            # Missing 'date_values' column
        })

        with pytest.raises(ValueError, match="DataFrame must contain columns"):
            db_util.bulk_insert_indicators_jsonb(bad_df)

    def test_bulk_insert_indicators_jsonb_empty_data(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Empty DataFrame
        empty_df = pd.DataFrame(columns=['ticker', 'indicator', 'date_values'])

        db_util = DatabaseFacade(mock_conn)

        with patch("stockie.db.database_facade.execute_values") as mock_ev:
            db_util.bulk_insert_indicators_jsonb(empty_df)

            mock_ev.assert_not_called()
            mock_conn.commit.assert_not_called()

    def test_bulk_insert_indicators_jsonb_database_error(self, mock_conn):
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