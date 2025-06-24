import pytest
import pandas as pd
from datetime import date
from calendar import SATURDAY, SUNDAY

from stockie.market_calendar import MarketCalendar

class TestMarketCalendar:
    @pytest.fixture(scope="class")
    def nyse_calendar(self):
        return MarketCalendar(market="NYSE")

    def test_is_trading_day_with_regular_weekday(self, nyse_calendar):
        trading_day = pd.Timestamp("2024-07-03")  # Day before July 4th (=Wednesday)
        assert nyse_calendar.is_trading_day(trading_day) is True

    def test_is_trading_day_with_holiday(self, nyse_calendar):
        holiday = pd.Timestamp("2024-07-04")  # US Independence Day
        assert nyse_calendar.is_trading_day(holiday) is False

    def test_next_trading_day_skips_weekend(self, nyse_calendar):
        friday = pd.Timestamp("2024-07-05")
        next_day = nyse_calendar.next_trading_day(after_date=friday)
        assert isinstance(next_day, date)
        assert next_day > friday.date()
        assert pd.Timestamp(next_day).weekday() not in (SATURDAY, SUNDAY)

    def test_next_trading_day_skips_if_today_is_trading_day(self, nyse_calendar):
        trading_day = pd.Timestamp("2024-07-03")
        next_day = nyse_calendar.next_trading_day(after_date=trading_day)
        assert next_day > trading_day.date()

    def test_prev_trading_day_skips_weekend(self, nyse_calendar):
        monday = pd.Timestamp("2024-07-08")
        prev_day = nyse_calendar.prev_trading_day(before_date=monday)
        assert isinstance(prev_day, date)
        assert prev_day < monday.date()
        assert pd.Timestamp(prev_day).weekday() not in (SATURDAY, SUNDAY)

    def test_prev_trading_day_skips_if_today_is_trading_day(self, nyse_calendar):
        trading_day = pd.Timestamp("2024-07-03")
        prev_day = nyse_calendar.prev_trading_day(before_date=trading_day)
        assert prev_day < trading_day.date()

    def test_default_behavior_uses_today(self, nyse_calendar, monkeypatch):
        mock_today = pd.Timestamp("2024-12-25")  # Christmas
        monkeypatch.setattr(pd.Timestamp, "today", lambda: mock_today)
        assert nyse_calendar.is_trading_day() is False

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))