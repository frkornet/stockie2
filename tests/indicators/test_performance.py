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
        ], index=tsla_df.index, name="daily_ret")

        pd.testing.assert_series_equal(result, expected)

    def test_cum_return_expected_values(self, tsla_df):
        ind = PerformanceIndicators(tsla_df)
        result = ind.cum_return().round(6)

        expected = pd.Series([
            0.000000, 0.020000, 0.010000, 0.030000, 0.020000, 0.040000, 0.060000, 0.050000,
            0.070000, 0.080000, 0.100000, 0.090000, 0.110000, 0.120000, 0.130000,
        ], index=tsla_df.index, name="cum_ret")

        pd.testing.assert_series_equal(result, expected)

    def test_drawdown_duration_expected(self, tsla_df):
        ind = PerformanceIndicators(tsla_df)
        result = ind.drawdown_duration()

        expected = pd.Series([
            0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0
        ], index=tsla_df.index, name="dd_duration")

        pd.testing.assert_series_equal(result, expected)

    def test_volatility_annualized_expected(self, tsla_df):
        ind = PerformanceIndicators(tsla_df)
        result = ind.volatility_annualized(window=5).round(6)

        expected = pd.Series([
            np.nan,   np.nan,   np.nan,   np.nan,   np.nan,   0.257026, 0.254808, 0.253203, 
            0.251017, 0.198482, 0.195833, 0.225000, 0.191385, 0.178393, 0.178400,
        ], index=tsla_df.index, name="volatility_ann_5")

        pd.testing.assert_series_equal(result, expected)