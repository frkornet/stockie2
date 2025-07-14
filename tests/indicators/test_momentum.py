import pytest
import pandas as pd
import numpy as np
from stockie.indicators.momentum import MomentumIndicators
from tests.indicators import aapl_df, tsla_df

class TestMomentumIndicators:
    def test_rsi(self, tsla_df):
        ind = MomentumIndicators(tsla_df)
        rsi = ind.rsi(window=5).round(6)

        # expected RSI values calculated in spreadsheet, rsi_5_tsla worksheet
        expected = pd.Series([
            np.nan,    100.000000, 88.888889, 91.304348, 80.382775, 84.898711, 88.273150, 77.455786, 82.742732,
            84.948809,  88.594011, 76.946815, 82.649398, 84.972681, 87.127286,
        ], index=tsla_df.index, name="rsi_5")

        pd.testing.assert_series_equal(rsi, expected)

    def test_stochastic_kd(self, tsla_df):
        ind = MomentumIndicators(tsla_df)
        stoch = ind.stoch(k_window=5, d_window=3).round(6)

        # expected %K and %D values calculated in spreadsheet, stoch_5_3_tsla worksheet
        expected_k = pd.Series([
            np.nan,     np.nan,     np.nan,     np.nan,    60.000000, 80.000000, 85.714286, 66.666667,
            85.714286,  83.333333,  85.714286,  71.428571, 83.333333, 83.333333, 83.333333,
        ], index=tsla_df.index, name="stoch_5_3_k")

        expected_d =  pd.Series([
            np.nan,     np.nan,     np.nan,     np.nan,    np.nan,     np.nan,    75.238095, 77.460317,
            79.365079,  78.571429,  84.920635,  80.158730, 80.158730,  79.365079, 83.333333,
        ],  index=tsla_df.index, name="stoch_5_3_d")
        
        expected_df = pd.DataFrame({
            "stoch_5_3_k": expected_k,
            "stoch_5_3_d": expected_d
        })

        pd.testing.assert_frame_equal(stoch, expected_df)

    def test_cci(self, tsla_df):
        ind = MomentumIndicators(tsla_df)
        cci = ind.cci(window=5).round(6)

        # expected CCI values calculated in spreadsheet, cci_5_tsla worksheet
        expected = pd.Series([
            np.nan,     np.nan,     np.nan,     np.nan,     30.303030, 121.212121, 129.629630,  55.555556, 
            101.851852, 111.111111, 129.629630, 55.555556, 111.111111, 111.111111, 111.111111
        ], index=tsla_df.index, name="cci_5")

        pd.testing.assert_series_equal(cci, expected)

    def test_momentum(self, tsla_df):
        ind = MomentumIndicators(tsla_df)
        mom = ind.momentum(window=4).round(6)

        expected = pd.Series([
             np.nan, np.nan,   np.nan,   np.nan,   2.000000, 2.000000, 5.000000, 2.000000, 
            5.00000, 4.000000, 4.000000, 4.000000, 4.000000, 4.000000, 3.000000,
        ], index=tsla_df.index, name="momentum_4")

        pd.testing.assert_series_equal(mom, expected)