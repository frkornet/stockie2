import argparse
import pandas as pd
import numpy as np
import psycopg2

import os
import multiprocessing

from importlib import import_module
from pathlib import Path
from stockie.db import DatabaseFacade
from stockie.loaders.config_loader import ConfigLoader
from stockie.log.custom_logger import CustomLogger
from typing import List, Dict, Any, Callable

class CalculateIndicators:
    def __init__(self, db_util: DatabaseFacade, config: dict, source_table: str = "stock_prices") -> None:
        """
        Initializes the indicator runner with database access and config.

        Args:
            db_util: DatabaseFacade instance
            config: Configuration dictionary
            source_table: Table to read price data from (default: 'stock_prices',
                         use 'stock_prices_temp' during daily job bulk load)

        Example config["indicators"]:
        {
          "risk": {
              "alpha": {
                  "enabled": true,
                  "window": [63],
                  "benchmark": "SPY",
                  "risk_free_benchmark": "DTB3"
              },
              ...
          },
          ...
        }
        """
        self.db_util = db_util
        self.source_table = source_table
        self.indicator_config = config.get("indicators", {})

        log_config = config['calculate_indicators']
        self.logger = CustomLogger(
            name=__file__,
            log_to_console=log_config['console'],
            log_level=log_config['log_level'],
            log_dir=os.path.dirname(log_config['log_filename']),
            log_filename=os.path.basename(log_config['log_filename'])
        ).get_logger()

        # DataFrame matching database table structure: ticker, indicator, date_values (JSONB)
        self.ticker_indicators_df = pd.DataFrame(columns=["ticker", "indicator", "date_values"])
        
        # Batch configuration for database writes
        self.db_batch_size = config.get('calculate_indicators', {}).get('db_batch_size', 100)
        self.processed_tickers = 0
        

    def run(self, tickers: list[str], part: int =0) -> None:
        """
        Runs the indicator calculations for the provided tickers.
        This method will fetch price data for each ticker, calculate indicators based on the configuration,
        and save the results directly to the database.
        :param tickers: List of ticker symbols to calculate indicators for.
        :param part: Part number for multiprocessing identification and logging.
        :raises ValueError: If there are mismatched list lengths in the configuration for indicators.
        :raises ModuleNotFoundError: If the indicator module cannot be found.
        :raises AttributeError: If the indicator class or method cannot be found.
        """
        self.logger.info(f'\n\n *** Starting calculate technical indicators run.')
        benchmark_data = self._resolve_dependencies(self.indicator_config)

        for ticker in tickers:
            df = self.db_util.fetch_price_data(ticker, table_name=self.source_table)
            if df.empty or "close" not in df.columns:
                continue

            self.logger.info(f"Calculating indicators for {ticker}...")
            for family, indicators in self.indicator_config.items():
                try:
                    module = import_module(f"stockie.indicators.{family}")
                    cls = getattr(module, f"{family.capitalize()}Indicators")
                except (ModuleNotFoundError, AttributeError):
                    continue

                instance = cls(df)

                for indicator, options in indicators.items():
                    if not isinstance(options, dict) or not options.get("enabled", False):
                        continue

                    func = getattr(instance, indicator, None)
                    if not callable(func):
                        continue

                    raw_params = {k: v for k, v in options.items() if k != "enabled"}
                    list_params = {k: v for k, v in raw_params.items() if isinstance(v, list)}

                    if list_params:
                        lengths = {len(v) for v in list_params.values()}
                        if len(lengths) != 1:
                            raise ValueError(
                                f"Mismatched list lengths in config for {family}.{indicator}: {list_params}"
                            )

                        zipped = zip(*list_params.values())
                        for values in zipped:
                            zipped_params = raw_params.copy()
                            for key, val in zip(list_params.keys(), values):
                                zipped_params[key] = val
                            resolved = self._inject_benchmark_series(zipped_params, benchmark_data)
                            self._process(func, ticker, resolved)
                    else:
                        resolved = self._inject_benchmark_series(raw_params, benchmark_data)
                        self._process(func, ticker, resolved)

            # Increment processed ticker count
            self.processed_tickers += 1
            
            # Save indicators in batches for better performance
            if self.processed_tickers % self.db_batch_size == 0:
                try:
                    self._save_batch_indicators()
                except Exception as e:
                    self.logger.error(f"Failed to save batch at ticker {self.processed_tickers}: {e}")
                    # Clear the DataFrame to avoid carrying over incomplete data
                    self.ticker_indicators_df = self.ticker_indicators_df.iloc[0:0]
        
        # Save any remaining indicators at the end
        if not self.ticker_indicators_df.empty:
            try:
                self._save_batch_indicators()
            except Exception as e:
                self.logger.error(f"Failed to save final batch: {e}")

        self.logger.info(f'*** Finished calculate technical indicator run.')
        
    def _save_batch_indicators(self) -> None:
        """
        Save all indicators in the DataFrame to database in batches for better performance.
        """
        if self.ticker_indicators_df.empty:
            return  # Nothing to save
        
        unique_tickers = self.ticker_indicators_df['ticker'].unique()
        num_tickers = len(unique_tickers)
        num_indicators = len(self.ticker_indicators_df)
        
        self.logger.info(f"Saving batch: {num_indicators} indicators for {num_tickers} tickers to database...")
        
        # Use bulk JSONB insert for the entire batch
        self.db_util.bulk_insert_indicators_jsonb(self.ticker_indicators_df)
        
        # Clear the DataFrame after successful save
        self.ticker_indicators_df = self.ticker_indicators_df.iloc[0:0]

    def _process(self, func: Callable, ticker: str, params: dict) -> None:
        """
        Executes the indicator function and stores the result in the database.
        """
        result = func(**params)

        if isinstance(result, pd.Series):
            name = result.name or func.__name__
            self._add_series_to_ticker_indicators(ticker, name, result)

        elif isinstance(result, pd.DataFrame):
            for name, series in result.items():
                self._add_series_to_ticker_indicators(ticker, name, result[name])

    def _add_series_to_ticker_indicators(self, ticker: str, name: str, series: pd.Series) -> None:
        """
        Add a pandas Series as a JSON time series for a ticker-indicator combination.
        """
        # Convert pandas Series to JSON dict, handling NaN and infinite values
        clean_series = series.dropna()
        if clean_series.empty:
            return  # Skip empty series
        
        # Filter out infinite values (not valid JSON) and convert to float
        date_values_json = {}
        for date, value in clean_series.items():
            if np.isfinite(value):  # Only include finite values (excludes NaN, +Inf, -Inf)
                date_values_json[date.strftime('%Y-%m-%d')] = float(value)
        
        # Skip if no valid values remain after filtering
        if not date_values_json:
            return
        
        # Add single row to DataFrame matching database structure
        new_row = pd.DataFrame({
            "ticker": [ticker],
            "indicator": [name], 
            "date_values": [date_values_json]
        })
        
        self.ticker_indicators_df = pd.concat([self.ticker_indicators_df, new_row], ignore_index=True)

    def _resolve_dependencies(self, config: dict) -> dict[str, pd.DataFrame]:
        """
        Scans config for keys containing 'benchmark' and loads those tickers.
        Returns a dict of {ticker: return_series}
        """
        cache = {}

        for family, indicators in self.indicator_config.items():
            for indicator, opts in indicators.items():
                if not isinstance(opts, dict) or not opts.get("enabled", False):
                    continue

                for key, val in opts.items():
                    if "benchmark" in key.lower() and isinstance(val, str) and val not in cache:
                        df = self.db_util.fetch_price_data(val, table_name=self.source_table)
                        if not df.empty and "close" in df.columns:
                            cache[val] = df

        return cache

    def _inject_benchmark_series(self, params: dict, benchmark_data: dict[str, pd.DataFrame]) -> dict:
        """
        Replaces any 'benchmark'-related string param with its Series from the cache.
        """
        out = params.copy()
        for key, val in out.items():
            if "benchmark" in key.lower() and isinstance(val, str):
                if val in benchmark_data:
                    out[key] = benchmark_data[val]
        return out

def chunk_list(lst: List[Any], n: int) -> List[List[Any]]:
    """Splits list `lst` into `n` roughly equal chunks."""
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]

def worker(tickers_chunk: List[str], config: Dict[str, Any], part: int, source_table: str = "stock_prices") -> None:
    """Worker function to run indicator calculations on a chunk of tickers."""
    # Remove admin_user from connection params (it's used elsewhere, not by psycopg2)
    db_config = {k: v for k, v in config["db"].items() if k != 'admin_user'}
    db_conn = psycopg2.connect(**db_config)
    db_util = DatabaseFacade(db_conn)
    runner = CalculateIndicators(db_util, config, source_table=source_table)
    runner.run(tickers_chunk, part)
    db_conn.close()

def calculate_indicators(db_facade: DatabaseFacade, full_config: Dict[str, Any], source_table: str = "stock_prices") -> None:
    """
    Calculate technical indicators using the provided database facade and configuration.
    
    Args:
        db_facade: DatabaseFacade instance to use
        full_config: Full configuration dictionary
        source_table: Table to read price data from (default: 'stock_prices',
                     use 'stock_prices_temp' during daily job bulk load)
    """
    tickers = db_facade.get_unique_tickers()

    indicator_config = full_config.get("calculate_indicators", {})
    n_processes = indicator_config.get("calculate_processes", 1)

    # process the benchmarks and remove them from the main ticker list
    benchmarks = full_config.get("tickers", {}).get("benchmarks", [])
    indicator_runner = CalculateIndicators(db_facade, full_config, source_table=source_table)
    if benchmarks:
        indicator_runner.run(benchmarks)
        tickers = list(set(tickers).difference(set(benchmarks)))

    if n_processes > 1:
        chunks = chunk_list(tickers, n_processes)

        process_list = []
        for i, chunk in enumerate(chunks):
            chunk = sorted(chunk)
            p = multiprocessing.Process(target=worker, args=(chunk, full_config, i, source_table))
            p.start()
            process_list.append(p)

        for p in process_list:
            p.join()

    else:
        indicator_runner = CalculateIndicators(db_facade, full_config, source_table=source_table)
        indicator_runner.run(tickers)

