import pandas as pd
from stockie.indicators.base import BaseIndicator

class MomentumIndicator(BaseIndicator):
    def rsi(self, window: int = 14) -> pd.Series:
        """ Calculate the Relative Strength Index (RSI) for the closing prices."""
        delta = self.df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0) # ensure 0 or positive values

        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi.name = f"rsi_{window}"
        return rsi

    def stoch(self, k_window: int = 14, d_window: int = 3) -> pd.DataFrame:
        """ Calculate the Stochastic Oscillator %K and %D values."""
        low_min = self.df["low"].rolling(window=k_window).min()
        high_max = self.df["high"].rolling(window=k_window).max()
        close = self.df["close"]

        percent_k = 100 * ((close - low_min) / (high_max - low_min))
        percent_d = percent_k.rolling(window=d_window).mean()

        prefix = f"stoch_{k_window}_{d_window}"
        return pd.DataFrame({
            f"{prefix}_k": percent_k,
            f"{prefix}_d": percent_d
        })

    def cci(self, window: int = 20) -> pd.Series:
        """ Calculate the Commodity Channel Index (CCI) for the closing prices."""
        tp = (self.df["high"] + self.df["low"] + self.df["close"]) / 3                        # typical price
        ma = tp.rolling(window=window).mean()                                                 # simple moving average of typical price
        md = tp.rolling(window=window).apply(lambda x: (abs(x - x.mean())).mean(), raw=False) # mean deviation
        cci = (tp - ma) / (0.015 * md)
        cci.name = f"cci_{window}"
        return cci

    def momentum(self, window: int = 10) -> pd.Series:
        """ Calculate the Momentum indicator for the closing prices."""
        mom = self.df["close"] - self.df["close"].shift(window)
        mom.name = f"momentum_{window}"
        return mom