import pandas as pd
from importlib import import_module
from stockie.db import DatabaseUtilities

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

    def run(self):
        tickers = self.db_util.get_unique_tickers()
        benchmark_data = self._resolve_dependencies(self.indicator_config)

        for ticker in tickers:
            df = self.db_util.fetch_price_data(ticker)
            if df.empty or "close" not in df.columns:
                continue

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

    def _process(self, func, ticker: str, params: dict):
        """
        Executes the indicator function and stores the result in the database.
        """
        result = func(**params)

        if isinstance(result, pd.Series):
            name = result.name or func.__name__
            self.db_util.insert_indicator_series(result, ticker, name)

        elif isinstance(result, pd.DataFrame):
            for name, series in result.items():
                self.db_util.insert_indicator_series(series, ticker, name)

    def _resolve_dependencies(self, config: dict) -> dict[str, pd.DataFrame]:
        """
        Scans config for keys containing 'benchmark' and loads those tickers.
        Returns a dict of {ticker: return_series}
        """
        cache = {}

        for group in config.get("indicators", {}).values():
            for opts in group.values():
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