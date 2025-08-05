import pandas as pd
import numpy as np
from stockie.indicators import BaseIndicators

class RiskIndicators(BaseIndicators):
    days_per_year = 252

    def __init__(self, df: pd.DataFrame, horizon_period: int = days_per_year):
        super().__init__(df, horizon_period=horizon_period)
        
    def alpha(
        self,
        window: int = 63,
        benchmark: pd.Series | pd.DataFrame = None,
        risk_free_benchmark: pd.Series | pd.DataFrame | float = 0.0
    ) -> pd.Series:
        """
        Computes rolling Jensen's Alpha using CAPM.

        Parameters:
        - benchmark: Series or DataFrame; must include 'close' if DataFrame
        - risk_free_benchmark: Series, DataFrame, or scalar; target rate of return
        """
        # Normalize benchmark and returns
        full_benchmark = benchmark if isinstance(benchmark, pd.DataFrame) else benchmark.to_frame(name="close")
        full_benchmark.name = getattr(benchmark, "name", "benchmark")

        benchmark_returns = self._compute_returns(
            self._normalize_series_input(obj=full_benchmark, index=self.df.index, dailyize=False, label="benchmark"),
            label="benchmark_ret"
        )

        asset_returns = self._compute_returns(self.df["close"], label="asset_ret")

        # Align inputs
        aligned = pd.concat([asset_returns, benchmark_returns], axis=1)
        asset_aligned = aligned.iloc[:, 0]
        bench_aligned = aligned.iloc[:, 1]

        # Normalize risk-free benchmark
        rf = self._normalize_series_input(
            obj=risk_free_benchmark, index=aligned.index, dailyize=True, label="risk_free_benchmark"
        )

        # Beta computation and alignment
        beta_series = self.beta(benchmark=full_benchmark, window=window).reindex(aligned.index)
        beta_values = beta_series.iloc[:, 0] if isinstance(beta_series, pd.DataFrame) else beta_series

        # CAPM logic
        mean_asset = asset_aligned.rolling(window).mean()
        mean_bench = bench_aligned.rolling(window).mean()
        mean_rf = rf.rolling(window).mean()

        expected = mean_rf + beta_values * (mean_bench - mean_rf)
        alpha_series = mean_asset - expected

        # Output label
        bench_name = getattr(benchmark, "name", "benchmark")
        rf_name = getattr(risk_free_benchmark, "name", "rf")
        alpha_series.name = self._build_indicator_name("alpha", window, bench_name, rf_name)

        return alpha_series

    def beta(
        self,
        benchmark: pd.Series | pd.DataFrame,
        window: int = 63
    ) -> pd.DataFrame:
        """
        Computes rolling beta of the asset vs a benchmark.

        Parameters:
        - benchmark: Series or DataFrame with 'close' column; must be named
        - window: rolling lookback window in trading days
        """
        full_benchmark = benchmark if isinstance(benchmark, pd.DataFrame) else benchmark.to_frame(name="close")
        full_benchmark.name = getattr(benchmark, "name", "benchmark")

        benchmark_returns = self._compute_returns(
            self._normalize_series_input(obj=full_benchmark, index=self.df.index, dailyize=False, label="benchmark"),
            label="benchmark_ret"
        )

        asset_returns = self._compute_returns(self.df["close"], label="asset_ret")

        # Align series
        assert isinstance(asset_returns, pd.Series) and isinstance(benchmark_returns, pd.Series), \
            'Both asset and benchmark must be type Series.'
        aligned = pd.concat([asset_returns, benchmark_returns], axis=1)
        asset_aligned = aligned.iloc[:, 0]
        bench_aligned = aligned.iloc[:, 1]

        # Rolling beta = covariance / variance
        cov = asset_aligned.rolling(window=window).cov(bench_aligned)
        var = bench_aligned.rolling(window=window).var()
        beta_series = cov / var.replace(0, pd.NA)

        prefix = self._build_indicator_name("beta", window, full_benchmark.name)
        return pd.DataFrame({
            f"{prefix}": beta_series,
            f"{prefix}_cov": cov,
            f"{prefix}_var": var
        })
    
    def rolling_volatility(self, window: int = 21) -> pd.Series:
        """
        Annualized rolling standard deviation of returns.
        
        NB: currently this only uses simple returns. Longer term we need to
        support log returns as well.
        """
        returns = self._compute_returns(self.df["close"], label="volatility_ret")
        vol = returns.rolling(window=window).std() * (self.horizon_period ** 0.5)
        vol.name = self._build_indicator_name("rolling_volatility", window)
        return vol

    def downside_deviation(self, window: int = 21, threshold: float = 0.0) -> pd.Series:
        """
        Downside deviation (semi-deviation) of returns below threshold (e.g., 0)
        
        NB: rows above threshold are filtered out during calculation. As a result, the
        output is a subset of the input index. Only rows that are below the threshold
        will be returned  The first window-1 rows will be np.nan / None.
        """
        returns = self._compute_returns(self.df["close"], label="dd_ret")
        downside = (returns[returns < threshold] - threshold) ** 2
        dd = (downside.rolling(window=window).mean() * self.horizon_period) ** 0.5 
        dd.name = self._build_indicator_name("downside_deviation", window)
        return dd

    def sharpe(
        self,
        window: int = 21,
        risk_free_rate: float | pd.Series | pd.DataFrame = 0.01
    ) -> pd.Series:
        """
        Computes the annualized Sharpe ratio over a rolling window.

        Parameters:
        - window: Lookback window in trading days
        - risk_free_rate: scalar, Series, or DataFrame with 'close' column
        """
        returns = self._compute_returns(self.df["close"], label="sharpe_ret")
        rf = self._normalize_series_input(
            obj=risk_free_rate, index=returns.index, dailyize=True, label="risk_free_rate"
        )

        excess = returns - rf
        mean_excess = excess.rolling(window).mean()
        std_excess = excess.rolling(window).std()
        sharpe = (mean_excess / std_excess) * (self.horizon_period ** 0.5)

        rf_name = getattr(risk_free_rate, "name", "rf")
        sharpe.name = self._build_indicator_name("sharpe", window, rf_name)

        return sharpe

    def sortino(
        self,
        window: int = 21,
        target_return: float | pd.Series | pd.DataFrame = 0.0
    ) -> pd.Series:
        """
        Rolling Sortino Ratio using excess returns and full-index downside deviation
        
        NB: the correct way to annualize mean_excess is to calculate it as follows:
        mean_excess = (1 + excess_return.rolling(window).mean()) ** self.horizon_period - 1

        However, doing so would increase the mean_excess and it is better to be conservative.
        This is also, how others are typically calculating the Sortino ratio.
        """
        returns = self._compute_returns(self.df["close"], label="sortino_ret")
        target = self._normalize_series_input(
            obj=target_return, index=returns.index, dailyize=True, label="target_return"
        )

        excess_return = returns - target
        mean_excess = excess_return.rolling(window).mean() * self.horizon_period
        semi_dev = self.downside_deviation(window=window, threshold=target_return)

        sortino_ratio = mean_excess[semi_dev.index] / semi_dev.replace(0, pd.NA)
        sortino_ratio.name = self._build_indicator_name("sortino_ratio", window, getattr(target_return, "name", "target"))
        return sortino_ratio

    def max_drawdown(self, window: int = days_per_year) -> pd.Series:
        """Rolling maximum drawdown over a lookback window"""
        roll_max = self.df["close"].rolling(window=window, min_periods=1).max()
        drawdown = self.df["close"] / roll_max - 1
        mdd = drawdown.rolling(window=window, min_periods=1).min()
        mdd.name = self._build_indicator_name("mdd", window)
        return mdd

    def calmar(self, window: int = days_per_year) -> pd.Series:
        """Calmar ratio = CAGR / |Max Drawdown| (log-aware version)"""
        prices = self.df["close"]
        cagr = self._compute_cagr(prices, window, label="cagr")
        mdd = self.max_drawdown(window=window).abs()
        calmar = cagr / mdd.replace(0, np.nan)
        calmar.name = self._build_indicator_name("calmar", window)
        return calmar