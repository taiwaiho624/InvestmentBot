import yfinance as yf
from utils import *

class MarketFeeder:
    def __init__(self):
        pass
    
    def get_last_prices(self, ticker, period, interval, sma_rolling_period):
        instrument = yf.Ticker(ticker)

        hist = instrument.history(period=period, interval=interval)
        
        hist["SMA"] = hist["Close"].rolling(window=sma_rolling_period).mean()

        return hist

    def get_current_price(self, ticker):
        instrument = yf.Ticker(ticker)
        
        return round(instrument.fast_info['lastPrice'], 2)

if __name__ == '__main__':
    feed = MarketFeeder()
    print(feed.get_current_price('QQQ'))


