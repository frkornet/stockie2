import pandas as pd

class BaseIndicators:
    def __init__(self, df: pd.DataFrame, horizon_period: int = 252):
        """
        Initialize with a price DataFrame. Calls set_data()
        to validate and assign the time series.
        """
        self.set_data(df)
        if not isinstance(horizon_period, int) or horizon_period <= 0:
            raise ValueError("Horizon period must be a positive integer.")
        self.horizon_period = horizon_period

    def set_data(self, df: pd.DataFrame):
        """
        Validates and stores the price DataFrame for indicator calculations.
        Required columns: at least 'close'. Assumes 'date' is index or column.
        """
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
        """
        Normalizes scalar, Series, or DataFrame into a Series aligned to index.

        Parameters:
        - obj: input data (scalar, Series, or DataFrame)
        - index: target index for reindexing
        - dailyize: if True, divides scalar values by 252
        - label: a string label used in error messages for clarity
        """
        if isinstance(obj, pd.DataFrame):
            if "close" not in obj.columns:
                raise ValueError(f"{label} DataFrame must contain a 'close' column.")
            series = obj["close"].reindex(index).ffill()
        elif isinstance(obj, pd.Series):
            series = obj.reindex(index).ffill()
        elif isinstance(obj, (int, float)):
            value = ( (1 + obj) ** (1 / 252)) - 1.0 if dailyize else obj
            series = pd.Series(value, index=index)
        else:
            raise TypeError(f"{label} must be a Series, DataFrame, or scalar.")

        return series
       
    def _build_indicator_name(self, base: str, *args) -> str:
        """Generates standardized names like 'sma_20' or 'macd_12_26_9'."""
        parts = [base] + [str(a).replace('.', '_') for a in args]
        return "_".join(parts)