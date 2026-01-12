"""
Centralized schema definitions for the stockie application.

This module contains all table and index definitions in a simple,
readable format that makes the database structure easy to understand
and maintain.
"""

STOCKIE_TABLES = [
    """
    CREATE TABLE stock_prices (
        ticker TEXT NOT NULL,
        date DATE NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume NUMERIC(20,0),
        adj_close REAL,
        PRIMARY KEY (ticker, date)
    ) TABLESPACE {}_data_ts
    """,
    
    """
    CREATE TABLE stock_price_audit (
        ticker TEXT,
        date DATE,
        message TEXT,
        change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) TABLESPACE {}_data_ts
    """,
    
    """
    CREATE TABLE technical_indicators (
        ticker TEXT NOT NULL,
        indicator TEXT NOT NULL,
        date_values JSONB NOT NULL,
        PRIMARY KEY (ticker, indicator)
    ) TABLESPACE {}_data_ts
    """
]

STOCKIE_INDEXES = [
    "CREATE INDEX stock_prices_ticker_idx ON stock_prices (ticker) TABLESPACE {}_index_ts",
    "CREATE INDEX stock_prices_date_idx ON stock_prices (date) TABLESPACE {}_data_ts",
    "CREATE INDEX stock_price_audit_ticker_idx ON stock_price_audit (ticker) TABLESPACE {}_index_ts",
    "CREATE INDEX stock_price_audit_date_idx ON stock_price_audit (date) TABLESPACE {}_data_ts",
    "CREATE INDEX technical_indicators_ticker_idx ON technical_indicators (ticker) TABLESPACE {}_index_ts",
    "CREATE INDEX technical_indicators_indicator_idx ON technical_indicators (indicator) TABLESPACE {}_index_ts",
    "CREATE INDEX technical_indicators_date_values_gin_idx ON technical_indicators USING GIN (date_values) TABLESPACE {}_index_ts"
]

STOCKIE_TABLESPACES = [
    "CREATE TABLESPACE {}_data_ts OWNER {} LOCATION {}",
    "CREATE TABLESPACE {}_index_ts OWNER {} LOCATION {}"
]