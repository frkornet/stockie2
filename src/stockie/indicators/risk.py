import pandas as pd
from stockie.indicators.base import BaseIndicator

class RiskIndicator(BaseIndicator):

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

        benchmark_returns = self._normalize_series_input(
            obj=full_benchmark, index=self.df.index, dailyize=False, label="benchmark"
        ).pct_change()

        asset_returns = self.df["close"].pct_change()

        # Align inputs
        aligned = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
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
        alpha_series.name = f"alpha_{window}_{bench_name}_{rf_name}"

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

        benchmark_returns = self._normalize_series_input(
            obj=full_benchmark,
            index=self.df.index,
            dailyize=False,
            label="benchmark"
        ).pct_change()

        asset_returns = self.df["close"].pct_change()

        # Align series
        aligned = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
        asset_aligned = aligned.iloc[:, 0]
        bench_aligned = aligned.iloc[:, 1]

        # Rolling beta = covariance / variance
        cov = asset_aligned.rolling(window=window).cov(bench_aligned)
        var = bench_aligned.rolling(window=window).var()
        beta_series = cov / var.replace(0, pd.NA)

        prefix = f"beta_{window}_{full_benchmark.name}"
        return pd.DataFrame({
            f"{prefix}": beta_series,
            f"{prefix}_cov": cov,
            f"{prefix}_var": var
        })
    
    def rolling_volatility(self, window: int = 21) -> pd.Series:
        """Annualized rolling standard deviation of returns"""
        returns = self.df["close"].pct_change()
        vol = returns.rolling(window=window).std() * (252 ** 0.5)
        vol.name = f"rolling_volatility_{window}"
        return vol

    def downside_deviation(self, window: int = 21, threshold: float = 0.0) -> pd.Series:
        """Downside deviation (semi-deviation) of returns below threshold (e.g., 0)"""
        returns = self.df["close"].pct_change()
        downside = (returns[returns < threshold] - threshold) ** 2
        dd = (downside.rolling(window=window).mean() * 252) ** 0.5 
        dd.name = f"downside_deviation_{window}"
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
        returns = self.df["close"].pct_change()
        rf = self._normalize_series_input(
            obj=risk_free_rate, index=returns.index, dailyize=True, label="risk_free_rate"
        )

        excess = returns - rf
        mean_excess = excess.rolling(window).mean()
        std_excess = excess.rolling(window).std()
        sharpe = (mean_excess / std_excess) * (252 ** 0.5)

        rf_name = getattr(risk_free_rate, "name", "rf")
        sharpe.name = f"sharpe_ratio_{window}_{rf_name}"

        return sharpe

    def sortino(
        self,
        window: int = 21,
        target_return: float | pd.Series | pd.DataFrame = 0.0
    ) -> pd.Series:
        """
        Computes the rolling Sortino Ratio.
        Measures excess return per unit of downside risk.

        Parameters:
        - window: Lookback window in trading days
        - target_return: scalar, Series, or DataFrame with 'close' column
        """
        returns = self.df["close"].pct_change()
        target = self._normalize_series_input(
            obj=target_return, index=returns.index, dailyize=True, label="target_return"
        )

        excess_return = returns - target
        downside = (returns[returns < target] - target) ** 2
        semi_dev = downside.rolling(window).mean() ** 0.5 * (252 ** 0.5)

        sortino_ratio = (excess_return.rolling(window).mean() * 252) / semi_dev.replace(0, pd.NA)
        target_name = getattr(target_return, "name", "target")
        sortino_ratio.name = f"sortino_ratio_{window}_{target_name}"

        return sortino_ratio
    
    def max_drawdown(self, window: int = 252) -> pd.Series:
        """Rolling maximum drawdown over a lookback window"""
        roll_max = self.df["close"].rolling(window=window, min_periods=1).max()
        drawdown = self.df["close"] / roll_max - 1
        mdd = drawdown.rolling(window=window, min_periods=1).min()
        mdd.name = f"mdd_{window}"
        return mdd

    def calmar_ratio(self, window: int = 252) -> pd.Series:
        """Calmar ratio = CAGR / |Max Drawdown| (approximate version using rolling returns)"""
        prices = self.df["close"]
        cagr = (prices / prices.shift(window)) ** (252 / window) - 1
        mdd = self.max_drawdown(window=window).abs()
        calmar = cagr / mdd.replace(0, pd.NA)
        calmar.name = f"calmar_ratio_{window}"
        return calmar