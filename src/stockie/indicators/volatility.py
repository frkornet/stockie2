import pandas as pd
from stockie.indicators.base import BaseIndicator

class VolatilityIndicator(BaseIndicator):
    def bollinger(self, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
        """ Calculate Bollinger Bands for the closing prices."""
        close = self.df["close"]
        ma = close.rolling(window=window).mean()
        std = close.rolling(window=window).std()

        upper = ma + num_std * std
        lower = ma - num_std * std

        prefix = f"bollinger_{window}_{int(num_std * 10)}"
        return pd.DataFrame({
            f"{prefix}_mid": ma,
            f"{prefix}_upper": upper,
            f"{prefix}_lower": lower
        })

    def atr(self, window: int = 14) -> pd.Series:
        """ Calculate the Average True Range (ATR) for the price data."""
        tr = self.tr()
        atr = tr.rolling(window=window).mean()
        atr.name = f"atr_{window}"
        return atr

    def stddev(self, window: int = 20) -> pd.Series:
        """ Calculate the standard deviation of the closing prices."""
        std = self.df["close"].rolling(window=window).std()
        std.name = f"stddev_{window}"
        return std

    def tr(self) -> pd.Series:
        """ Calculate the True Range (TR) for the price data."""
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        prev_close = close.shift(1)

        tr = pd.concat([
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)

        tr.name = "tr"
        return tr