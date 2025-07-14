from stockie.indicators import BaseIndicators
import pandas as pd
from typing import Union

class PerformanceIndicators(BaseIndicators):
    def __init__(self, df: pd.DataFrame):
        super().__init__(df)

    def daily_return(self) -> pd.Series:
        """Simple daily returns."""
        ret = self.df["close"].pct_change()
        ret.name = self._build_indicator_name("daily_ret")
        return ret

    def cum_return(self) -> pd.Series:
        """Cumulative return over time."""
        daily = self.df["close"].pct_change().fillna(0)
        cum = (1 + daily).cumprod() - 1
        cum.name = self._build_indicator_name("cum_ret")
        return cum

    def drawdown_duration(self) -> pd.Series:
        """
        Number of consecutive days below previous peak.
        Useful for stress-testing strategy resilience.
        """
        cum = self.cum_return() + 1
        peak = cum.cummax()
        drawdown = cum < peak
        duration = drawdown.astype(int).groupby((~drawdown).cumsum()).cumsum()
        duration.name = self._build_indicator_name("dd_duration")
        return duration

    def volatility_annualized(self, window: int = 21) -> pd.Series:
        """
        Annualized rolling volatility of returns.
        """
        returns = self.df["close"].pct_change()
        vol = returns.rolling(window).std() * (252 ** 0.5)
        vol.name = self._build_indicator_name("volatility_ann", window)
        return vol