import pandas as pd
from stockie.indicators import BaseIndicators

class VolatilityIndicators(BaseIndicators):

    def __init__(self, df: pd.DataFrame) -> None:
        super().__init__(df)

    def bollinger(self, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
        """ Calculate Bollinger Bands for the closing prices."""
        close = self.df["close"]
        ma = close.rolling(window=window).mean()
        std = close.rolling(window=window).std()

        upper = ma + num_std * std
        lower = ma - num_std * std

        prefix = self._build_indicator_name("adx", window, int(num_std*10))
        return pd.DataFrame({
            self._build_indicator_name("adx", window, int(num_std*10), "mid"): ma,
            self._build_indicator_name("adx", window, int(num_std*10), "upper"): upper,
            self._build_indicator_name("adx", window, int(num_std*10), "lower"): lower
        })

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

        tr.name = self._build_indicator_name("tr")
        return tr
    
    def max_tr(self, window: int = 14) -> pd.Series:
        """ Calculate the maximum True Range over a rolling window."""
        tr = self.tr()
        tr_max = tr.rolling(window=window).max()
        tr_max.name = self._build_indicator_name("max_tr", window)
        return tr_max
    
    def atr(self, window: int = 14) -> pd.Series:
        """ Calculate the Average True Range (ATR) for the price data."""
        tr = self.tr()
        atr = tr.rolling(window=window).mean()
        atr.name = self._build_indicator_name("atr", window)
        return atr

    def stddev(self, window: int = 20) -> pd.Series:
        """ Calculate the standard deviation of the closing prices."""
        std = self.df["close"].rolling(window=window).std()
        std.name = self._build_indicator_name("stddev", window)
        return std
