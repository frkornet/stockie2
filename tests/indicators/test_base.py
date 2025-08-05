import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from stockie.indicators import BaseIndicators
from tests.indicators.fixtures import aapl_df, tsla_df

class TestBaseIndicators:
    def test_initialize_with_aapl(self, aapl_df):
        ind = BaseIndicators(aapl_df)
        assert "close" in ind.df.columns
        assert len(ind.df) == 10

    def test_initialize_with_tsla(self, tsla_df):
        ind = BaseIndicators(tsla_df)
        assert ind.df.index.is_monotonic_increasing
        assert ind.df["high"].iloc[0] == 101

    def test_set_data_non_dataframe_type(self):
        with pytest.raises(TypeError, match="Expected a pandas DataFrame"):
            BaseIndicators("not a dataframe")

    def test_set_data_missing_close_column(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=3),
            "open": [10, 11, 12]
        })
        with pytest.raises(ValueError, match="must contain a 'close' column"):
            BaseIndicators(df)

    def test_set_data_with_non_datetime_date_column(self):
        df = pd.DataFrame({
            "date": [1, 2, 3],  # integers not convertible to datetime
            "close": [10, 11, 12]
        })
        with pytest.raises(ValueError, match="index must be datetime"):
            BaseIndicators(df)

    def test_set_data_with_valid_date_column(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=3),
            "close": [10, 11, 12]
        })
        ind = BaseIndicators(df)
        assert pd.api.types.is_datetime64_any_dtype(ind.df.index)
        assert "close" in ind.df.columns

    def test_set_data_with_datetime_index(self):
        dates = pd.date_range("2024-01-01", periods=3)
        df = pd.DataFrame({
            "close": [10, 11, 12]
        }, index=dates)
        ind = BaseIndicators(df)
        assert ind.df.index.equals(df.sort_index().index)

    def test_normalize_scalar_with_aapl(self, aapl_df):
        ind = BaseIndicators(aapl_df)
        rate = 0.04
        out = ind._normalize_series_input((1+rate)**252, ind.df.index, dailyize=True).round(6)
        assert pytest.approx(out.iloc[0]) == rate

    def test_normalize_series_with_tsla(self, tsla_df):
        ind = BaseIndicators(tsla_df)
        input_series = tsla_df["close"]
        out = ind._normalize_series_input(input_series, ind.df.index)
        assert out.equals(input_series)

    def test_normalize_invalid_input_type(self, aapl_df):
            ind = BaseIndicators(aapl_df)

            invalid_inputs = [None, "not a series", {}, [1, 2, 3]]
            for bad_value in invalid_inputs:
                with pytest.raises(TypeError, match="must be a Series, DataFrame, or scalar"):
                    ind._normalize_series_input(bad_value, ind.df.index, label="bad_input")

    def test_compute_simple_returns(self, aapl_df):
        expected_simple = pd.Series(
            [None, 0.010000, 0.009901, 0.009804, 0.009709, 0.009615, 0.009524, 0.009434, 0.009346, 0.009259,],
            index=aapl_df.index, name="close"
        )
        expected_simple.name = "returns_pct"
        ind_simple = BaseIndicators(aapl_df, use_log_returns=False)
        actual_simple = ind_simple._compute_returns(aapl_df.close).round(6)
        pd.testing.assert_series_equal(actual_simple, expected_simple)

    def test_compute_log_returns(self, aapl_df):
        expected_log = pd.Series(
            [None, 0.009950, 0.009852, 0.009756, 0.009662, 0.009569, 0.009479, 0.009390, 0.009302, 0.009217, ],
            index=aapl_df.index, name="close"
        )
        expected_log.name = "returns_log"
        ind_log = BaseIndicators(aapl_df, use_log_returns=True)
        actual_log = ind_log._compute_returns(aapl_df.close).round(6)
        pd.testing.assert_series_equal(actual_log, expected_log)

    def test_compute_simple_cagr(self, aapl_df):
        expected_simple = pd.Series(
            [None, None, 11.123322, 10.830340, 10.549924, 10.281358, 10.023976, 9.777159, 9.540329, 9.312946, ],
            index=aapl_df.index, name="close"
        )
        expected_simple.name = "cagr_pct"
        window, horizon = 2, 252
        ind_simple = BaseIndicators(aapl_df, horizon_period=horizon, use_log_returns=False)
        actual_simple = ind_simple._compute_cagr(aapl_df.close, window).round(6)
        pd.testing.assert_series_equal(actual_simple, expected_simple)

    def test_compute_log_cagr(self, aapl_df):
        expected_log = pd.Series(
            [None, None, 2.495131, 2.470667, 2.446679, 2.423152, 2.400073, 2.377429, 2.355209, 2.333400, ],
            index=aapl_df.index, name="close"
        )
        expected_log.name = "cagr_log"
        window, horizon = 2, 252
        ind_log = BaseIndicators(aapl_df, horizon_period=horizon, use_log_returns=True)
        actual_log = ind_log._compute_cagr(aapl_df.close, window).round(6)
        pd.testing.assert_series_equal(actual_log, expected_log)

    def test_build_name_macd(self, aapl_df):
        ind = BaseIndicators(aapl_df)
        name = ind._build_indicator_name("macd", 12, 26, 9)
        assert name == "macd_12_26_9"