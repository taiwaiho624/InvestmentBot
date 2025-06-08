import pandas as pd
import yfinance as yf
from utils import *

class MarketFeeder:
    def __init__(self):
        pass
    
    def get_last_prices(self, ticker, period, interval, sma_rolling_period=None):
        instrument = yf.Ticker(ticker)

        hist = instrument.history(period=period, interval=interval)
        
        if sma_rolling_period != None:
            hist["SMA"] = hist["Close"].rolling(window=sma_rolling_period).mean()

        hist['Date'] = hist.index

        hist['Date'] = pd.to_datetime(hist['Date']).dt.strftime('%Y%m%d')

        hist.index = hist['Date']

        return hist.to_dict('index')

    def get_current_price(self, ticker):
        instrument = yf.Ticker(ticker)
        
        return round(instrument.fast_info['lastPrice'], 2)

if __name__ == '__main__':
    feed = MarketFeeder()
    print(feed.get_current_price('QQQ'))


