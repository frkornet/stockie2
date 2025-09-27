import argparse
import pandas as pd
import psycopg2

import os
import csv
import multiprocessing
import cProfile
import pstats

from importlib import import_module
from pathlib import Path
from stockie.db import DatabaseUtilities
from stockie.loaders.config_loader import ConfigLoader
from stockie.log.custom_logger import CustomLogger

class CalculateIndicators:
    def __init__(self, db_util: DatabaseUtilities, config: dict):
        """
        Initializes the indicator runner with database access and config.

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
        self.indicator_config = config.get("indicators", {})

        log_config = config['calculate_indicators']
        self.logger = CustomLogger(
            name=__file__,
            log_to_console=log_config['console'],
            log_level=log_config['log_level'],
            log_dir=os.path.dirname(log_config['log_filename']),
            log_filename=os.path.basename(log_config['log_filename'])
        ).get_logger()

        self.ticker_indicators_df = pd.DataFrame(columns=["ticker", "indicator", "date", "value"])
        self.cvs_header = True
        self.ticker_df_cache = {}
        self.ticker_counter = 0
        
        calc_indicators_config = config.get("calculate_indicators", {})
        self.cvs_directory = calc_indicators_config.get("cvs_directory", "/tmp/")
        self.save_every_n_tickers = calc_indicators_config.get("save_every_n_tickers", 10)
        self.concatenate_dataframes = calc_indicators_config.get("concatenate_dataframes", True)
        

    def run(self, tickers: list[str], part: int =0) -> None:
        """
        Runs the indicator calculations for the provided tickers.
        This method will fetch price data for each ticker, calculate indicators based on the configuration,
        and save the results to a CSV file.
        :param tickers: List of ticker symbols to calculate indicators for.
        :param part: Part number for the CSV file, used for chunking large datasets.
        :raises ValueError: If there are mismatched list lengths in the configuration for indicators.
        :raises ModuleNotFoundError: If the indicator module cannot be found.
        :raises AttributeError: If the indicator class or method cannot be found.
        """
        self.logger.info(f'\n\n *** Starting calculate technical indicators run.')
        benchmark_data = self._resolve_dependencies(self.indicator_config)
        self._remove_cvs_file(part)

        for ticker in tickers:
            df = self.db_util.fetch_price_data(ticker)
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

            self._save_ticker_indicators(ticker, part, force=False)

        if tickers:
            self._save_ticker_indicators(ticker, part, force=True)    
        self.logger.info(f'*** Finished calculate technical indicator run.')
        
    def _remove_cvs_file(self, part):
        """
        Removes the CSV file if it exists.
        """
        self.cvs_file_name = f"{self.cvs_directory}indicators_part_{part}.csv"
        cvs_file = Path(self.cvs_file_name)
        if cvs_file.exists():
            cvs_file.unlink()
        
    def _save_ticker_indicators(self, ticker: str, part: int, force=False):
        """
        Saves the current ticker's indicators DataFrame to the cache and optionally to CSV.
        If `force` is True, it will save immediately regardless of the ticker count."""
        self.ticker_df_cache[ticker] = self.ticker_indicators_df
        self.ticker_indicators_df = self.ticker_indicators_df.iloc[0:0]

        if (self.ticker_counter + 1) % self.save_every_n_tickers == 0 or force:
            self._save_dfs_to_cvs(ticker, part)
        else:
            self.ticker_counter += 1

    def _save_dfs_to_cvs(self, ticker: str, part: int):
        """ 
        Saves the cached DataFrames to a CSV file. 
        If `concatenate_dataframes` is True, it concatenates all DataFrames before saving to CSV.
        """
        self.logger.info(f"Saving indicators for {self.ticker_counter + 1} tickers to {self.cvs_file_name}...")

        if self.concatenate_dataframes:
            dfs = pd.concat(self.ticker_df_cache.values(), ignore_index=True)
            dfs.to_csv(
                self.cvs_file_name, encoding='utf-8',
                index=False, mode='a', quoting=csv.QUOTE_ALL, header=self.cvs_header
            )
            self.cvs_header = False
        else:
            for t_df in self.ticker_df_cache.values():
                if not t_df.empty:
                    t_df.to_csv(
                        self.cvs_file_name, encoding='utf-8',
                        index=False, mode='a', quoting=csv.QUOTE_ALL, header=self.cvs_header
                    )
                    self.cvs_header = False
        
        self.ticker_df_cache.clear()
        self.ticker_counter = 0

    def _process(self, func, ticker: str, params: dict):
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

    def _add_series_to_ticker_indicators(self, ticker: str, name: str, series: pd.Series, ):
        df = pd.DataFrame({
                "ticker": ticker,
                "indicator": name,
                "date": series.index,
                "value": series.values
            },
        ).dropna(subset=["value"])
        df_list = ([ self.ticker_indicators_df] if not self.ticker_indicators_df.empty else []) + [df]
        self.ticker_indicators_df = pd.concat(df_list,ignore_index=True,)

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
                        df = self.db_util.fetch_price_data(val)
                        if not df.empty and "close" in df.columns:
                            cache[val] = df

        return cache

    def _inject_benchmark_series(self, params: dict, benchmark_data: dict[str, pd.Series]) -> dict:
        """
        Replaces any 'benchmark'-related string param with its Series from the cache.
        """
        out = params.copy()
        for key, val in out.items():
            if "benchmark" in key.lower() and isinstance(val, str):
                if val in benchmark_data:
                    out[key] = benchmark_data[val]
        return out

def chunk_list(lst, n):
    """Splits list `lst` into `n` roughly equal chunks."""
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]

def worker(tickers_chunk, config, part):
    """Worker function to run indicator calculations on a chunk of tickers."""
    db_conn = psycopg2.connect(**config["db"])
    db_util = DatabaseUtilities(db_conn)
    runner = CalculateIndicators(db_util, config)
    runner.run(tickers_chunk, part)
    db_conn.close()

def calculate_indicators(config_dir):
    """
    Main function to calculate indicators and store the result in CSV files.
    """
    config_loader = ConfigLoader(
        config_path=os.path.join(config_dir, "settings.yaml"),
        dotenv_path=os.path.join(config_dir, ".env")
    )
    config = config_loader.get()
    db_config = config["db"]
    db_conn = psycopg2.connect(**db_config)
    db_util = DatabaseUtilities(db_conn)

    tickers = db_util.get_unique_tickers()

    n_processes = config.get("calculate_indicators", {}).get("calculate_processes", 1)
    if n_processes > 1:
        chunks = chunk_list(tickers, n_processes)
        benchmarks = config.get("tickers", {}).get("benchmarks", [])

        process_list = []
        for i, chunk in enumerate(chunks):
            chunk = sorted(list(set(chunk + benchmarks)))
            p = multiprocessing.Process(target=worker, args=(chunk, config, i))
            p.start()
            process_list.append(p)

        for p in process_list:
            p.join()

    else:
        indicator_runner = CalculateIndicators(db_util, config)
        indicator_runner.run(tickers)

    db_conn.close()

def export_profile_to_csv(stats, filename="profile.csv"):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Function", "Calls", "Total Time", "Cumulative Time"])
        for func, stat in stats.stats.items():
            func_name = f"{func[0]}:{func[1]}({func[2]})"
            cc, nc, tt, ct, callers = stat
            writer.writerow([func_name, nc, tt, ct])

def main():
    parser = argparse.ArgumentParser(description="Calculate technical indicators and store results in CSV files.")
    parser.add_argument("--config-dir", default="/mnt/repos/stockie/config/", help="Directory containing settings.yaml and .env")
    args = parser.parse_args()

    config_loader = ConfigLoader(
        config_path=os.path.join(args.config_dir, "settings.yaml"),
        dotenv_path=os.path.join(args.config_dir, ".env")
    )
    config = config_loader.get()
    profile = config.get("calculate_indicators", {}).get("profile", False)

    if profile:
        print("Profiling is enabled. This may take a while...")
        profiler = cProfile.Profile()
        profiler.enable()

    calculate_indicators(args.config_dir)

    if profile:
        profiler.disable()
        stats = pstats.Stats(profiler).strip_dirs().sort_stats("cumtime")
        stats.print_stats(30)
        stats.dump_stats("profile_output.prof")
        export_profile_to_csv(stats, "profile_output.csv")

if __name__ == "__main__":
    main()