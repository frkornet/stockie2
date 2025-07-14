import pytest
import pandas as pd
from stockie.indicators.volatility import VolatilityIndicators
from tests.indicators import tsla_df, aapl_df

class TestVolatilityIndicators:

    def test_bollinger_values_aapl(self, aapl_df):
        ind = VolatilityIndicators(aapl_df)
        window = 5
        num_std = 2.0
        result = ind.bollinger(window=window, num_std=num_std).round(6)

        expected_mid = pd.Series([
            None, None, None, None, 102.0,
            103.0, 104.0, 105.0, 106.0, 107.0
        ], index=aapl_df.index, name="adx_5_20_mid")

        expected_upper = pd.Series([
            None,       None,       None,       None, 
            105.162278, 106.162278, 107.162278, 108.162278, 109.162278, 110.162278
        ], index=aapl_df.index, name="adx_5_20_upper")

        expected_lower = pd.Series([
            None,      None,      None,       None, 
            98.837722, 99.837722, 100.837722, 101.837722, 102.837722, 103.837722,
        ], index=aapl_df.index, name="adx_5_20_lower")

        pd.testing.assert_series_equal(result["adx_5_20_mid"], expected_mid)
        pd.testing.assert_series_equal(result["adx_5_20_upper"], expected_upper)
        pd.testing.assert_series_equal(result["adx_5_20_lower"], expected_lower)

    def test_tr_values_tsla(self, tsla_df):
        ind = VolatilityIndicators(tsla_df)
        result = ind.tr().round(6)

        expected = pd.Series([
            2.0, 3.0, 2.0, 3.0, 2.0, 3.0, 3.0, 2.0,
            3.0, 2.0, 3.0, 2.0, 3.0, 2.0, 2.0
        ], index=tsla_df.index, name="tr")

        pd.testing.assert_series_equal(result, expected)

    def test_atr_values_tsla(self, tsla_df):
        ind = VolatilityIndicators(tsla_df)
        result = ind.atr(window=5).round(6)

        expected = pd.Series([
            None, None, None, None, 
            2.4,  2.6,  2.6,  2.6,  2.6, 2.6, 2.6, 2.4, 2.6, 2.4, 2.4,
        ], index=tsla_df.index, name="atr_5")

        pd.testing.assert_series_equal(result, expected)

    def test_stddev_values_tsla(self, tsla_df):
        ind = VolatilityIndicators(tsla_df)
        result = ind.stddev(window=5).round(6)

        expected = pd.Series([
            None,     None,     None,     None, 
            1.140175, 1.140175, 1.923538, 1.581139, 1.923538, 1.581139, 1.923538, 1.923538, 1.581139, 1.581139, 1.581139,             
        ], index=tsla_df.index, name="stddev_5")

        pd.testing.assert_series_equal(result, expected)
