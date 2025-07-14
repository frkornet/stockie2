import pandas as pd
from stockie.indicators import BaseIndicators

class MomentumIndicators(BaseIndicators):
    def __init__(self, df: pd.DataFrame):
        super().__init__(df)

    def rsi(self, window: int = 14) -> pd.Series:
        """
        Calculate RSI using Wilder's smoothing method.

        See: https://howtoexcel.net/2023/05/how-to-calculate-rsi-in-excel.html for a description of RSI
        and how to calculate it.
        """
        delta = self.df["close"].diff()
        gain = delta.clip(lower=0)
        loss = delta.clip(upper=0).abs()  # convert losses to positive values

        # Wilder's smoothing uses alpha=1/window and adjust=False
        avg_gain = gain.ewm(alpha=1/window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/window, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi.name = self._build_indicator_name("rsi", window)
        return rsi

    def stoch(self, k_window: int = 14, d_window: int = 3) -> pd.DataFrame:
        """ 
        Calculate the Stochastic Oscillator %K and %D values.

        See: https://investexcel.net/how-to-calculate-the-stochastic-oscillator/ for a description of 
        Stochastic Oscillator and how to calculate it.
        """
        low_min = self.df["low"].rolling(window=k_window).min()
        high_max = self.df["high"].rolling(window=k_window).max()
        close = self.df["close"]

        percent_k = 100 * ((close - low_min) / (high_max - low_min))
        percent_d = percent_k.rolling(window=d_window).mean()

        prefix = self._build_indicator_name("stoch", k_window, d_window)
        return pd.DataFrame({
            f"{prefix}_k": percent_k,
            f"{prefix}_d": percent_d
        })

    def cci(self, window: int = 20) -> pd.Series:
        """
        Calculate the Commodity Channel Index (CCI) for the closing prices.

        See: https://www.exfinsis.com/tutorials/microsoft-excel/cci-stock-technical-indicator-with-excel/ for a description of CCI
        and how to calculate it.
        """
        tp = (self.df["high"] + self.df["low"] + self.df["close"]) / 3                        # typical price
        ma = tp.rolling(window=window).mean()                                                 # simple moving average of typical price
        md = tp.rolling(window=window).apply(lambda x: (abs(x - x.mean())).mean(), raw=False) # mean deviation
        cci = (tp - ma) / (0.015 * md)
        cci.name = self._build_indicator_name("cci", window)
        return cci

    def momentum(self, window: int = 10) -> pd.Series:
        """
        Calculate the Momentum indicator for the closing prices.
        
        Please note: There is an inconsistency with how this indicator behaves versus other indicators. Normally, with a 
        window argument there will be window-1 number of NaN values at the start of the series. In momentum's case
        there will be window number of NaN values at the start of the series. I left this behavior as is to maintain
        compatibility with how other open-source libraries calculate momentum.

        See: https://www.investopedia.com/terms/m/momentum.asp for a description of Momentum and how to calculate it.
        """
        mom = self.df["close"] - self.df["close"].shift(window)
        mom.name = self._build_indicator_name("momentum", window)
        return mom