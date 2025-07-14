import pytest
import pandas as pd
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
        out = ind._normalize_series_input(252, ind.df.index, dailyize=True)
        assert pytest.approx(out.iloc[0]) == 1.0

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

    def test_build_name_macd(self, aapl_df):
        ind = BaseIndicators(aapl_df)
        name = ind._build_indicator_name("macd", 12, 26, 9)
        assert name == "macd_12_26_9"