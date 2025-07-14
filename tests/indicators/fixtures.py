import pytest
import pandas as pd

@pytest.fixture
def aapl_df():
    dates = pd.date_range("2024-01-01", periods=10)
    close = pd.Series([100 + i for i in range(10)], index=dates)
    volume = pd.Series([1000 + i*10 for i in range(10)], index=dates)
    df = pd.DataFrame({
        "close": close,
        "high": close + 1,
        "low": close - 1,
        "volume": volume,
    }, index=dates)
    return df

@pytest.fixture
def tsla_df():
    dates = pd.date_range("2024-01-01", periods=15)
    close = pd.Series(
        [100, 102, 101, 103, 102, 104, 106, 105, 107, 108,
         110, 109, 111, 112, 113], index=dates)
    volume = pd.Series(
        [1000, 950, 990, 1020, 1100, 900, 980, 1030, 1100, 1080,
            975, 1010, 1110, 1050, 1130], index=dates)
    df = pd.DataFrame({
        "close": close,
        "high": close + 1,
        "low": close - 1,
        "volume": volume,
    }, index=dates)
    return df

@pytest.fixture
def sp500_df():
    dates = pd.date_range("2024-01-01", periods=15)
    close = pd.Series(
        [100, 101, 102, 101, 102, 103, 104, 103, 104, 104,
         105, 105, 106, 106, 107], index=dates)
    volume = pd.Series(
        [2000, 1950, 1990, 2020, 2100, 1900, 1980, 2030, 2100, 2080,
         1975, 2010, 2110, 2050, 2130], index=dates)
    df = pd.DataFrame({
        "close": close,
        "high": close + 1,
        "low": close - 1,
        "volume": volume,
    }, index=dates)
    return df