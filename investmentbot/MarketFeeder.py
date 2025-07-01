import pandas as pd
import yfinance as yf
import time

def get_last_prices(ticker, period, interval, sma_rolling_period=None):
    instrument = yf.Ticker(ticker)

    hist = instrument.history(period=period, interval=interval)
    
    if sma_rolling_period != None:
        hist["SMA"] = hist["Close"].rolling(window=sma_rolling_period).mean()

    hist['Date'] = hist.index

    hist['Date'] = pd.to_datetime(hist['Date']).dt.strftime('%Y%m%d')

    hist.index = hist['Date']

    return hist.to_dict('index')

def get_current_price(ticker):
    instrument = yf.Ticker(ticker)
    
    return round(instrument.fast_info['lastPrice'], 2)

def main():
    for i in range(1000):
        print(list(get_last_prices(ticker='QLD', period='max', interval='1d').items())[-1])
        time.sleep(1)
    # print(get_last_prices(ticker='QLD', period='max', interval='1d').items())

