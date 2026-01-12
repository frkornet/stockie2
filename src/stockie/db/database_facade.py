from psycopg2 import sql
from psycopg2.extras import execute_values, Json # type: ignore
import pandas as pd
from datetime import date
from typing import Any, List, Callable, Tuple, Union, Optional, TypeVar, ParamSpec
import psycopg2
import re
from stockie.db.schema_definitions import STOCKIE_TABLES, STOCKIE_INDEXES, STOCKIE_TABLESPACES

P = ParamSpec('P')
R = TypeVar('R')

class DatabaseFacade:
    def __init__(self, conn: psycopg2.extensions.connection) -> None:
        self.conn = conn
        self.cur = conn.cursor()
        self.conn.autocommit = True

    #####################################################
    ###             Database Helper Methods           ###
    #####################################################

    @staticmethod
    def extract_table_name(create_sql: str) -> str:
        """Extract table name from CREATE TABLE statement."""
        # Match: CREATE [TEMP|TEMPORARY] TABLE [IF NOT EXISTS] table_name
        pattern = r'CREATE\s+(?:TEMP(?:ORARY)?\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s(]+)'
        match = re.search(pattern, create_sql, re.IGNORECASE)
        if match:
            return match.group(1).strip('"').lower()
        raise ValueError(f"Could not extract table name from: {create_sql}")
    
    @staticmethod
    def extract_tablespace_name(create_sql: str) -> str:
        """Extract tablespace name from CREATE TABLESPACE statement."""
        parts = create_sql.upper().split()
        tablespace_idx = parts.index('TABLESPACE') + 1
        # Get the original case name from the original string
        original_parts = create_sql.split()
        return original_parts[tablespace_idx].lower()
    
    @staticmethod
    def extract_index_name(create_sql: str) -> str:
        """Extract index name from CREATE INDEX statement."""
        # Match: CREATE [UNIQUE] INDEX [IF NOT EXISTS] index_name
        pattern = r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s(]+)'
        match = re.search(pattern, create_sql, re.IGNORECASE)
        if match:
            return match.group(1).strip('"').lower()
        raise ValueError(f"Could not extract index name from: {create_sql}")

    #############################################################
    ###             Database Administration Methods           ###
    #############################################################

    ## 
    ## Helper methods
    ##
        
    def tablespace_exists(self, tablespace_name: str) -> bool:
        """Check if tablespace exists."""
        self.cur.execute("""
            SELECT EXISTS (
                SELECT FROM pg_tablespace 
                WHERE spcname = %s
            );
        """, (tablespace_name,))
        result = self.cur.fetchone()
        return result[0] if result is not None else False

    ## 
    ## Create methods
    ##

    def create_user(self, user_name: str, password: str) -> None:
        """Create database user."""                      
        query = sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {}").format(
            sql.Identifier(user_name), 
            sql.Literal(password)
        )
        self.cur.execute(query)
                
    def create_database(self, database_name: str, owner: str) -> None:
        """Create database for specified user."""
        query = sql.SQL("CREATE DATABASE {} WITH OWNER = {}").format(
            sql.Identifier(database_name), 
            sql.Identifier(owner)
        )
        self.cur.execute(query)

    def create_stockie_tablespaces(self, data_path: str, index_path: str, owner: str) -> None:
        """Create stockie tablespaces (data and index)."""
        if not data_path or not index_path:
            raise ValueError("data_path and index_path parameters are required")
        
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', owner):
            raise ValueError("Owner name must be alphanumeric with underscores, starting with a letter")

        for tablespace_sql in STOCKIE_TABLESPACES:
            if "data_ts" in tablespace_sql:
                query = tablespace_sql.format(owner, owner, "%s")
                self.cur.execute(query, (data_path,))
            elif "index_ts" in tablespace_sql:
                query = tablespace_sql.format(owner, owner, "%s")
                self.cur.execute(query, (index_path,))
            else:
                raise ValueError(f"Unknown tablespace type in '{tablespace_sql}' - must contain 'data_ts' or 'index_ts'")

    def create_stockie_tables(self,  owner: str) -> None:
        """Create all stockie tables and indexes."""

        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', owner):
            raise ValueError("Owner name must be alphanumeric with underscores, starting with a letter")

        for table_sql in STOCKIE_TABLES:
            query = table_sql.format(owner, "%s")
            self.cur.execute(query)

        for index_sql in STOCKIE_INDEXES:
            query = index_sql.format(owner, "%s")
            self.cur.execute(query)

    ## 
    ## Drop methods
    ##

    def drop_user(self, user_name: str) -> None:
        """Drop user (assumes user exists)."""
        #self.cur.execute(sql.SQL("DROP OWNED BY {} CASCADE").format(sql.Identifier(user_name)))
        self.cur.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(user_name)))

    def drop_database(self, database_name: str) -> None:
        """Drop database (assumes database exists)."""
        self.cur.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name)))              
    
    def drop_stockie_tablespaces(self, owner: str) -> None:
        """Drop all stockie tablespaces."""
        for tablespace_sql in STOCKIE_TABLESPACES:
            tablespace_name = self.extract_tablespace_name(tablespace_sql).replace('{}', owner)
            if self.tablespace_exists(tablespace_name):
                self.cur.execute(sql.SQL("DROP TABLESPACE {}").format(sql.Identifier(tablespace_name)))

    def drop_stockie_tables(self) -> None:
        """Drop all stockie tables and indexes using CASCADE."""
        for table_sql in reversed(STOCKIE_TABLES):
            table_name = self.extract_table_name(table_sql)
            if self.table_exists(table_name):
                self.cur.execute(sql.SQL("DROP TABLE {} CASCADE").format(sql.Identifier(table_name)))

    #############################################################
    ###                Common database methods                ###
    #############################################################

    def table_exists(self, table_names: Union[str, List[str]]) -> bool:
        if isinstance(table_names, str):
            table_names = [table_names]

        placeholders = ','.join(['%s'] * len(table_names))
        self.cur.execute(f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name IN ({placeholders})
        """, table_names)

        existing = {row[0] for row in self.cur.fetchall()}
        return all(name in existing for name in table_names)

    def with_transaction(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
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

    def vacuum_full_table(self, table_name: str) -> dict[str, Any]:
        """
        Perform VACUUM FULL on specified table to reclaim space from dead tuples.
        
        Parameters:
            table_name (str): Name of the table to vacuum
            
        Returns:
            dict: Results containing success status, duration, and any error message
        """
        import time
        
        result: dict[str, Any] = {
            'success': False,
            'duration_seconds': 0,
            'duration_minutes': 0,
            'error_message': None,
            'table_name': table_name
        }
        
        try:
            start_time = time.time()
            
            with self.conn.cursor() as cursor:
                cursor.execute(sql.SQL("VACUUM FULL {}").format(sql.Identifier(table_name)))
                self.conn.commit()
            
            duration_seconds = time.time() - start_time
            result['duration_seconds'] = round(duration_seconds, 1)
            result['duration_minutes'] = round(duration_seconds / 60, 1)
            result['success'] = True
            
        except Exception as e:
            self.conn.rollback()
            result['error_message'] = str(e)
            
        return result

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
                    df[col] = pd.to_numeric(df[col], errors='coerce') #type: ignore
                    
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

    def get_price_dates(self, ticker: str) -> set[date]:
        self.cur.execute("SELECT date FROM stock_prices WHERE ticker = %s", (ticker,))
        return {row[0] for row in self.cur.fetchall()}

    def delete_price_by_dates(self, ticker: str, dates: List[date]) -> None:
        self.cur.execute("""
            DELETE FROM stock_prices
            WHERE ticker = %s AND date = ANY(%s)
        """, (ticker, list(dates)))
        self.conn.commit()

    def insert_price_data(self, data: List[Tuple[str, date, float, float, float, float, int]]) -> None:
        execute_values(self.cur, """
            INSERT INTO stock_prices (ticker, date, open, high, low, close, volume) 
            VALUES %s
            ON CONFLICT (ticker, date) DO NOTHING
        """, data)
        self.conn.commit()

    ###############################################################
    ### Methods for interacting with technical_indicators table ###
    ###############################################################

    def bulk_insert_indicators_jsonb(self, df: pd.DataFrame) -> None:
        """
        Bulk inserts indicators from a DataFrame with JSONB date_values into the technical_indicators table.
        
        Parameters:
            df (pd.DataFrame): DataFrame with columns ['ticker', 'indicator', 'date_values']
                             where date_values is a dict of date strings to float values
        """       
        required_columns = {'ticker', 'indicator', 'date_values'}
        if not required_columns.issubset(df.columns):
            raise ValueError(f"DataFrame must contain columns: {required_columns}")
        
        if df.empty:
            return  # nothing to insert
        
        # Convert DataFrame to list of tuples for bulk insert
        data = [
            (row['ticker'], row['indicator'], Json(row['date_values']))
            for _, row in df.iterrows()
        ]
        
        query = """
            INSERT INTO technical_indicators (ticker, indicator, date_values)
            VALUES %s
            ON CONFLICT (ticker, indicator) DO UPDATE
            SET date_values = EXCLUDED.date_values;
        """

        try:
            with self.conn.cursor() as cur:
                execute_values(cur, query, data)
                self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"Failed to bulk insert indicators: {e}")



