from stockie.indicators import BaseIndicators
import pandas as pd
import numpy as np

class VolumeIndicators(BaseIndicators):

    def __init__(self, df: pd.DataFrame) -> None:
        super().__init__(df)

    def vsma(self, window: int = 21) -> pd.Series:
        """Calculate the Volume Simple Moving Average (Volume SMA) for the price data."""
        vma = self.df["volume"].rolling(window=window).mean()
        vma.name = self._build_indicator_name("vsma", window)
        return vma

    def vema(self, window: int = 21) -> pd.Series:
        """Calculate the Volume Exponential Moving Average (Volume EMA) for the price data"""
        vma = self.df["volume"].ewm(span=window, adjust=False).mean()
        vma.name = self._build_indicator_name("vema", window)
        return vma

    def pvt(self) -> pd.Series:
        """
        Calculate the Price-Volume Trend (PVT) for the price data
        
        See: https://www.stockmaniacs.net/price-volume-trend-indicator/ for more info and details
        on the calculation.
        """
        close = self.df["close"]
        volume = self.df["volume"]
        pct_change = close.pct_change(fill_method=None)

        pvt = (pct_change * volume).fillna(0).cumsum()
        pvt.name = self._build_indicator_name("pvt")
        return pvt

    def obv(self) -> pd.Series:
        """Calculate On-Balance Volume (OBV) for the price data"""
        close = self.df["close"]
        volume = self.df["volume"]

        direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
        obv = (volume * direction).fillna(0).cumsum()
        obv.name = self._build_indicator_name("obv")
        return obv

    def cmf(self, window: int = 21) -> pd.Series:
        """
        Calculate the Chaikin Money Flow (CMF) for the price data.
        
        See: https://tradingtuitions.com/chaikin-money-flow-excel-sheet-2/ for more details on the indiccator
        and its calculation.
        """
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        volume = self.df["volume"]

        denom = (high - low).replace(0, np.nan)
        money_flow_multiplier = (((close - low) - (high - close)) / denom).fillna(0)

        cmf = (money_flow_multiplier * volume).rolling(window=window).sum() / volume.rolling(window=window).sum()
        cmf.name = self._build_indicator_name("cmf", window)
        return cmf

