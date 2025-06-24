import pandas as pd
import datetime as dt
import requests
from stockie.config_loader import ConfigLoader

class Tickers:
    def __init__(self, logger):
        self.config = ConfigLoader().get()
        ticker_config = self.config["tickers"]
        logger.info("Loading tickers...")
        logger.info(f"Selected ticker classes: {ticker_config=}")

        self.nsye_tickers = self._get_nyse_tickers('N') if ticker_config['nyse'] else []
        self.nyse_american_tickers = self._get_nyse_tickers('A') if ticker_config['nyse_american'] else []
        self.nyse_arca_tickers = self._get_nyse_tickers('P') if ticker_config['nyse_arca'] else []
        
        self.sp500_tickers = self._get_sp500_tickers() if ticker_config['sp500'] else []
        self.dow30_tickers = self._get_dow30_tickers() if ticker_config['dow30'] else []
        
        # TODO: Implement method to fetch Russell 2000
        self.russell2000_tickers = []

        self.nasdaq_tickers = self._get_nasdaq_tickers() if ticker_config['nasdaq'] else []
        self.nasdaq100_tickers = self._get_nasdaq100_tickers() if ticker_config['nasdaq100'] else []

        self.all_tickers = sorted(set(
            self.nsye_tickers +
            self.nyse_american_tickers +
            self.nyse_arca_tickers +
            self.sp500_tickers +
            self.dow30_tickers +
            self.russell2000_tickers +
            self.nasdaq_tickers +
            self.nasdaq100_tickers
        ))

    def _get_nyse_tickers(self, exchange='N'):
        url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/otherlisted.txt"
        df = pd.read_csv(url, sep="|")
        nyse_df = df[df["Exchange"] == exchange]
        return sorted(nyse_df["ACT Symbol"].dropna().unique())

    def _get_dow30_tickers(self):
        return [
            "AAPL",  # Apple
            "AMGN",  # Amgen
            "AXP",   # American Express
            "BA",    # Boeing
            "CAT",   # Caterpillar
            "CRM",   # Salesforce
            "CSCO",  # Cisco Systems
            "CVX",   # Chevron
            "DIS",   # Walt Disney
            "DOW",   # Dow Inc.
            "GS",    # Goldman Sachs
            "HD",    # Home Depot
            "HON",   # Honeywell
            "IBM",   # IBM
            "INTC",  # Intel
            "JNJ",   # Johnson & Johnson
            "JPM",   # JPMorgan Chase
            "KO",    # Coca-Cola
            "MCD",   # McDonald's
            "MMM",   # 3M
            "MRK",   # Merck
            "MSFT",  # Microsoft
            "NKE",   # Nike
            "PG",    # Procter & Gamble
            "TRV",   # Travelers
            "UNH",   # UnitedHealth
            "V",     # Visa
            "VZ",    # Verizon
            "WBA",   # Walgreens Boots Alliance
            "WMT",   # Walmart
        ]

    def _get_sp500_tickers(self):
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df = tables[0]
        return df["Symbol"].tolist()

    # TODO: implement this method to fetch Russell 2000 tickers
    def _get_russell2000_tickers(self):
        return []

    def _get_nasdaq_tickers(self):
        url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
        df = pd.read_csv(url, sep="|")
        
        # last element is something like 'FILE CREATION TIME: 0623202518:01' and needs to be skipped
        df = df.iloc[:-1]
        df = df[df["Symbol"].notna()]
        return df["Symbol"].tolist()

    def _get_nasdaq100_tickers(self):
        url = "https://api.nasdaq.com/api/quote/list-type/nasdaq100"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9"
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json()
        rows = data["data"]["data"]["rows"]
        tickers = [row["symbol"] for row in rows]
        return tickers
    
    def get_all_tickers(self):
        return self.all_tickers