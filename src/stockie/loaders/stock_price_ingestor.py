import yfinance as yf
from yfinance.exceptions import YFInvalidPeriodError, YFTzMissingError

import pandas as pd
import psycopg2
from datetime import datetime, timedelta, date
from typing import List, Union, Set, Dict

from stockie.util import AuditWriter
from stockie.db import DatabaseFacade

import logging
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

class StockPriceIngestor:
    """
    Stock price ingestor that downloads price data from yfinance and manages 
    database synchronization with change detection and reconciliation.
    """
    
    def __init__(self, db_facade: DatabaseFacade, start_date: Union[str, datetime, date], 
             logger: logging.Logger, delta_threshold: float = 1e-4, 
             batch_size: int = 100, max_consecutive_failures: int = 10) -> None:
        """
        Initialize the stock price ingestor.
        
        Args:
            db_facade: DatabaseFacade instance to use
            start_date: Start date for price data (str in YYYY-MM-DD format, datetime, or date)
            logger: Logger instance for output
            delta_threshold: Threshold for detecting price changes (default: 1e-4)
            batch_size: Number of tickers to process in a single yfinance batch (default: 100)
            max_consecutive_failures: Maximum consecutive batch failures before stopping (default: 10)
            
        Raises:
            RuntimeError: If start_date is invalid or required database tables are missing
        """
        self.db_facade = db_facade
        self.conn = db_facade.conn
        self.audit = AuditWriter(self.conn)
        self.logger = logger
        self.batch_size = batch_size
        self.max_consecutive_failures = max_consecutive_failures

        self.start_date = self._validate_start_date(start_date)
        self.delta_threshold = delta_threshold

        required = ["stock_prices", "stock_price_audit"]
        if not self.db_facade.table_exists(required):
            raise RuntimeError(f"Missing required tables: {', '.join(required)}")
    
    def _validate_start_date(self, start_date: Union[str, datetime, date]) -> date:
        """
        Validate and convert start_date to date object.
        
        Args:
            start_date: Start date in various formats
            
        Returns:
            Validated date object
            
        Raises:
            RuntimeError: If start_date is None or has invalid format/type
        """
        if start_date is None:
            raise RuntimeError(f"Start date is required: {start_date}")
        elif isinstance(start_date, str):
            return datetime.strptime(start_date, "%Y-%m-%d").date()
        elif isinstance(start_date, datetime):
            return start_date.date()
        elif isinstance(start_date, date):
            return start_date     
        else:
            raise RuntimeError(f"Start date has invalid datatype (only str and datetime supported): {type(start_date)}")

    def _has_changes(self, df_new: pd.DataFrame, df_db: pd.DataFrame, 
                     compare_cols: List[str], ticker: str) -> bool:
        """
        Compare new data with database data to detect changes.
        
        Args:
            df_new: New DataFrame from yfinance
            df_db: Existing DataFrame from database
            compare_cols: List of columns to compare
            ticker: Ticker symbol for logging
            
        Returns:
            True if changes are detected, False otherwise
        """
        # Check row count first
        if not self._check_row_count_match(df_new, df_db, ticker):
            return True
        
        # Check date alignment
        if not self._check_date_alignment(df_new, df_db, ticker):
            return True
        
        # Check column value differences
        return self._check_column_differences(df_new, df_db, compare_cols, ticker)
    
    def _check_row_count_match(self, df_new: pd.DataFrame, df_db: pd.DataFrame, ticker: str) -> bool:
        """Check if row counts match between new and database data."""
        if len(df_new) != len(df_db):
            reason = "row_count_mismatch"
            self.audit.log_change_summary(ticker, reason, [])
            self.logger.info(f"{ticker}: row count mismatch ({len(df_new)} vs {len(df_db)})")
            return False
        return True
    
    def _check_date_alignment(self, df_new: pd.DataFrame, df_db: pd.DataFrame, ticker: str) -> bool:
        """Check if dates align properly after merge."""
        self.logger.info(df_new.columns)
        self.logger.info(df_db.columns)
        merged = pd.merge(df_new, df_db, on="Date", how="left")
        if len(merged) != len(df_new):
            reason = "date_join_mismatch"
            self.audit.log_change_summary(ticker, reason, [])
            self.logger.info(f"{ticker}: date join mismatch")
            return False
        return True
    
    def _check_column_differences(self, df_new: pd.DataFrame, df_db: pd.DataFrame, 
                                  compare_cols: List[str], ticker: str) -> bool:
        """Check for differences in column values."""
        merged = pd.merge(df_new, df_db, on="Date", how="left")
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

    def _yfinance_download(self, tickers_batch: List[str], compare_cols: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Download stock data for one or more tickers using yfinance.
        
        Args:
            tickers_batch: List of ticker symbols to download
            compare_cols: List of columns to include in result
            
        Returns:
            Dictionary mapping ticker to DataFrame with price data
            
        Raises:
            Exception: If download fails completely
        """
        raw_data = self._fetch_raw_yfinance_data(tickers_batch)
        return self._process_raw_yfinance_data(raw_data, tickers_batch, compare_cols)

    def _fetch_raw_yfinance_data(self, tickers_batch: List[str]) -> pd.DataFrame:
        """
        Fetch raw data from yfinance API.
        
        Args:
            tickers_batch: List of ticker symbols to download
            
        Returns:
            Raw DataFrame from yfinance
            
        Raises:
            Exception: If no data is returned
        """
        today = datetime.today().date()
        end_date = today + timedelta(days=1)
        
        self.logger.info(f"Downloading {len(tickers_batch)} tickers: {tickers_batch}")
        
        tickers_str = ' '.join(tickers_batch)
        data = yf.download(
            tickers_str,
            start=self.start_date,
            end=end_date,
            auto_adjust=True,
            progress=False,
            group_by='ticker',
            threads=True
        )
        
        if data.empty:
            raise Exception(f"No data returned for tickers: {tickers_batch}")
        
        return data

    def _process_raw_yfinance_data(self, data: pd.DataFrame, tickers_batch: List[str], 
                                  compare_cols: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Process raw yfinance data into individual ticker DataFrames.
        
        Args:
            data: Raw DataFrame from yfinance
            tickers_batch: List of ticker symbols
            compare_cols: List of columns to include in result
            
        Returns:
            Dictionary mapping ticker to processed DataFrame
        """
        result = {}
        
        for ticker in tickers_batch:
            try:
                ticker_df = self._extract_ticker_data(data, ticker, compare_cols)
                result[ticker] = ticker_df
            except Exception as e:
                self.logger.error(f"Error extracting {ticker} from data: {e}")
                result[ticker] = pd.DataFrame()
        
        return result

    def _extract_ticker_data(self, data: pd.DataFrame, ticker: str, compare_cols: List[str]) -> pd.DataFrame:
        """
        Extract and format data for a ticker from yfinance multi-level columns.
        
        Args:
            data: Raw DataFrame with multi-level columns from yfinance
            ticker: Ticker symbol to extract
            compare_cols: List of columns to include in result
            
        Returns:
            Formatted DataFrame for the ticker
        """
        # Check if ticker exists in data
        if ticker not in data.columns.get_level_values(0):
            self.logger.warning(f"Ticker {ticker} not found in data")
            return pd.DataFrame()
        
        # Extract ticker data from multi-level columns and make a copy
        ticker_df = data.xs(ticker, level=0, axis=1).copy()
        
        if ticker_df.empty:
            self.logger.info(f"{ticker}: no data.")
            return pd.DataFrame()
        
        # Format the data
        self.logger.info(f'{ticker=}: {ticker_df.columns=} {len(ticker_df)}')
        
        ticker_df.reset_index(inplace=True)
        ticker_df['Date'] = ticker_df['Date'].dt.date
        ticker_df['Ticker'] = ticker
        
        return ticker_df[['Ticker', 'Date'] + compare_cols]

    def _update_data_with_changes(self, new_data: pd.DataFrame, ticker: str, 
                                 success_msg: str) -> None:
        """
        Delete existing data and insert new data, with logging.
        
        Args:
            new_data: DataFrame with new price data to insert
            ticker: Stock ticker symbol
            success_msg: Message to log on successful update
        """
        dates_to_delete = new_data['Date'].tolist()
        
        # Ensure we have the right columns for insertion
        columns_for_insert = ['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        insert_data = new_data[columns_for_insert]
        
        self.db_facade.delete_price_by_dates(ticker, dates_to_delete)
        self.db_facade.insert_price_data(insert_data.values.tolist())
        self.logger.info(f"{ticker}: {success_msg} ({len(new_data)} rows)")

    def _process_today_price(self, df: pd.DataFrame, db_df: pd.DataFrame, ticker: str) -> None:
        """
        Process today's stock price data, inserting or updating as necessary.
        
        Args:
            df: New DataFrame with price data
            db_df: Existing DataFrame from database
            ticker: Stock ticker symbol
        """
        today = datetime.today().date()
        today_row = df[df['Date'] == today]
        
        if today_row.empty:
            self.logger.info(f"{ticker}: no data for today.")
            return
        
        if today not in self.db_facade.get_price_dates(ticker):
            self._insert_today_data(today_row, ticker)
        else:
            self._update_today_data_if_changed(today_row, db_df, ticker)
    
    def _insert_today_data(self, today_row: pd.DataFrame, ticker: str) -> None:
        """Insert today's price data."""
        self.db_facade.insert_price_data(today_row.values.tolist())
        self.logger.info(f"{ticker}: inserted today's row.")
    
    def _update_today_data_if_changed(self, today_row: pd.DataFrame, db_df: pd.DataFrame, ticker: str) -> None:
        """Update today's data if changes are detected."""
        self.logger.info(f"{ticker}: today's data already present.")
        
        today_db_row = db_df[db_df['Date'] == datetime.today().date()]
        if self._has_changes(today_row, today_db_row, ['Open', 'High', 'Low', 'Close', 'Volume'], ticker):
            self._update_data_with_changes(today_row, ticker, "updated today's row")
        else:
            self.logger.info(f"{ticker}: no changes to today's row")

    def _process_historical_prices(self, df: pd.DataFrame, db_df: pd.DataFrame, ticker: str) -> None:
        """
        Process historical stock price data, reconciling with the database.
        
        Args:
            df: New DataFrame with price data
            db_df: Existing DataFrame from database
            ticker: Stock ticker symbol
        """
        today = datetime.today().date()
        hist_df = df[df['Date'] < today]
        
        if hist_df.empty:
            self.logger.info(f"{ticker}: no historical data to process.")
            return

        if db_df.empty:
            self._insert_historical_data(hist_df, ticker)
        else:
            self._reconcile_historical_data(hist_df, db_df, ticker, today)
    
    def _insert_historical_data(self, hist_df: pd.DataFrame, ticker: str) -> None:
        """Insert historical data when no prior data exists."""
        self.db_facade.insert_price_data(hist_df.values.tolist())
        self.logger.info(f"{ticker}: inserted historical rows (no prior data).")
    
    def _reconcile_historical_data(self, hist_df: pd.DataFrame, db_df: pd.DataFrame, 
                                   ticker: str, today: date) -> None:
        """Reconcile historical data with existing database data."""
        db_hist_df = db_df[db_df['Date'] < today]
        
        if self._has_changes(hist_df, db_hist_df, ['Open', 'High', 'Low', 'Close', 'Volume'], ticker):
            self._update_data_with_changes(hist_df, ticker, "reconciled historical rows")
        else:
            self.logger.info(f"{ticker}: no historical differences")

    def _process_ticker_batch(self, batch_tickers: List[str], compare_cols: List[str]) -> bool:
        """
        Process a batch of tickers using batch download.
        
        Args:
            batch_tickers: List of ticker symbols to process
            compare_cols: List of columns to compare
            
        Returns:
            True if batch processing succeeded, False if it failed
        """
        def process_ticker(ticker: str, df: pd.DataFrame) -> None:
            """Process a single ticker's data within a transaction."""
            db_df = self.db_facade.fetch_price_after_start_date(ticker, self.start_date)
            
            # Convert decimal columns to float for comparison
            decimal_cols = ['open_db', 'high_db', 'low_db', 'close_db', 'volume_db']
            for col in decimal_cols:
                if col in db_df.columns:
                    db_df[col] = pd.to_numeric(db_df[col], errors='coerce')
            
            self._process_today_price(df, db_df, ticker)
            self._process_historical_prices(df, db_df, ticker)

        try:
            batch_data = self._yfinance_download(batch_tickers, compare_cols)
            
            for ticker in batch_tickers:
                try:
                    ticker = ticker.upper()
                    df = batch_data.get(ticker, pd.DataFrame())
                    
                    if df.empty:
                        self.logger.info(f"{ticker}: no data.")
                        continue

                    self.db_facade.with_transaction(process_ticker, ticker, df)

                except YFInvalidPeriodError as e:
                    self.logger.warning(f"{ticker}: invalid period - {e} -> ignored")
                except YFTzMissingError as e:
                    self.logger.warning(f"{ticker}: delisted - {e} -> ignored")
                except Exception as e:
                    self.logger.exception(f"{ticker}: ingestion failed - {e}")
    
            return True
                
        except Exception as e:
            self.logger.error(f"Batch processing failed for {batch_tickers}: {e}")
            return False
          
    def download(self, tickers: Union[str, List[str]]) -> None:
        """
        Download and process stock price data for given tickers.
        
        Args:
            tickers: Single ticker string or list of ticker strings
            
        Raises:
            RuntimeError: If max_consecutive_failures consecutive batches fail
        """
        compare_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        ticker_list = tickers if isinstance(tickers, list) else [tickers]

        self.logger.info(f"Starting stock price download for {len(ticker_list)} tickers (batch size: {self.batch_size})...")
        self.logger.info(f"{ticker_list=}")

        consecutive_failures = 0

        for i in range(0, len(ticker_list), self.batch_size):
            batch = ticker_list[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(ticker_list) + self.batch_size - 1) // self.batch_size
            
            self.logger.info(f"Processing batch {batch_num}/{total_batches}: {batch}")
            
            batch_success = self._process_ticker_batch(batch, compare_cols)
            
            if batch_success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                self.logger.warning(f"Batch {batch_num} failed. Consecutive failures: {consecutive_failures}")
                
                if consecutive_failures >= self.max_consecutive_failures:
                    error_msg = f"Stopping after {self.max_consecutive_failures} consecutive batch failures"
                    self.logger.error(error_msg)
                    raise RuntimeError(error_msg)

        self.logger.info("Stock price download completed.")
