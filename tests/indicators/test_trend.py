import pytest
import pandas as pd
import numpy as np
from   stockie.indicators import TrendIndicators 
from   tests.indicators import aapl_df, tsla_df

class TestTrendIndicators:

    def test_sma_5_aapl(self, aapl_df):
        ind = TrendIndicators(aapl_df)
        result = ind.sma(5)
        expected = pd.Series(
            [100.0, 100.5, 101.0, 101.5, 102.0,
             103.0, 104.0, 105.0, 106.0, 107.0],
            index=aapl_df.index,
            name="sma_5"
        )
        pd.testing.assert_series_equal(result, expected)

    def test_ema_3_aapl(self, aapl_df):
        ind = TrendIndicators(aapl_df)
        result = ind.ema(3)
        expected = pd.Series(
            [100.0, 100.5, 101.25, 102.125, 103.0625,
             104.03125, 105.015625, 106.0078125, 107.00390625, 108.001953125],
            index=aapl_df.index,
            name="ema_3"
        )
        pd.testing.assert_series_equal(result, expected)

    def test_macd_12_26_9_tsla(self, tsla_df):
        ind = TrendIndicators(tsla_df)
        df = ind.macd()
        macd = df["macd_12_26_9_line"]
        signal = df["macd_12_26_9_signal"]
        hist = df["macd_12_26_9_hist"]

        # NB: Hard-coded values calculated manually using Excel using MACD formula
        expected_macd = pd.Series([
            0.00000000, 0.15954416, 0.20295290, 0.39419390, 0.45976228,
            0.66543821, 0.97854115, 1.13292617, 1.40051641, 1.67397867,
            2.02869720, 2.20371945, 2.47527569, 2.73959724, 2.99523837
        ], index=tsla_df.index, name="macd_12_26_9_line")

        expected_signal = pd.Series([
            0.00000000, 0.03190883, 0.06611765, 0.13173290, 0.19733877,
            0.29095866, 0.42847516, 0.56936536, 0.73559557, 0.92327219,
            1.14435719, 1.35622964, 1.58003885, 1.81195053, 2.04860810
        ], index=tsla_df.index, name="macd_12_26_9_signal")

        expected_hist = expected_macd - expected_signal
        expected_hist.name = "macd_12_26_9_hist"

        pd.testing.assert_series_equal(macd, expected_macd, atol=1e-6)
        pd.testing.assert_series_equal(signal, expected_signal, atol=1e-6)
        pd.testing.assert_series_equal(hist, expected_hist, atol=1e-6)

    # TODO: validate unit test and adx() calculation match what I see in spreadsheet
    def test_adx_bounds_tsla(self, tsla_df):
        # Extend TSLA data to 30 rows for sufficient ADX history
        df = pd.concat([tsla_df, tsla_df], ignore_index=True)
        df.index = pd.date_range(start="2024-01-01", periods=len(df))
        ind = TrendIndicators(df)
        result = ind.adx(window=14).round(6)

        # Extract series
        adx = result["adx_14"]
        plus_di = result["adx_14_+di"]
        minus_di = result["adx_14_-di"]

        # Hardcoded expected values (see spreadsheet, adx_5_tsla worksheet)
        expected_adx = pd.Series(
            [np.nan]*27 + [8.845470006, 4.640151515, 8.615491651],
            index=df.index,
            name="adx_14"
        )
        expected_plus_di = pd.Series(
            [np.nan]*14 + [
                48.571429, 32.608696, 36.170213, 32.608696, 36.170213, 32.608696,
                32.608696, 36.170213, 32.608696, 34.042553, 32.608696, 36.170213,
                32.608696, 34.042553, 34.042553, 48.571429,
            ],
            index=df.index,
            name="adx_14_+di"
        )
        expected_minus_di = pd.Series(
            [np.nan]*14 + [
                11.428571, 36.956522, 34.042553, 36.956522, 34.042553, 36.956522,
                36.956522, 34.042553, 36.956522, 36.170213, 36.956522, 
                34.042553, 36.956522, 36.170213, 36.170213, 11.428571,
            ],
            index=df.index,
            name="adx_14_-di"
        )

        # Compare with tolerances to allow for small numerical drift
        pd.testing.assert_series_equal(adx, expected_adx, check_exact=False, atol=1e-5)
        pd.testing.assert_series_equal(plus_di, expected_plus_di, check_exact=False, atol=1e-5)
        pd.testing.assert_series_equal(minus_di, expected_minus_di, check_exact=False, atol=1e-5)