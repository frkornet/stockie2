from psycopg2 import sql
from psycopg2.extras import execute_values
from collections.abc import Iterable
import pandas as pd

class DatabaseUtilities:
    def __init__(self, conn):
        self.conn = conn
        self.cur = conn.cursor()

    def table_exists(self, table_names):
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
    
    from typing import List

    def get_unique_tickers(self) -> List[str]:
        """
        Returns a list of unique tickers from the stock_prices table.
        """
        with self.conn.cursor() as cur:
            cur.execute("SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker;")
            results = cur.fetchall()
            return [row[0] for row in results]


    def insert_indicator_series(self, series: pd.Series, ticker: str, indicator: str):
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
        df.name = ticker

        return df