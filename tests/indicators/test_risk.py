import pytest
import pandas as pd
from stockie.indicators.risk import RiskIndicators
from tests.indicators import aapl_df, tsla_df, sp500_df

class TestRiskIndicators:

    def test_alpha_tsla(self, tsla_df, sp500_df):
        benchmark = sp500_df["close"]
        benchmark.name = "sp500"
        ind = RiskIndicators(tsla_df)
        result = ind.alpha(window=5, benchmark=benchmark, risk_free_benchmark=0.01).round(6)

        expected = pd.Series([
            None,     None,     None,     None,     None, 
            0.012378, 0.012336, 0.007429, 0.001286, 0.005987, 0.005883, 0.002725, 0.000163, 0.003112, -0.000061, 
        ], index=tsla_df.index, name="alpha_5_sp500_rf")

        pd.testing.assert_series_equal(result, expected)

    def test_beta_tsla(self, tsla_df):
        benchmark = tsla_df["close"] + 1.0
        benchmark.name = "sp500"
        ind = RiskIndicators(tsla_df)
        result = ind.beta(benchmark=benchmark, window=5).round(6)

        expected_beta = pd.Series([
            None,     None,     None,     None,     None, 
            1.009855, 1.009770, 1.009711, 1.009626, 1.009593, 1.009465, 1.009350, 1.009252, 1.009177, 1.009177, 
        ], index=tsla_df.index, name="beta_5_sp500")

        expected_cov = pd.Series([
            None,     None,     None,     None,     None, 
            0.000260, 0.000255, 0.000252, 0.000248, 0.000155, 0.000151, 0.000199, 0.000144, 0.000125, 0.000125, 
        ], index=tsla_df.index, name="beta_5_sp500_cov")

        expected_var = pd.Series([
            None,     None,     None,     None,     None, 
            0.000257, 0.000253, 0.000250, 0.000245, 0.000153, 0.000149, 0.000197, 0.000143, 0.000124, 0.000124, 
        ], index=tsla_df.index, name="beta_5_sp500_var") 

        pd.testing.assert_series_equal(result["beta_5_sp500"], expected_beta)
        pd.testing.assert_series_equal(result["beta_5_sp500_cov"], expected_cov)
        pd.testing.assert_series_equal(result["beta_5_sp500_var"], expected_var)

    def test_rolling_volatility_aapl(self, aapl_df):
        ind = RiskIndicators(aapl_df)
        result = ind.rolling_volatility(window=5).round(6)

        expected = pd.Series([
            None,     None,     None,     None,     None, 
            0.002413, 0.002367, 0.002321, 0.002277, 0.002235
        ], index=aapl_df.index, name="rolling_volatility_5")

        pd.testing.assert_series_equal(result, expected)

    def test_downside_deviation_tsla(self, tsla_df):
        ind = RiskIndicators(tsla_df)
        result = ind.downside_deviation(window=2).round(6)

        index = [pd.to_datetime('2024-01-03'), pd.to_datetime('2024-01-05'), pd.to_datetime('2024-01-08'), pd.to_datetime('2024-01-12')]
        expected = pd.Series([
            None, 0.154879, 0.151956, 0.147062, 
        ], index=index, name="downside_deviation_2")

        pd.testing.assert_series_equal(result, expected)

    def test_sharpe_aapl(self, aapl_df):
        ind = RiskIndicators(aapl_df)
        result = ind.sharpe(window=5, risk_free_rate=0.04).round(6)

        expected = pd.Series([
            None,        None,        None,        None,        None,
            1007.291473, 1017.006705, 1026.718711, 1036.427492, 1046.13305 
        ], index=aapl_df.index, name="sharpe_5_rf")

        pd.testing.assert_series_equal(result, expected)

    def test_sortino_tsla(self, tsla_df):
        ind = RiskIndicators(tsla_df)
        result = ind.sortino(window=5, target_return=0.0).round(6)

        expected = pd.Series([
            None,       None,      None,      None,      None,
            20.528190, 20.132400, 20.713632, 20.318027, 43.494508, 42.674764, 15.382291, 43.864143, 36.024766, 35.698947, 
        ], index=tsla_df.index, name="sortino_ratio_5_target")

        pd.testing.assert_series_equal(result, expected)

    def test_max_drawdown_tsla(self, tsla_df):
        ind = RiskIndicators(tsla_df)
        result = ind.max_drawdown(window=5).round(6)

        expected = pd.Series([
             0.000000,  0.000000, -0.009804, -0.009804, -0.009804, -0.009804, -0.009804, -0.009709,
            -0.009709, -0.009434, -0.009434, -0.009434, -0.009091, -0.009091, -0.009091,
        ], index=tsla_df.index, name="mdd_5")

        pd.testing.assert_series_equal(result, expected)

    def test_calmar_tsla(self, tsla_df):
        ind = RiskIndicators(tsla_df)
        result = ind.calmar(window=5).round(6)

        expected = pd.Series([
            None, None, None, None, None,
            634.343525, 606.870861, 626.425025, 599.721911, 1783.794084, 1684.67552, 326.698861, 1700.214932, 989.103605, 966.43785, 
        ], index=tsla_df.index, name="calmar_5")

        pd.testing.assert_series_equal(result, expected)