from stockie.indicators.base import BaseIndicator
from stockie.indicators.volatility import VolatilityIndicator
import pandas as pd

class TrendIndicator(BaseIndicator):
    def sma(self, window: int) -> pd.Series:
        result = self.df["close"].rolling(window=window).mean()
        result.name = f"sma_{window}"
        return result

    def ema(self, window: int) -> pd.Series:
        result = self.df["close"].ewm(span=window, adjust=False).mean()
        result.name = f"ema_{window}"
        return result

    def macd(self, fast_window=12, slow_window=26, signal_window=9) -> pd.DataFrame:
        fast = self.df["close"].ewm(span=fast_window, adjust=False).mean()
        slow = self.df["close"].ewm(span=slow_window, adjust=False).mean()
        macd_line = fast - slow
        signal = macd_line.ewm(span=signal_window, adjust=False).mean()
        hist = macd_line - signal

        prefix = f"macd_{fast_window}_{slow_window}_{signal_window}"

        return pd.DataFrame({
            f"{prefix}_line": macd_line,
            f"{prefix}_signal": signal,
            f"{prefix}_hist": hist
        })
    
    def adx(self, window: int = 14) -> pd.DataFrame:
        """
        Average Directional Index (ADX) along with +DI and -DI.
        Measures trend strength, not direction.
        """
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]

        # Calculate components
        up_move = high.diff()
        down_move = low.diff().abs()

        plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
        minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move

        tr = VolatilityIndicator(self.df).tr()  # Use the existing True Range method

        smoothed_tr = tr.rolling(window=window).sum()
        smoothed_plus_dm = plus_dm.rolling(window=window).sum()
        smoothed_minus_dm = minus_dm.rolling(window=window).sum()

        plus_di = 100 * smoothed_plus_dm / smoothed_tr
        minus_di = 100 * smoothed_minus_dm / smoothed_tr
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1)
        adx = dx.rolling(window=window).mean()

        prefix = f"adx_{window}"
        return pd.DataFrame({
            f"{prefix}": adx,
            f"{prefix}_+di": plus_di,
            f"{prefix}_-di": minus_di
        })