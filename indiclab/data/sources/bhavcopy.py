import io
import sys
import zipfile
import pandas as pd
import requests
from datetime import datetime
from dataclasses import dataclass
from typing import ClassVar

@dataclass
class BhavcopyConfigEquity:

    URL: ClassVar[dict[str, tuple[str, bool]]] = {
        "NSE": ("https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{Y}{MM}{DD}_F_0000.csv.zip", True),
        "BSE": ("https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{Y}{MM}{DD}_F_0000.CSV", False),
    }

    LEGACY_URL: ClassVar[dict[str, tuple[str, bool]]] = {
        "NSE": ("https://nsearchives.nseindia.com/content/historical/EQUITIES/{Y}/{MON}/cm{DD}{MON}{Y}bhav.csv.zip", True),
        "BSE": ("https://www.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_{DD}{MM}{YY}.zip", True),
    }

    HEADERS: ClassVar[dict] = {
        "NSE": {"User-Agent": "Mozilla/5.0",
                "Referer": "https://www.nseindia.com/all-reports"},

        "BSE": {"User-Agent": "Mozilla/5.0",
                "Referer": "https://www.bseindia.com/markets/marketinfo/BhavCopy.aspx"},
    }

@dataclass
class BhavcopyConfigDerivatives:

    URL: ClassVar[dict[str, tuple[str, bool]]] = {
        "NSE": ("https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{Y}{MM}{DD}_F_0000.csv.zip", True),
        "BSE": ("https://www.bseindia.com/download/Bhavcopy/Derivative/BhavCopy_BSE_FO_0_0_0_{Y}{MM}{DD}_F_0000.CSV", False),
    }

    LEGACY_URL: ClassVar[dict[str, tuple[str, bool]]] = {
        "NSE": ("https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{Y}/{MON}/fo{DD}{MON}{Y}bhav.csv.zip", True),
        "BSE": ("https://www.bseindia.com/download/BhavCopy/Derivative/bhavcopy{DD}-{MM}-{YY}.zip", True)
    }

    HEADERS: ClassVar[dict] = {
        "NSE": {"User-Agent": "Mozilla/5.0",
                "Referer": "https://www.nseindia.com/all-reports-derivatives"},

        "BSE": {"User-Agent": "Mozilla/5.0",
                "Referer": "https://www.bseindia.com/markets/marketinfo/BhavCopy.aspx"},
    }

def get_bhavcopy_equity(date: str, exchange: str = "NSE", timeOut = 5) -> pd.DataFrame:

    legacy_end_date = datetime(2024, 7, 8)
    t_date = datetime.strptime(date, "%Y%m%d")
    exchange = exchange.upper()

    if exchange not in ['BSE', 'NSE']:
        raise ValueError('exchage must be NSE or BSE')

    url, iszip = (BhavcopyConfigEquity.URL if t_date >= legacy_end_date else BhavcopyConfigEquity.LEGACY_URL)[exchange]
    url = url.format(Y = t_date.year, YY = t_date.strftime("%y"), MM = t_date.strftime("%m"),\
                     DD = t_date.strftime("%d"), MON = t_date.strftime("%b").upper())

    ''' Data Loading '''
    s = requests.Session()
    s.headers.update(BhavcopyConfigEquity.HEADERS[exchange])
    if exchange == 'NSE':
        s.get("https://www.nseindia.com", timeout=timeOut)

    r = s.get(url, timeout=timeOut)
    r.raise_for_status()

    if iszip:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            df = pd.read_csv(z.open(z.namelist()[0]))
    else:
        df = pd.read_csv(io.StringIO(r.text))


    """Data Processing"""
    if exchange == "BSE":
        
        if t_date >= legacy_end_date:
            columns = [
                "TradDt", "Src", "SctySrs", "FinInstrmTp", "ISIN", "TckrSymb",
                "FinInstrmNm", "OpnPric", "HghPric", "LwPric", "ClsPric",
                "LastPric", "SttlmPric", "TtlTradgVol", "TtlTrfVal",
                "TtlNbOfTxsExctd",
            ]
        else:
            columns = [
                "SC_CODE", "SC_NAME", "SC_GROUP", "ISIN_CODE", "OPEN", "HIGH",
                "LOW", "CLOSE", "LAST", "NO_TRADES", "NET_TURNOV",
            ]

        df = df[columns]

        if t_date >= legacy_end_date:
            df.columns = [
                "Date", "Exchange", "Instrument_Type", "Instrument", "ISIN",
                "Ticker", "Name", "Open", "High", "Low", "Close", "Last",
                "Settlement", "Volume", "Turnover", "Trades",
            ]

        else:
            df.columns = [
                "Instrument_ID", "Name", "Instrument_Type", "ISIN", "Open",
                "High", "Low", "Close", "Last", "Trades", "Turnover",
            ]
            df["Date"] = t_date
            df["Exchange"] = exchange
            df["Settlement"] = df["Close"]

    elif exchange == "NSE":

        if t_date >= legacy_end_date:
            columns = [
                "TradDt", "Src", "SctySrs", "FinInstrmTp", "ISIN", "TckrSymb",
                "FinInstrmNm", "OpnPric", "HghPric", "LwPric", "ClsPric",
                "LastPric", "SttlmPric", "TtlTradgVol", "TtlTrfVal",
                "TtlNbOfTxsExctd",
            ]

            df = df[columns]
            df.columns = [
                "Date", "Exchange", "Instrument_Type", "Instrument", "ISIN",
                "Ticker", "Name", "Open", "High", "Low", "Close", "Last",
                "Settlement", "Volume", "Turnover", "Trades",
            ]

        else:
            df = df[
                [
                    "TIMESTAMP", "SYMBOL", "SERIES", "OPEN", "HIGH", "LOW",
                    "CLOSE", "LAST", "TOTTRDQTY", "TOTTRDVAL", "TOTALTRADES", "ISIN",
                ]
            ]
            df.columns = [
                "Date", "Ticker", "Instrument_Type", "Open", "High", "Low",
                "Close", "Last", "Volume", "Turnover", "Trades", "ISIN",
            ]

            df["Date"] = t_date
            df["Exchange"] = exchange
            df["Settlement"] = df["Close"]

    df['Date'] = pd.to_datetime(df['Date'])
    return df
 
def get_bhavcopy_derivative(date: str, exchange: str = "NSE", timeOut = 5) -> pd.DataFrame:

    legacy_end_date = datetime(2024, 7, 8)
    t_date = datetime.strptime(date, "%Y%m%d")
    exchange = exchange.upper()

    if exchange not in ['BSE', 'NSE']:
        raise ValueError('exchage must be NSE or BSE')

    if (t_date < legacy_end_date) and (exchange == 'BSE'):
        raise ValueError('BSE option data not available prior to {legacy_end_date.strftime("%Y-%m-%d")}')

    url, iszip = (BhavcopyConfigDerivatives.URL if t_date >= legacy_end_date else BhavcopyConfigDerivatives.LEGACY_URL)[exchange]
    url = url.format(Y = t_date.year, YY = t_date.strftime("%y"), MM = t_date.strftime("%m"),\
                     DD = t_date.strftime("%d"), MON = t_date.strftime("%b").upper())

    ''' Data Loading '''
    s = requests.Session()
    s.headers.update(BhavcopyConfigDerivatives.HEADERS[exchange])
    if exchange == 'NSE':
        s.get("https://www.nseindia.com", timeout=timeOut)

    r = s.get(url, timeout=timeOut)
    r.raise_for_status()

    if iszip:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            filename = z.namelist()[0]

            with z.open(filename) as f:
                if filename.lower().endswith((".xls", ".xlsx")):
                    df = pd.read_excel(f, header = 1)
                else:
                    df = pd.read_csv(f)
    else:
        df = pd.read_csv(io.StringIO(r.text))

    """Data Processing"""
    if exchange == "BSE":
        
        if t_date >= legacy_end_date:
            columns = [
                "TradDt", "Src", "FinInstrmTp", 'FinInstrmId', "ISIN", "TckrSymb",
                "FinInstrmNm", 'XpryDt', "StrkPric", "OptnTp", "OpnPric", "HghPric", "LwPric", "ClsPric",
                "LastPric", "SttlmPric", "TtlTradgVol", "TtlTrfVal",
                "TtlNbOfTxsExctd", 'OpnIntrst'
            ]
            
            df = df[columns]
            df.columns = [
                "Date", "Exchange", "Instrument_Type", "Instrument_ID", "ISIN",
                "Ticker", "Name", "Expiry_Date", "Strike_Price", "Option_Type",  "Open", "High", "Low", "Close", "Last",
                "Settlement", "Volume", "Turnover", "Trades", "Open_Interest"
            ]

    elif exchange == "NSE":

        if t_date >= legacy_end_date:
            columns = [
                      "TradDt", "Src", "FinInstrmTp", 'FinInstrmId', "ISIN", "TckrSymb", "FinInstrmNm", 'XpryDt', "StrkPric", "OptnTp", "OpnPric", "HghPric", "LwPric", "ClsPric",
                      "LastPric", "SttlmPric", "TtlTradgVol", "TtlTrfVal",
                      "TtlNbOfTxsExctd", 'OpnIntrst'
             ]

            df = df[columns]
            df.columns = [
                "Date", "Exchange", "Instrument_Type", "Instrument_ID", "ISIN",
                "Ticker", "Name", "Expiry_Date", "Strike_Price", "Option_Type",  "Open", "High", "Low", "Close", "Last",
                "Settlement", "Volume", "Turnover", "Trades", "Open_Interest"
            ]

        else:
            df = df[
                ['TIMESTAMP', 'INSTRUMENT', 'SYMBOL', 'EXPIRY_DT', 'STRIKE_PR', 'OPTION_TYP', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'SETTLE_PR', 'CONTRACTS', 'VAL_INLAKH', 'OPEN_INT']
            ]

            df.columns = ['Date', "Instrument_Type", 'Symbol', 'Expiry_Date', 'Strike_Price', 'Option_Type', 'Open', 'High', 'Low', 'Close', 'Settlement', 'Volume', 'Turnover_In_LAKH', 'Open_Interest']

            df["Date"] = t_date
            df["Exchange"] = exchange

    df['Date'] = pd.to_datetime(df['Date'])
    return df



 
