import pytest
import pandas as pd
from stockie.indicators import VolumeIndicators
from tests.indicators import tsla_df, aapl_df

class TestVolumeIndicators:

    def test_vsma_aapl(self, aapl_df):
        ind = VolumeIndicators(aapl_df)
        result = ind.vsma(window=5).round(6)

        expected = pd.Series([
            None, None, None, None, 1020.0, 1030.0, 1040.0, 1050.0, 1060.0, 1070.0
        ], index=aapl_df.index, name="vsma_5")

        pd.testing.assert_series_equal(result, expected)

    def test_vema_aapl(self, aapl_df):
        ind = VolumeIndicators(aapl_df)
        result = ind.vema(window=5).round(6)

        expected = pd.Series([
            1000.000000, 1003.333333, 1008.888889, 1015.925926, 1023.950617, 
            1032.633745, 1041.755830, 1051.170553, 1060.780369, 1070.520246
        ], index=aapl_df.index, name="vema_5")

        pd.testing.assert_series_equal(result, expected)

    def test_pvt_tsla(self, tsla_df):
        ind = VolumeIndicators(tsla_df)
        result = ind.pvt().round(6)

        expected = pd.Series([
             0.000000,  19.000000,   9.294118,  29.492137,  18.812526,  36.459585,  55.305738,  45.588757, 
            66.541138,  76.634596,  94.690152,  85.508334, 105.875306, 115.334766, 125.424051, 
        ], index=tsla_df.index, name="pvt")

        pd.testing.assert_series_equal(result, expected)

    def test_obv_tsla(self, tsla_df):
        ind = VolumeIndicators(tsla_df)
        result = ind.obv().round(6)

        expected = pd.Series([
            0, 950, -40, 980, -120, 780, 1760, 730, 1830, 2910, 3885, 2875, 3985, 5035, 6165,
        ], index=tsla_df.index, name="obv")

        pd.testing.assert_series_equal(result, expected)

    def test_cmf_tsla(self, tsla_df):
        tsla_df['high'] = [h+i/2 for i, h in enumerate(tsla_df['high'])]
        ind = VolumeIndicators(tsla_df)
        result = ind.cmf(window=5).round(6)

        expected = pd.Series(
            [None,      None,      None,      None,      -0.297854, -0.404666, -0.481993, -0.542862, 
             -0.592326, -0.633493, -0.662325, -0.687887, -0.711018, -0.731144, -0.749085]
        , index=tsla_df.index, name="cmf_5")

        pd.testing.assert_series_equal(result, expected)