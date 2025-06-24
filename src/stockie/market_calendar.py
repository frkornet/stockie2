import pandas as pd
import pandas_market_calendars as mcal
from datetime import datetime, date

class MarketCalendar:
    def __init__(self, market='NYSE'):
        self.calendar = mcal.get_calendar(market)

    def is_trading_day(self, check_date=None):
        check_date = check_date or pd.Timestamp.today().normalize()
        schedule = self.calendar.schedule(start_date=check_date, end_date=check_date)
        return not schedule.empty

    def next_trading_day(self, after_date=None):
        after_date = pd.Timestamp(after_date or datetime.today())
        valid_days = self.calendar.valid_days(
            start_date=after_date,
            end_date=after_date + pd.Timedelta(days=10)
        ).tz_localize(None)
        future = valid_days[valid_days > after_date]
        return future[0].date() if not future.empty else None

    def prev_trading_day(self, before_date=None):
        before_date = pd.Timestamp(before_date or datetime.today())
        valid_days = self.calendar.valid_days(
            start_date=before_date - pd.Timedelta(days=10),
            end_date=before_date
        ).tz_localize(None)
        past = valid_days[valid_days < before_date]
        return past[-1].date() if not past.empty else None
    
    def today(self):
        """Returns today's date"""
        return pd.Timestamp.today().normalize().date()