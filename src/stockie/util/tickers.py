# src/stockie/util/tickers.py

import pandas as pd
import requests
from io import StringIO
from typing import List
import logging

class Tickers:
    def __init__(self, logger: logging.Logger, full_config: dict) -> None:
        self.logger = logger
        self.ticker_config = full_config["tickers"]
        self.logger.info("Initialized Tickers with config:")
        self.logger.info(f"{self.ticker_config=}")

    @property
    def benchmarks(self) -> List[str]:
        return self.ticker_config.get("benchmarks", [])

    @property
    def cryptocurrencies(self) -> List[str]:
        return self.ticker_config.get("cryptocurrencies", [])

    @property
    def nsye_tickers(self) -> List[str]:
        if not self.ticker_config.get("nyse"):
            return []
        return self._get_nyse_tickers('N')

    @property
    def nyse_american_tickers(self) -> List[str]:
        if not self.ticker_config.get("nyse_american"):
            return []
        return self._get_nyse_tickers('A')

    @property
    def nyse_arca_tickers(self) -> List[str]:
        if not self.ticker_config.get("nyse_arca"):
            return []
        return self._get_nyse_tickers('P')

    @property
    def sp500_tickers(self) -> List[str]:
        if not self.ticker_config.get("sp500"):
            return []
        return self._get_sp500_tickers()

    @property
    def dow30_tickers(self) -> List[str]:
        if not self.ticker_config.get("dow30"):
            return []
        return self._get_dow30_tickers()

    @property
    def russell2000_tickers(self) -> List[str]:
        return []  # TODO

    @property
    def nasdaq_tickers(self) -> List[str]:
        if not self.ticker_config.get("nasdaq"):
            return []
        return self._get_nasdaq_tickers()

    @property
    def nasdaq100_tickers(self) -> List[str]:
        if not self.ticker_config.get("nasdaq100"):
            return []
        return self._get_nasdaq100_tickers()

    @property
    def all_tickers(self) -> List[str]:
        return sorted(set(
            self.benchmarks +
            self.cryptocurrencies +
            self.nsye_tickers +
            self.nyse_american_tickers +
            self.nyse_arca_tickers +
            self.sp500_tickers +
            self.dow30_tickers +
            self.russell2000_tickers +
            self.nasdaq_tickers +
            self.nasdaq100_tickers
        ))

    def _get_nyse_tickers(self, exchange: str = 'N') -> List[str]:
        url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/otherlisted.txt"
        df = pd.read_csv(url, sep="|")
        return sorted(df[df["Exchange"] == exchange]["ACT Symbol"].dropna().unique())

    def _get_dow30_tickers(self) -> List[str]:
        return [
            "AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW", "GS", "HD",
            "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "PG",
            "TRV", "UNH", "V", "VZ", "WBA", "WMT"
        ]

    def _get_sp500_tickers(self) -> List[str]:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tables = pd.read_html(StringIO(response.text))
        
        # Look for table with S&P 500 count (500-510 rows) and Symbol column
        for table in tables:
            if 500 <= table.shape[0] <= 510 and 'Symbol' in table.columns:
                return table["Symbol"].tolist()
        
        # Fallback to table 1 if the above doesn't work
        return tables[1]["Symbol"].tolist()

    def _get_nasdaq_tickers(self) -> List[str]:
        url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
        df = pd.read_csv(url, sep="|").iloc[:-1]
        return df[df["Symbol"].notna()]["Symbol"].tolist()

    def _get_nasdaq100_tickers(self) -> List[str]:
        url = "https://api.nasdaq.com/api/quote/list-type/nasdaq100"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        rows = response.json()["data"]["data"]["rows"]
        return [row["symbol"] for row in rows]