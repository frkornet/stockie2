from stockie.indicators import BaseIndicators
from stockie.indicators import VolatilityIndicators
import pandas as pd
import numpy as np

class TrendIndicators(BaseIndicators):

    def __init__(self, df: pd.DataFrame) -> None:
        super().__init__(df)

    def sma(self, window: int) -> pd.Series:
        """
        Calculate Simple Moving Average (SMA) for the 'close' price.

        See: https://www.investopedia.com/terms/s/sma.asp for a description of SMA
        and how to calculate it.
        """
        result = self.df["close"].rolling(window=window, min_periods=1).mean()
        result.name = self._build_indicator_name("sma", window) 
        return result

    def ema(self, window: int) -> pd.Series:
        """
        Calculate Exponential Moving Average (EMA) for the 'close' price.

        See: https://www.investopedia.com/terms/e/ema.asp for a description of EMA
        and how to calculate it.
        """
        result = self.df["close"].ewm(span=window, adjust=False).mean()
        result.name = self._build_indicator_name("ema", window)
        return result

    def macd(self, fast_window: int=12, slow_window: int=26, signal_window:int =9) -> pd.DataFrame:
        """
        Calculate the Moving Average Convergence Divergence (MACD) indicator.
        
        See: https://www.investopedia.com/terms/m/macd.asp for a description of MACD
        and how to calculate it.
        """
        fast = self.df["close"].ewm(span=fast_window, adjust=False).mean()
        slow = self.df["close"].ewm(span=slow_window, adjust=False).mean()
        macd_line = fast - slow
        signal = macd_line.ewm(span=signal_window, adjust=False).mean()
        hist = macd_line - signal

        prefix = self._build_indicator_name("macd", fast_window, slow_window, signal_window)

        return pd.DataFrame({
            f"{prefix}_line": macd_line,
            f"{prefix}_signal": signal,
            f"{prefix}_hist": hist
        })
    
    def adx(self, window: int = 14) -> pd.DataFrame:
        """Average Directional Index (ADX), plus +DI and -DI using Wilder's method.
        
        See: https://tradingtuitions.com/adx-trend-strength-indicator for a description of ADX
        and how to calculate it.
        """

        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]

        # Calculate directional movements
        up_move = high.diff()
        down_move = -low.diff() # same as low.shift(1) - low

        # Calclulate +DM and -DM and make sure the first row is NaN
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
        plus_dm.iloc[0]=np.nan
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
        minus_dm.iloc[0]=np.nan

        # True Range via VolatilityIndicator
        tr = VolatilityIndicators(self.df).tr()

        # Wilder's smoothing (initial sum, then smoothed average)
        atr = tr.rolling(window=window).sum()
        plus_dm_smooth = plus_dm.rolling(window=window).sum()
        minus_dm_smooth = minus_dm.rolling(window=window).sum()

        plus_di = 100 * (plus_dm_smooth / atr).replace([np.nan, float("inf")], 0.0)
        minus_di = 100 * (minus_dm_smooth / atr).replace([np.nan, float("inf")], 0.0)

        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        adx = dx.rolling(window=window).mean()

        prefix = self._build_indicator_name('adx', window) 
        return pd.DataFrame({
            prefix          : adx,
            prefix + '_+di' : plus_di,
            prefix + '_-di' : minus_di
        })