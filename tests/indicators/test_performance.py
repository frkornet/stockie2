import pytest
import pandas as pd
import numpy as np
from stockie.indicators import PerformanceIndicators
from tests.indicators import tsla_df

class TestPerformanceIndicators:
    def test_daily_return_expected_values(self, tsla_df):
        ind = PerformanceIndicators(tsla_df)
        result = ind.daily_return().round(6)

        expected = pd.Series([
            np.nan,   0.020000, -0.009804,  0.019802, -0.009709, 0.019608, 0.019231, -0.009434,
            0.019048, 0.009346,  0.018519, -0.009091,  0.018349, 0.009009, 0.008929, 
        ], index=tsla_df.index, name="daily_ret_pct")

        pd.testing.assert_series_equal(result, expected)

    def test_daily_return_log_expected_values(self, tsla_df):
        ind = PerformanceIndicators(tsla_df, use_log_returns=True)
        result = ind.daily_return().round(6)

        expected = pd.Series([
            np.nan,   0.019803, -0.009852,  0.019608, -0.009756, 0.019418, 0.019048, -0.009479,
            0.018868, 0.009302,  0.018349, -0.009132,  0.018182, 0.008969, 0.008889,
        ], index=tsla_df.index, name="daily_ret_log")

        pd.testing.assert_series_equal(result, expected)

    def test_cum_return_expected_values(self, tsla_df):
        ind = PerformanceIndicators(tsla_df)
        result = ind.cum_return().round(6)

        expected = pd.Series([
            0.000000, 0.020000, 0.010000, 0.030000, 0.020000, 0.040000, 0.060000, 0.050000,
            0.070000, 0.080000, 0.100000, 0.090000, 0.110000, 0.120000, 0.130000,
        ], index=tsla_df.index, name="cum_ret_pct")

        pd.testing.assert_series_equal(result, expected)

    def test_cum_return_log_expected_values(self, tsla_df):
        ind = PerformanceIndicators(tsla_df, use_log_returns=True)
        result = ind.cum_return().round(6)

        expected = pd.Series([
            0.000000, 0.020000, 0.010000, 0.030000, 0.020000, 0.040000, 0.060000, 0.050000,
            0.070000, 0.080000, 0.100000, 0.090000, 0.110000, 0.120000, 0.130000,
        ], index=tsla_df.index, name="cum_ret_log")

        pd.testing.assert_series_equal(result, expected)

    def test_drawdown_duration_expected(self, tsla_df):
        ind = PerformanceIndicators(tsla_df)
        result = ind.drawdown_duration()

        expected = pd.Series([
            0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0
        ], index=tsla_df.index, name="dd_duration")

        pd.testing.assert_series_equal(result, expected)
