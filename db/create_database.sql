-- Create the stock_prices table
CREATE TABLE IF NOT EXISTS stock_prices (
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume BIGINT,
    adj_close REAL,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS stock_price_audit (
    ticker TEXT,
    date DATE,
    column_changed TEXT,
    old_value FLOAT,
    new_value FLOAT,
    change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE technical_indicators (
    ticker TEXT,
    indicator TEXT,
    date DATE,
    value DOUBLE PRECISION,
    PRIMARY KEY (ticker, indicator, date)
);