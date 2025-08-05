import pandas as pd
import numpy as np
from stockie.indicators import BaseIndicators

class PerformanceIndicators(BaseIndicators):
    def __init__(self, df: pd.DataFrame, horizon_period: int = 252, use_log_returns: bool = False):
        super().__init__(df, horizon_period=horizon_period, use_log_returns=use_log_returns)

    def daily_return(self) -> pd.Series:
        """Daily returns using configured return method (simple or log)."""
        return self._compute_returns(self.df["close"], label="daily_ret")

    def cum_return(self) -> pd.Series:
        """Cumulative returns over time."""
        daily = self._compute_returns(self.df["close"], fillna=True, label="cum_ret")

        if self.use_log_returns:
            # Cumulative log return: exp(sum) - 1
            cum = np.exp(daily.cumsum()) - 1
        else:
            # Cumulative simple return: product of (1 + r) - 1
            cum = (1 + daily).cumprod() - 1

        cum.name = daily.name  # Already includes suffix
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