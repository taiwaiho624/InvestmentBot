from MarketFeeder import MarketFeeder
import math
import pandas as pd
import datetime as datetime
from datetime import date
from dateutil.relativedelta import relativedelta
from configparser import ConfigParser

class ValueAverageTradingBot:
    def __init__(self, market_feeder):
        self.market_feeder = market_feeder
    
        self._init_strategy()
        self._init_balance()

        self.hist = self.market_feeder.get_last_prices(ticker=self.underlying, period=self.period, interval=self.interval, sma_rolling_period=self.sma_rolling_period)
        
    def _init_strategy(self):
        config = ConfigParser()   
        config.read('config.ini')

        self.ticker = config.get('Strategy', 'ticker')
        self.underlying = config.get('Strategy', 'underlying')
        self.period = config.get('Strategy', 'period')
        self.interval = config.get('Strategy', 'interval')
        self.sma_rolling_period = int(config.get('Strategy', 'sma_rolling_period'))
        self.ytd_return = float(config.get('Strategy', 'ytd_return'))
        self.month_return = self.ytd_return ** (1 / self.sma_rolling_period)

    def _init_balance(self):
        columns = ['date', 'cv_before', 'sv_before', 'cv_add','cv_after','sv_after', 'target_value']
        df = pd.read_csv('balance.csv', names=columns, header=None, skiprows=[0])
        df[columns[1:]] = df[columns[1:]].astype(float)

        self.df = df 
        self.stock_value_before = df.at[df.index[-1], 'sv_before']
        self.cash_value_before = df.at[df.index[-1], 'cv_before']
        self.cash_value = self.cash_value_before + df.at[df.index[-1], 'cv_add']
        
        self.target_value = 0

        for index, row in df.iterrows():
            self.target_value = self.target_value * self.month_return + row['cv_add']
            df.at[df.index[index], 'target_value'] = self.target_value
        
        total_cost = 0

        for index, row in df.iterrows():
            total_cost = total_cost + row['cv_add']
            df.at[df.index[index], 'total_cost'] = self.target_value

    def _get_x_month_prices(self, reference_date, delta):
        first_date_of_last_month = date(reference_date.year, reference_date.month, 1) + relativedelta(months=delta)
        key = '{0}{1}'.format(first_date_of_last_month.year, first_date_of_last_month.month)
        return self.hist.loc[[key]]


    def signal(self, price=None, record=False, date=datetime.datetime.now(), row_index=-1):
        previous_price = self._get_x_month_prices(date, -1)
        previous_close = previous_price['Close'][-1]
        previous_sma = previous_price['SMA'][-1]

        # Check if previous month close price is below the 12 month sma
        print('Date[{0}] Month Close[{1}] SMA-{2}[{3}]'.format(previous_price.index[-1], previous_close, self.sma_rolling_period, previous_sma))
        
        if previous_close < previous_sma:
            # Clear all the position
            print('Action[CLEAR] Ticker[{0}] Reason[{1}]'.format(self.ticker, "Month Close is below SMA"))
            
        else:
            current_price = None

            if price is not None:
                current_price = price
            elif datetime.datetime.now().month == date.month and datetime.datetime.now().year == date.year:
                current_price = self.market_feeder.get_current_price(self.ticker)
            else:
                next_price = self._get_x_month_prices(date, 1)
                current_price = next_price['Open'][-1]

            # If the stock value is not up to target value, buy up to the target value 
            if self.stock_value_before < self.target_value:
                value_diff = self.target_value - self.stock_value_before

                fill_value = min(value_diff, self.cash_value)

                buy_qty = math.floor(fill_value / current_price)

                if buy_qty == 0:
                    print('Action[NO] Ticker[{0}] Current Price[{1}] Current Cash[{2}] Diff from target value [{3}]'.format(self.ticker, current_price, self.cash_value, value_diff))
                    
                else:
                    print('Action[BUY] Ticker[{0}] Current Price[{1}] Quantity[{2}] Reason[{3}]'.format(self.ticker, current_price, buy_qty, "To Meet Target Value"))

                    self.df.at[self.df.index[row_index], 'cv_after'] = self.cash_value - (buy_qty * current_price)
                    self.df.at[self.df.index[row_index], 'sv_after'] = self.stock_value_before + (buy_qty * current_price)

            # If the stock value is over target value, sell off to the target value 
            else:
                value_diff = self.stock_value_before - self.target_value

                sell_qty = math.ceil(value_diff / current_price)

                print('Action[SELL] Ticker[{0}] Current Price[{1}] Quantity[{2}] Reason[{3}]'.format(self.ticker, current_price, sell_qty, "Take Profit"))

                self.df.at[self.df.index[row_index], 'cv_after'] = self.cash_value + (sell_qty * current_price)
                self.df.at[self.df.index[row_index], 'sv_after'] = self.stock_value_before - (sell_qty * current_price)
        
        if record:
            self.df.to_csv("balance.csv", index=False, float_format='%.0f', columns=['date', 'cv_before', 'sv_before', 'cv_add','cv_after','sv_after', 'target_value'])

        print(self.df)

    def replay(self):
        pass



