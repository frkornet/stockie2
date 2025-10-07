-- Create stockie role
create role stockie with login password 'stockie';
create role stockie_dev with login password 'stockie_dev';

-- Create table spaces for stockie_db database
create tablespace stockie_data_ts
    owner stockie
    location '/mnt/pgdb/stockie/data';

create tablespace stockie_dev_data_ts
    owner stockie_dev
    location '/mnt/pgdb/stockie_dev/data';

create tablespace stockie_index_ts
    owner stockie
    location '/mnt/pgdb/stockie/index';

create tablespace stockie_dev_index_ts
    owner stockie_dev
    location '/mnt/pgdb/stockie_dev/index';

create database stockie_db
    with owner = stockie
    tablespace =stockie_data_ts;

create database stockie_dev_db
    with owner = stockie_dev
    tablespace =stockie_dev_data_ts;

#########

SET role stockie;

-- Create the stock_prices table
drop table stock_prices;

create table stock_prices (
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume NUMERIC(20,0),
    adj_close REAL
) tablespace stockie_data_ts;

create unique index stock_prices_pk_idx
    ON stock_prices (ticker, date)
    tablespace stockie_index_ts;

alter table stock_prices
    add constraint stock_prices_pkey
    primary key using index stock_prices_pk_idx;


drop table stock_price_audit;

create table stock_price_audit (
    ticker TEXT,
    date DATE,
    message TEXT,
    change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) tablespace stockie_data_ts;

drop table technical_indicators;

create table technical_indicators (
    ticker TEXT NOT NULL,
    indicator TEXT NOT NULL,
    date_values JSONB NOT NULL
) tablespace stockie_data_ts;

create unique index technical_indicators_pk_idx
    ON technical_indicators (ticker, indicator)
    tablespace stockie_index_ts;

alter table technical_indicators
    add constraint technical_indicators_pkey
    primary key using index technical_indicators_pk_idx;

###########

SET role stockie_dev;

-- Create the stock_prices table
drop table stock_prices;

create table stock_prices (
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume NUMERIC(20,0),
    adj_close REAL
) tablespace stockie_dev_data_ts;

create unique index stock_prices_pk_idx
    ON stock_prices (ticker, date)
    tablespace stockie_dev_index_ts;

alter table stock_prices
    add constraint stock_prices_pkey
    primary key using index stock_prices_pk_idx;

drop table stock_price_audit;

create table stock_price_audit (
    ticker TEXT,
    date DATE,
    message TEXT,
    change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
 ) tablespace stockie_dev_data_ts;

drop table technical_indicators;

create table technical_indicators (
    ticker TEXT NOT NULL,
    indicator TEXT NOT NULL,
    date_values JSONB NOT NULL
) tablespace stockie_dev_data_ts;

create unique index technical_indicators_pk_idx
    ON technical_indicators (ticker, indicator)
    tablespace stockie_dev_index_ts;

alter table technical_indicators
    add constraint technical_indicators_pkey
    primary key using index technical_indicators_pk_idx;