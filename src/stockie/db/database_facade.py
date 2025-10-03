from psycopg2 import sql
from psycopg2.extras import execute_values
from collections.abc import Iterable
import pandas as pd
from datetime import date
from typing import List, Callable, Any, Union
import psycopg2

class DatabaseFacade:
    def __init__(self, conn: psycopg2.extensions.connection) -> None:
        self.conn = conn
        self.cur = conn.cursor()
        self.conn.autocommit = True

    #############################################################
    ###                Common database methods                ###
    #############################################################

    def table_exists(self, table_names: Union[str, List[str]]) -> bool:
        if isinstance(table_names, str):
            table_names = [table_names]
        elif not isinstance(table_names, Iterable):
            raise TypeError("Expected a string or an iterable of strings for table_names")

        if not all(isinstance(name, str) for name in table_names):
            raise ValueError("All table names must be strings")

        placeholders = ','.join(['%s'] * len(table_names))
        self.cur.execute(f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name IN ({placeholders})
        """, table_names)

        existing = {row[0] for row in self.cur.fetchall()}
        return all(name in existing for name in table_names)

    def truncate_table(self, table_name: str) -> None:
        """
        Truncates the specified table.
        """
        if not isinstance(table_name, str):
            raise TypeError("Table name must be a string.")
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql.SQL("TRUNCATE TABLE {}").format(sql.Identifier(table_name)))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"Failed to truncate table '{table_name}': {e}")

    def with_transaction(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function within a transaction with automatic rollback on error.
        
        This method temporarily disables autocommit, executes the function within
        a transaction, and automatically commits on success or rolls back on error.
        
        Args:
            func: Function to execute within the transaction
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The return value of the executed function
            
        Raises:
            Exception: Re-raises any exception from the function after rollback
        """

        original_autocommit = self.conn.autocommit
        self.conn.autocommit = False
        
        try:
            result = func(*args, **kwargs)
            self.conn.commit()
            return result
        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            self.conn.autocommit = original_autocommit

    #############################################################
    ### Methods for interacting with stock_price_audit table  ###
    #############################################################

    def write_audit_message(self, ticker: str, message: str) -> None:
                self.cur.execute("""
            INSERT INTO stock_price_audit (ticker, date, message)
            VALUES (%s, CURRENT_DATE, %s)
        """, (ticker, message))

    #############################################################
    ###    Methods for interacting with stock_prices table    ###
    #############################################################

    def get_unique_tickers(self) -> List[str]:
        """
        Returns a list of unique tickers from the stock_prices table.
        """
        with self.conn.cursor() as cur:
            cur.execute("SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker;")
            results = cur.fetchall()
            return [row[0] for row in results]

    def fetch_price_data(self, ticker: str) -> pd.DataFrame:
        """
        Returns a DataFrame with date and close price for the given ticker.
        """
        query = """
            SELECT date, close, low, high, volume
            FROM stock_prices
            WHERE ticker = %s
            ORDER BY date;
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (ticker,))
            rows = cur.fetchall()

        columns = ["date", "close", "low", "high", "volume"]
        if not rows:
            df = pd.DataFrame(columns=columns).set_index("date")
        else:
            df = pd.DataFrame(rows, columns=columns).set_index("date")
            df.index = pd.to_datetime(df.index)
            
            # Convert decimal columns to float for calculations
            numeric_columns = ["close", "low", "high", "volume"]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
        df.name = ticker

        return df

    def fetch_price_after_start_date(self, ticker: str, start_date: date) -> pd.DataFrame:
        self.cur.execute("""
            SELECT date, open, high, low, close, adj_close, volume
            FROM stock_prices
            WHERE ticker = %s AND date >= %s
        """, (ticker, start_date))
        return pd.DataFrame(self.cur.fetchall(), columns=[
            'Date', 'open_db', 'high_db', 'low_db',
            'close_db', 'adj_close_db', 'volume_db'
        ])

    def get_price_dates(self, ticker: str) -> set:
        self.cur.execute("SELECT date FROM stock_prices WHERE ticker = %s", (ticker,))
        return {row[0] for row in self.cur.fetchall()}

    def delete_price_by_dates(self, ticker: str, dates: List[date]) -> None:
        self.cur.execute("""
            DELETE FROM stock_prices
            WHERE ticker = %s AND date = ANY(%s)
        """, (ticker, list(dates)))
        self.conn.commit()

    def insert_price_data(self, data: List[tuple]) -> None:
        execute_values(self.cur, """
            INSERT INTO stock_prices (ticker, date, open, high, low, close, volume) 
            VALUES %s
            ON CONFLICT (ticker, date) DO NOTHING
        """, data)
        self.conn.commit()

    ###############################################################
    ### Methods for interacting with technical_indicators table ###
    ###############################################################

    def insert_indicator_series(self, series: pd.Series, ticker: str, indicator: str) -> None:
        """
        Inserts a time series into the technical_indicators table.

        Parameters:
            series (pd.Series): Indexed by date, containing indicator values.
            ticker (str): The stock symbol, e.g. 'AAPL'.
            indicator (str): The indicator name, e.g. 'sma_20'.
        """
        if not isinstance(series, pd.Series):
            raise TypeError("Expected a pandas Series with datetime index and float values.")

        data = [
            (ticker, date.date(), indicator, float(value))
            for date, value in series.dropna().items()
        ]

        if not data:
            return  # nothing to insert

        query = """
            INSERT INTO technical_indicators (ticker, date, indicator, value)
            VALUES %s
            ON CONFLICT (ticker, date, indicator) DO UPDATE
            SET value = EXCLUDED.value;
        """

        with self.conn.cursor() as cur:
            execute_values(cur, query, data)
            self.conn.commit()
    
    def copy_from_file(self, file_path: str) -> None:
        """
        Loads a CSV file into the technical_indicators table using PostgreSQL COPY.
        """
        try:
            with self.conn.cursor() as cur:
                with open(file_path, 'r') as f:
                    cur.copy_expert(
                        """
                        COPY technical_indicators(ticker, indicator, date, value)
                        FROM STDIN WITH (
                            FORMAT csv,
                            HEADER true,
                            QUOTE '"'
                        )
                        """,
                        f
                    )
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"Failed to load {file_path}: {e}")
