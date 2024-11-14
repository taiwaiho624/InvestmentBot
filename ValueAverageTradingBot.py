from MarketFeeder import MarketFeeder
import math
import pandas as pd

class ValueAverageTradingBot:
    def __init__(self, market_feeder):
        self.market_feeder = market_feeder
    
        self._init_strategy()
        self._init_balance()

    def _init_strategy(self):
        self.ticker = "QLD"
        self.underlying = "QQQ"
        self.period = "2y"
        self.interval = "1mo"
        self.sma_rolling_period = 12
        self.ytd_return = 1.22
        self.month_return = self.ytd_return ** (1 / self.sma_rolling_period)

    def _init_balance(self):
        columns = ['date', 'cv_before', 'sv_before', 'cv_add','cv_after','sv_after']
        df = pd.read_csv('data/balance.csv', names=columns, header=None, skiprows=[0])
        df[columns[1:]] = df[columns[1:]].astype(float)

        self.df = df
        self.stock_value_before = df.at[df.index[-1], 'sv_before']
        self.cash_value_before = df.at[df.index[-1], 'cv_before']
        self.cash_value = self.cash_value_before + df.at[df.index[-1], 'cv_add']
        
        self.target_value = 0

        for index, row in df.iterrows():
            self.target_value = self.target_value * self.month_return + row['cv_add']
            df.at[df.index[index], 'target_value'] = self.target_value

    def signal(self):
        hist = self.market_feeder.get_last_prices(ticker=self.underlying, period=self.period, interval=self.interval, sma_rolling_period=self.sma_rolling_period)
        
        if len(hist) < 2:
            print("[E] No Historial Data")
            return

        # Check if previous month close price is below the 12 month sma
        if hist['Close'][-2] < hist['SMA'][-2]:
            # Clear all the position
            print('Action[CLEAR] Ticker[{0}]')
            
        else:
            current_price = self.market_feeder.get_current_price(self.ticker)

            # If the stock value is not up to target value, buy up to the target value 
            if self.stock_value_before < self.target_value:
                value_diff = self.target_value - self.stock_value_before

                fill_value = min(value_diff, self.cash_value)

                buy_qty = math.floor(fill_value / current_price)

                if buy_qty == 0:
                    print('Action[NO] Ticker[{0}] Current Price[{1}] Current Cash[{2}] Diff from target value [{3}]'.format(self.ticker, current_price, self.cash_value, value_diff))
                    
                else:
                    print('Action[BUY] Ticker[{0}] Current Price[{1}] Quantity[{2}] Reason[{3}]'.format(self.ticker, current_price, buy_qty, "To Meet Target Value"))

                    self.df.at[self.df.index[-1], 'cv_after'] = self.cash_value_before + self.cash_value - (buy_qty * current_price)
                    self.df.at[self.df.index[-1], 'sv_after'] = self.stock_value_before + (buy_qty * current_price)

            # If the stock value is over target value, sell off to the target value 
            else:
                value_diff = self.stock_value_before - self.target_value

                sell_qty = math.ceil(value_diff / current_price)

                print('Action[SELL] Ticker[{0}] Current Price[{1}] Quantity[{2}] Reason[{3}]'.format(self.ticker, current_price, sell_qty, "Take Profit"))

                self.df.at[self.df.index[-1], 'cv_after'] = self.cash_value_before + self.cash_value + (sell_qty * current_price)
                self.df.at[self.df.index[-1], 'sv_after'] = self.stock_value_before - (sell_qty * current_price)
                
        print (self.df)

if __name__ == '__main__':
    value_average_trading_bot = ValueAverageTradingBot(MarketFeeder())
    value_average_trading_bot.signal()



