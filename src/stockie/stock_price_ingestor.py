import yfinance as yf
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta, date

from stockie.audit_writer import AuditWriter
from stockie.database_utilities import DatabaseUtilities
from stockie.custom_logger import CustomLogger

logger = CustomLogger().get_logger()

class StockPriceIngestor:
    def __init__(self, db_config, start_date, delta_threshold=1e-4, logger=logger):
        self.conn = psycopg2.connect(**db_config)
        self.cur = self.conn.cursor()
        self.audit = AuditWriter(self.cur)
        self.logger = logger

        if start_date is None:
            raise RuntimeError(f"Start date is required: {start_date}")
        elif isinstance(start_date, str):
            self.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        elif isinstance(start_date, datetime):
            self.start_date = start_date.date()
        elif isinstance(start_date, date):
            self.start_date = start_date     
        else:
            raise RuntimeError(f"Start date has invalid datatype (only str and datetime supported): {type(start_date)}")
        
        self.delta_threshold = delta_threshold

        db_util = DatabaseUtilities(self.conn)
        required = ["stock_prices", "stock_price_audit"]
        if not db_util.table_exists(required):
            raise RuntimeError(f"Missing required tables: {', '.join(required)}")

    def _fetch_db_prices(self, ticker, start_date):
        self.cur.execute("""
            SELECT date, open, high, low, close, adj_close, volume
            FROM stock_prices
            WHERE ticker = %s AND date >= %s
        """, (ticker, start_date))
        return pd.DataFrame(self.cur.fetchall(), columns=[
            'Date', 'open_db', 'high_db', 'low_db',
            'close_db', 'adj_close_db', 'volume_db'
        ])

    def _get_existing_dates(self, ticker):
        self.cur.execute("SELECT date FROM stock_prices WHERE ticker = %s", (ticker,))
        return {row[0] for row in self.cur.fetchall()}

    def _delete_rows(self, ticker, dates):
        self.cur.execute("""
            DELETE FROM stock_prices
            WHERE ticker = %s AND date = ANY(%s)
        """, (ticker, list(dates)))
        self.conn.commit()

    def _insert_rows(self, records):
        # adj_close is not in dataframe
        execute_values(self.cur, """
            INSERT INTO stock_prices (ticker, date, open, high, low, close, volume) 
            VALUES %s
            ON CONFLICT (ticker, date) DO NOTHING
        """, records)
        self.conn.commit()

    def _has_changes(self, df_new, df_db, compare_cols, ticker):
        if len(df_new) != len(df_db):
            reason = "row_count_mismatch"
            self.audit.log_change_summary(ticker, reason, [])
            self.logger.info(f"{ticker}: row count mismatch ({len(df_new)} vs {len(df_db)})")
            return True

        logger.info(df_new.columns)
        logger.info(df_db.columns)
        merged = pd.merge(df_new, df_db, on="Date", how="left")
        if len(merged) != len(df_new):
            reason = "date_join_mismatch"
            self.audit.log_change_summary(ticker, reason, [])
            self.logger.info(f"{ticker}: date join mismatch")
            return True

        mismatched_cols = set()
        for col in compare_cols:
            db_col = f"{col.lower()}_db"
            if db_col not in merged.columns:
                mismatched_cols.add(col)
                continue
            diff = (merged[col] - merged[db_col]).abs() > self.delta_threshold
            if diff.any():
                mismatched_cols.add(col)

        if mismatched_cols:
            reason = "column_value_mismatch"
            self.audit.log_change_summary(ticker, reason, sorted(mismatched_cols))
            self.logger.info(f"{ticker}: mismatched columns: {sorted(mismatched_cols)}")
            return True

        return False

    def _yfinance_ticker_download(self, ticker, compare_cols): 
        """Download stock data for a single ticker using yfinance."""
        today = datetime.today().date()
        df = yf.download(ticker, start=self.start_date, end=today + timedelta(days=1), auto_adjust=True, progress=False)
        df.columns = df.columns.droplevel(1)
        logger.info(f'{ticker=}: {df.columns=} {len(df)}')
        if df.empty:
            self.logger.info(f"{ticker}: no data.")
            return df

        df.reset_index(inplace=True)
        df['Date'] = df['Date'].dt.date
        df['Ticker'] = ticker
        return df[['Ticker', 'Date'] + compare_cols]

    def _process_today_price(self, df, db_df, ticker):
        """Process today's stock price data, inserting or updating as necessary."""
        today = datetime.today().date()
        today_row = df[df['Date'] == today]
        if not today_row.empty:
            if today not in self._get_existing_dates(ticker):
                self._insert_rows(today_row.values.tolist())
                self.logger.info(f"{ticker}: inserted today's row.")
            else:
                self.logger.info(f"{ticker}: today's data already present.")
                if not db_df.empty:
                    today_db_row = db_df[db_df['Date'] == today]
                    if self._has_changes(today_row, today_db_row, ['Open', 'High', 'Low', 'Close', 'Volume'], ticker):
                        self._delete_rows(ticker, [today])
                        self._insert_rows(today_row.values.tolist())
                        self.logger.info(f"{ticker}: updated today's row.")
                    else:
                        self.logger.info(f"{ticker}: no changes to today's row.")
        else:
            self.logger.info(f"{ticker}: no data for today.")

    def _process_historical_prices(self, df, db_df, ticker):
        """Process historical stock price data, reconciling with the database."""
        today = datetime.today().date()
        hist_df = df[df['Date'] < today]
        if hist_df.empty:
            self.logger.info(f"{ticker}: no historical data to process.")
            return

        if db_df.empty:
            self._insert_rows(hist_df.values.tolist())
            self.logger.info(f"{ticker}: inserted historical rows (no prior data).")
            return

        db_df = db_df[db_df['Date'] < today]
        if self._has_changes(hist_df, db_df, ['Open', 'High', 'Low', 'Close', 'Volume'], ticker):
            self._delete_rows(ticker, hist_df['Date'].tolist())
            self._insert_rows(hist_df[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']].values.tolist())
            self.logger.info(f"{ticker}: reconciled {len(hist_df)} historical rows.")
        else:
            self.logger.info(f"{ticker}: no historical differences.")
    
          
    def download(self, tickers):
        compare_cols = ['Open', 'High', 'Low', 'Close', 'Volume']

        for ticker in tickers if isinstance(tickers, list) else [tickers]:
            try:
                ticker = ticker.upper()
                df = self._yfinance_ticker_download(ticker, compare_cols)
                if df.empty:
                    self.logger.info(f"{ticker}: no data.")
                    continue

                db_df = self._fetch_db_prices(ticker, self.start_date)
                self._process_today_price(df, db_df, ticker)
                self._process_historical_prices(df, db_df, ticker)

            except Exception as e:
                self.logger.exception(f"{ticker}: ingestion failed - {e}")

    def close(self):
        self.cur.close()
        self.conn.close()