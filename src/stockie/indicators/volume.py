import pandas as pd
from stockie.indicators.base import BaseIndicator

class VolumeIndicator(BaseIndicator):
    def obv(self) -> pd.Series:
        """Calculate On-Balance Volume (OBV) for the price data"""
        close = self.df["close"]
        volume = self.df["volume"]

        direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
        obv = (volume * direction).fillna(0).cumsum()
        obv.name = "on_balance_volume"
        return obv

    def cmf(self, window: int = 21) -> pd.Series:
        """Calculate the Chaikin Money Flow (CMF) for the price data."""
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        volume = self.df["volume"]

        clv = ((close - low) - (high - close)) / (high - low).replace(0, 1)
        cmf = (clv * volume).rolling(window=window).sum() / volume.rolling(window=window).sum()
        cmf.name = f"cmf_{window}"
        return cmf

    def vema(self, window: int = 21) -> pd.Series:
        """Calculate the Volume Exponential Moving Average (Volume EMA) for the price data"""
        vma = self.df["volume"].ewm(span=window, adjust=False).mean()
        vma.name = f"vema_{window}"
        return vma

    def vsma(self, window: int = 21) -> pd.Series:
        """Calculate the Volume Simple Moving Average (Volume SMA) for the price data."""
        vma = self.df["volume"].rolling(window=window).mean()
        vma.name = f"vsma_{window}"
        return vma

    def pvt(self) -> pd.Series:
        """Calculate the Price-Volume Trend (PVT) for the price data"""
        close = self.df["close"]
        volume = self.df["volume"]
        pct_change = close.pct_change()

        pvt = (pct_change * volume).fillna(0).cumsum()
        pvt.name = "pvt"
        return pvt