import pandas as pd
import numpy as np

class BaseIndicators:
    def __init__(self, df: pd.DataFrame, horizon_period: int = 252, use_log_returns: bool = False):
        self.set_data(df)
        if not isinstance(horizon_period, int) or horizon_period <= 0:
            raise ValueError("Horizon period must be a positive integer.")
        self.horizon_period = horizon_period
        self.use_log_returns = use_log_returns

    def set_data(self, df: pd.DataFrame):
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Expected a pandas DataFrame")

        if "close" not in df.columns:
            raise ValueError("DataFrame must contain a 'close' column")

        if "date" in df.columns:
            df = df.set_index("date")

        if not pd.api.types.is_datetime64_any_dtype(df.index):
            raise ValueError("DataFrame index must be datetime or 'date' column must be convertible to datetime")

        df = df.sort_index()
        self.df = df.copy()

    def _normalize_series_input(
        self,
        obj: pd.Series | pd.DataFrame | float,
        index: pd.Index,
        dailyize: bool = False,
        label: str = "input"
    ) -> pd.Series:
        if isinstance(obj, pd.DataFrame):
            if "close" not in obj.columns:
                raise ValueError(f"{label} DataFrame must contain a 'close' column.")
            series = obj["close"].reindex(index).ffill()
        elif isinstance(obj, pd.Series):
            series = obj.reindex(index).ffill()
        elif isinstance(obj, (int, float)):
            if dailyize:
                value = ( obj / self.horizon_period if self.use_log_returns else
                          ((1 + obj) ** (1 / self.horizon_period)) - 1.0)
            else:
                value = obj

            series = pd.Series(value, index=index)
        else:
            raise TypeError(f"{label} must be a Series, DataFrame, or scalar.")

        return series

    def _compute_returns(
        self,
        series: pd.Series,
        fillna: bool = False,
        label: str = "returns"
    ) -> pd.Series:
        """ Compute simple or log returns based on use_log_returns flag. """
        if self.use_log_returns:
            ret = np.log(series / series.shift(1))
        else:
            ret = series.pct_change(fill_method=None)

        if fillna:
            ret = ret.fillna(0)

        suffix = "log" if self.use_log_returns else "pct"
        ret.name = self._build_indicator_name(label, suffix)
        return ret

    def _compute_cagr(self, prices: pd.Series, window: int, label: str = "cagr") -> pd.Series:
        """
        Computes rolling simple or log compounded average growth rate (CAGR) over a window, 
        respecting use_log_returns flag.

        Parameters:
        - prices: Series of prices
        - window: Lookback window in trading days
        - label: Optional name for output series

        NB: to convert log CAGR to simple CAGR, use: exp(log_cagr) - 1. 
        """
        shifted = prices.shift(window)

        if self.use_log_returns:
            log_ret = np.log(prices) - np.log(shifted)
            cagr = (log_ret / window) * self.horizon_period
            suffix = "log"
        else:
            cagr = (prices / shifted) ** (self.horizon_period / window) - 1
            suffix = "pct"

        cagr.name = self._build_indicator_name(label, suffix)
        return cagr

    def _build_indicator_name(self, base: str, *args) -> str:
        """Generates standardized names like 'sma_20' or 'macd_12_26_9'."""
        parts = [base] + [str(a).replace('.', '_') for a in args]
        return "_".join(parts)