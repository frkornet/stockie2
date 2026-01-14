from psycopg2 import sql
from psycopg2.extras import execute_values, Json
import pandas as pd
from datetime import date
from typing import Any, List, Callable, Tuple, Union, Optional, TypeVar, ParamSpec
import psycopg2
import re
import time
from stockie.db.schema_definitions import STOCKIE_TABLES, STOCKIE_INDEXES, STOCKIE_TABLESPACES, ATOMIC_TABLE_SWAP

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
    
    @staticmethod
    def _extract_table_from_index_sql(index_sql: str) -> str:
        """Extract the table name that an index is created on."""
        # Match: ON table_name [USING...] or ON table_name(column...)
        pattern = r'\bON\s+([^\s(]+)'
        match = re.search(pattern, index_sql, re.IGNORECASE)
        if match:
            return match.group(1).strip('"').lower()
        raise ValueError(f"Could not extract table name from index SQL: {index_sql}")

    @staticmethod
    def _validate_sql_identifier(identifier: str, identifier_type: str = "identifier") -> None:
        """
        Validate that identifier is safe for SQL operations.
        Applies to owners, table names, index names, column names, etc.
        
        Args:
            identifier: SQL identifier to validate
            identifier_type: Type description for error message (e.g., 'owner', 'table name')
            
        Raises:
            ValueError: If identifier contains invalid characters
        """
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', identifier):
            raise ValueError(
                f"{identifier_type.capitalize()} '{identifier}' must be alphanumeric with underscores, "
                f"starting with a letter"
            )

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
        
        self._validate_sql_identifier(owner, "owner name")

        for tablespace_sql in STOCKIE_TABLESPACES:
            if "data_ts" in tablespace_sql:
                query = tablespace_sql.format(owner, owner, "%s")
                self.cur.execute(query, (data_path,))
            elif "index_ts" in tablespace_sql:
                query = tablespace_sql.format(owner, owner, "%s")
                self.cur.execute(query, (index_path,))
            else:
                raise ValueError(f"Unknown tablespace type in '{tablespace_sql}' - must contain 'data_ts' or 'index_ts'")

    def _create_tables_filtered(self, owner: str, table_filter: List[str], name_suffix: str) -> None:
        """Helper method to create filtered tables with optional suffix."""
        for table_sql in STOCKIE_TABLES:
            table_name = self.extract_table_name(table_sql)
            
            if table_filter and table_name not in table_filter:
                continue
            
            query = table_sql.format(owner, "%s")
            if name_suffix:
                query = query.replace(f"TABLE {table_name}", f"TABLE {table_name}{name_suffix}")
            self.cur.execute(query)

    def _create_indexes_filtered(self, owner: str, table_filter: List[str], name_suffix: str) -> None:
        """Helper method to create filtered indexes with optional suffix."""
        for index_sql in STOCKIE_INDEXES:
            index_name = self.extract_index_name(index_sql)
            table_name = self._extract_table_from_index_sql(index_sql)
            
            if table_filter and table_name not in table_filter:
                continue
            
            query = index_sql.format(owner, "%s")
            if name_suffix:
                query = query.replace(f"INDEX {index_name}", f"INDEX {index_name}{name_suffix}")
                query = query.replace(f"ON {table_name}", f"ON {table_name}{name_suffix}")
            
            self.cur.execute(query)

    def create_stockie_tables(self, owner: str, table_filter: List[str] = [], name_suffix: str = "") -> None:
        """
        Create stockie tables and indexes.
        
        Args:
            owner: Database owner name for tablespace formatting
            table_filter: List of stockie table names to create (empty list = all stockie tables)
            name_suffix: Optional suffix to append to table/index names (e.g., '_temp')
        """
        self._validate_sql_identifier(owner, "owner name")
        self._create_tables_filtered(owner, table_filter, name_suffix)
        self._create_indexes_filtered(owner, table_filter, name_suffix)

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
        self._validate_sql_identifier(owner, "owner name")

        for tablespace_sql in STOCKIE_TABLESPACES:
            tablespace_name = self.extract_tablespace_name(tablespace_sql).replace('{}', owner)
            if self.tablespace_exists(tablespace_name):
                self.cur.execute(sql.SQL("DROP TABLESPACE {}").format(sql.Identifier(tablespace_name)))

    def drop_stockie_tables(self, table_filter: List[str] = [], name_suffix: str = "") -> None:
        """
        Drop stockie tables and indexes using CASCADE.
        
        Args:
            table_filter: List of stockie table names to drop (empty list = all stockie tables)
            name_suffix: Optional suffix appended to table names (e.g., '_temp', '_old')
        """
        for table_sql in reversed(STOCKIE_TABLES):
            table_name = self.extract_table_name(table_sql)
            
            if table_filter and table_name not in table_filter:
                continue
            
            full_table_name = f"{table_name}{name_suffix}"
            
            if self.table_exists(full_table_name):
                self.cur.execute(sql.SQL("DROP TABLE {} CASCADE").format(sql.Identifier(full_table_name)))

    #############################################################
    ###                Common database methods                ###
    #############################################################

    def rename_table(self, old_name: str, new_name: str) -> None:
        """Rename a table from old_name to new_name"""
        self._validate_sql_identifier(old_name, "old table name")
        self._validate_sql_identifier(new_name, "new table name")

        self.cur.execute(
            sql.SQL("ALTER TABLE {} RENAME TO {}").format(
                sql.Identifier(old_name),
                sql.Identifier(new_name)
            )
        )

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

    def rename_index(self, old_name: str, new_name: str) -> None:
        """Rename an index from old_name to new_name"""
        self._validate_sql_identifier(old_name, "old index name")
        self._validate_sql_identifier(new_name, "new index name")
        self.cur.execute(
            sql.SQL("ALTER INDEX {} RENAME TO {}").format(
                sql.Identifier(old_name),
                sql.Identifier(new_name)
            )
        )

    #############################################################
    ###     Methods for atomic table swap implementation      ###
    #############################################################

    def create_temp_tables(self, owner: str) -> None:
        """Create temporary tables for atomic swap pattern."""
        self._validate_sql_identifier(owner, "owner name")
        self.create_stockie_tables(owner=owner, table_filter=ATOMIC_TABLE_SWAP, name_suffix='_temp')

    def atomic_table_swap(self) -> None:
        """
        Atomically swap tables in 4 steps. Each step is completed for all tables
        in ATOMIC_TABLE_SWAP before moving to the next step:
        1. Rename <table> to <table>_old
        2. Rename <table>_temp to <table>
        3. Drop <table>_old tables
        4. Drop _temp from all indexes on <table>
        
        Note: The function assumes that the _temp tables exist and have been populated with data.
        The indexes on _temp tables have also been created with a _temp suffix.
        
        Raises:
            RuntimeError: If swap fails, with phase and object context for debugging
        """
        current_phase = None
        current_object = None
        
        def phase_1_renaming_tables_to_old() -> None:
            nonlocal current_phase, current_object
            current_phase = "Phase 1: Renaming tables to _old"
            for table_name in ATOMIC_TABLE_SWAP:
                current_object = table_name
                if self.table_exists(table_name):
                    old_name = f"{table_name}_old"
                    self.rename_table(table_name, old_name)
        
        def phase_2_removing_temp_suffix_from_tablenames() -> None:
            nonlocal current_phase, current_object
            current_phase = "Phase 2: Removing _temp suffix from tablenames"
            for table_name in ATOMIC_TABLE_SWAP:
                current_object = f"{table_name}_temp"
                temp_name = f"{table_name}_temp"
                self.rename_table(temp_name, table_name)
        
        def phase_3_dropping_old_tables() -> None:
            nonlocal current_phase, current_object
            current_phase = "Phase 3: Dropping old tables"
            self.drop_stockie_tables(table_filter=ATOMIC_TABLE_SWAP, name_suffix='_old')
        
        def phase_4_removing_temp_suffix_from_indexes() -> None:
            nonlocal current_phase, current_object
            current_phase = "Phase 4: Removing _temp suffix from indexes"
            for index_sql in STOCKIE_INDEXES:
                index_name = self.extract_index_name(index_sql)
                table_name = self._extract_table_from_index_sql(index_sql)
                
                if table_name in ATOMIC_TABLE_SWAP:
                    current_object = f"{index_name}_temp"
                    temp_index = f"{index_name}_temp"
                    self.rename_index(temp_index, index_name)
        
        try:
            phase_1_renaming_tables_to_old()
            phase_2_removing_temp_suffix_from_tablenames()
            phase_3_dropping_old_tables()
            phase_4_removing_temp_suffix_from_indexes()
            
        except Exception as e:
            error_msg = f"Swap failed during {current_phase} on object '{current_object}': {str(e)}"
            raise RuntimeError(error_msg) from e    

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

    def fetch_price_data(self, ticker: str, table_name: str = "stock_prices") -> pd.DataFrame:
        """
        Returns a DataFrame with date and close price for the given ticker from specified table.
        """
        self._validate_sql_identifier(table_name, "table name")
        
        query = sql.SQL("""
            SELECT date, close, low, high, volume
            FROM {}
            WHERE ticker = %s
            ORDER BY date;
        """).format(sql.Identifier(table_name))
        
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
        """Fetch price data after start date."""
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
        """Get all dates for a ticker."""
        self.cur.execute("SELECT date FROM stock_prices WHERE ticker = %s", (ticker,))
        return {row[0] for row in self.cur.fetchall()}

    def delete_price_by_dates(self, ticker: str, dates: List[date]) -> None:
        """Delete price data for specific dates."""
        self.cur.execute("""
            DELETE FROM stock_prices
            WHERE ticker = %s AND date = ANY(%s)
        """, (ticker, list(dates)))
        self.conn.commit()

    def bulk_insert_price_data(self, data: List[Tuple[str, date, float, float, float, float, int]]) -> None:
        """Bulk insert price data into stock_prices_temp."""
        execute_values(self.cur, """
            INSERT INTO stock_prices_temp (ticker, date, open, high, low, close, volume) 
            VALUES %s
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
            INSERT INTO technical_indicators_temp (ticker, indicator, date_values)
            VALUES %s
        """

        try:
            with self.conn.cursor() as cur:
                execute_values(cur, query, data)
                self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"Failed to bulk insert indicators: {e}")



