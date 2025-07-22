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
            0.012379, 0.012336, 0.007429, 0.001286, 0.005987, 0.005883, 0.002725, 0.000162, 0.003112, -0.000061, 
        ], index=tsla_df.index, name="alpha_5_sp500_rf")

        pd.testing.assert_series_equal(result, expected)

    def test_beta_tsla(self, tsla_df, sp500_df):
        benchmark = sp500_df["close"]
        benchmark.name = "sp500"
        ind = RiskIndicators(tsla_df)
        result = ind.beta(benchmark=benchmark, window=5).round(6)

        expected_beta = pd.Series([
            None,      None,      None,     None,     None, 
            -0.749694, -0.776098, 0.219774, 1.095764, 1.425463, 1.409894, 1.531128, 1.925292, 1.603589, 1.614775, 
        ], index=tsla_df.index, name="beta_5_sp500")

        expected_cov = pd.Series([
            None,     None,     None,     None,     None, 
            -0.000058, -0.000060, 0.000025, 0.000082, 0.000107, 0.000105, 0.000100, 0.000053, 0.000044, 0.000044,
        ], index=tsla_df.index, name="beta_5_sp500_cov")

        expected_var = pd.Series([
            None,     None,     None,     None,     None, 
            0.000078, 0.000077, 0.000114, 0.000075, 0.000075, 0.000075, 0.000065, 0.000028, 0.000027, 0.000027,
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
            1007.613100, 1017.334671, 1027.053079, 1036.768324, 1046.480406, 
        ], index=aapl_df.index, name="sharpe_5_rf")

        pd.testing.assert_series_equal(result, expected)

    def test_sortino_tsla(self, tsla_df):
        ind = RiskIndicators(tsla_df)
        result = ind.sortino(window=2, target_return=0.0).round(6)

        expected_index = [
            pd.to_datetime('2024-01-03'), pd.to_datetime('2024-01-05'), pd.to_datetime('2024-01-08'), pd.to_datetime('2024-01-12')
        ]
        expected = pd.Series([
            None, 8.211251, 8.123382, 8.077411, 
        ], index=expected_index, name="sortino_ratio_2_target")

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