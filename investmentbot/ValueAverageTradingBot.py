import datetime as datetime
from datetime import date
from investmentbot.utils import *
import statistics
from investmentbot.define import *
import pandas as pd
from openpyxl import load_workbook
import investmentbot.MarketFeeder as MarketFeeder
import logging
import time

class Stat:
    def __init__(self):
        self.events = {}

    def add_event(self, event):
        self.events[event.date] = event
    
    def calculate_mdd(self, event):
        total_value = event.stock + event.cash
        mdd = 0
        past_event_values = []
        for _, past_event in self.events.items():
            past_event_values.append(past_event.stock + past_event.cash)
        
        if len(past_event_values) > 0:
            mdd = (max(past_event_values) - total_value ) / max(past_event_values) * 100

        if mdd < 0:
            mdd = 0
        return mdd

    def get(self):
        result = {}
        mdd = [event.mdd for _, event in self.events.items()]
        total_equity = [event.stock + event.cash for _, event in self.events.items()]
        returns = [(event.stock + event.cash - event.cost)  / event.cost for _, event in self.events.items()]
        cash_ratio = [(event.cash) / (event.stock + event.cash) * 100 for _, event in self.events.items() if event.stock != 0]
        result['max_mdd'] = max(mdd)
        result['equity_sd'] = statistics.stdev(total_equity)
        result['return_sd'] = statistics.stdev(returns)
        result['final_return'] = returns[-1]
        result['cash_ratio_mean'] = statistics.mean(cash_ratio)
        result['cash_ratio_median'] = statistics.median(cash_ratio)
        return result


class ValueAverageTradingBot:
    def __init__(self):        
        # Algo
        self.underlying_ticker = 'QQQ'
        self.deriv_ticker = 'QLD'
        self.cash_growth = 1
        self.buy_in_threshold = 1.04
        self.growth = 1.22
        self.init_cash = 5000
        self.cash_in_per_month = 3185
        self.tp_increment = 0.1        
        self.tp1_max = 10
        self.tp2_max = 3
        
        # Account State
        self.target_value = None # Adjust Per Month
        self.cash = None
        self.cost = None
        self.stock = 0
        self.number_of_stock = 0
        self.state = State.WAIT_IN
        self.wait_in_and_previous_is_higher_than_sma = False
        self.tp1_counter = 0
        self.tp2_counter = 0

        # Stat
        self.current_month = ''

        # Data
        self._get_data()
        self.stat = Stat()

        self.latest_is_previous=False
        self.record_daily = False
        self.events = []

    def _get_data(self):
        self.hist_underlying_month = MarketFeeder.get_last_prices(ticker=self.underlying_ticker, period='max', interval='1mo', sma_rolling_period=12)
        self.hist_underlying_day = MarketFeeder.get_last_prices(ticker=self.underlying_ticker, period='max', interval='1d')
        self.hist_deriv = MarketFeeder.get_last_prices(ticker=self.deriv_ticker, period='max', interval='1d')

    def _get_previous_trading_day(self, day, latest_is_previous):
        if latest_is_previous:
            return list(self.hist_underlying_day)[-1]
        previous = None
        for date, value in self.hist_underlying_day.items():
            if date == day:
                return previous
            previous = date
        return None

    def get_params(self):
        result = {}
        result['Underlying'] = self.underlying_ticker
        result['Deriv_ticker'] = self.deriv_ticker
        result['Cash Growth rate'] = self.cash_growth
        result['Deriv Growth rate'] = self.growth
        result['Buy in threshold'] = self.buy_in_threshold
        result['TP ratio'] = self.tp_increment
        result['TP1 Max'] = self.tp1_max
        result['TP2 Max'] = self.tp2_max
        return result

    def buy(self, number_of_stocks, price):
        self.number_of_stock += number_of_stocks
        self.stock = self.number_of_stock * price
        self.cash -= number_of_stocks * price

    def sell(self, number_of_stocks, price):
        self.number_of_stock -= number_of_stocks
        self.stock = self.number_of_stock * price
        self.cash += number_of_stocks * price

    def action(self, action, operation_price):
        number_of_stocks = 0
        side = Side.HOLD
        if action == Action.BUY_UP_TO or action == Action.ENRTRY:
            self.state = State.WAIT_OUT
            self.wait_in_and_previous_is_higher_than_sma = False        
            value_to_buy = min((self.target_value - self.stock), self.cash)
            number_of_stocks = int(value_to_buy / operation_price)
            self.buy(number_of_stocks, operation_price)
            side = Side.BUY
        elif action == Action.TAKE_PROF1 or action == Action.TAKE_PROF2:
            self.state = State.WAIT_OUT
            if action == Action.TAKE_PROF1:
                self._increment_tp1_counter()
                value_to_sell = (self.stock - self.target_value) * self.tp_increment * self.tp1_counter
            elif action == Action.TAKE_PROF2:
                self._increment_tp2_counter()
                value_to_sell = self.stock * self.tp_increment * self.tp2_counter
            number_of_stocks = int(value_to_sell / operation_price)
            self.sell(number_of_stocks, operation_price)
            side = Side.SELL
        elif action == Action.SELL_HALF:
            self.state = State.SL_ONE
            number_of_stocks = int(self.number_of_stock / 2)
            self.sell(number_of_stocks, operation_price)
            side = Side.SELL
        elif action == Action.SELL_ALL:
            self.state = State.WAIT_IN
            self._reset_tp_counter()
            number_of_stocks = self.number_of_stock
            self.sell(number_of_stocks, operation_price)
            side = Side.SELL

        operation = f"{side.name:<5} {number_of_stocks}@{operation_price:.3f}" if action != Action.NO_ACTION else "HOLD"
        return Event(action, f"{operation}")

    def _reset_tp_counter(self):
        self.tp1_counter = 0
        self.tp2_counter = 0

    def _increment_tp1_counter(self):
        self.tp1_counter += 1
        if self.tp1_counter > self.tp1_max:
            self.tp1_counter = self.tp1_max

    def _increment_tp2_counter(self):
        self.tp2_counter +=1
        if self.tp2_counter > self.tp2_max:
            self.tp2_counter = self.tp2_max
            
    def init_from_file(self, data):
        self.target_value = data['目標市值']
        self.cash = data['現金']
        self.cost = data['成本']
        self.stock = data['股票市值']
        self.number_of_stock = data['股票數量']
        self.state = get_state_from_string(data['Current State'])
        self.wait_in_and_previous_is_higher_than_sma = data['等入市-上月高於sma']
        self.tp1_counter = data['TP1 Counter']
        self.tp2_counter = data['TP2 Counter']
        self.current_month = get_month_by_day(str(data['日期']))
        self.latest_processed_date = data['日期']

    def check(self, trading_day, operation_price=None, underlying_price=None):
        month = get_month_by_day(trading_day)
        previous_month = get_previous_month_by_day(trading_day)
        previous_month_sma = self.hist_underlying_month[previous_month]['SMA']
        previous_month_close = self.hist_underlying_month[previous_month]['Close']
        this_month_open = self.hist_underlying_month[month]['Open'] if underlying_price == None else underlying_price
        try:
            previous_day = self._get_previous_trading_day(trading_day, self.latest_is_previous)
            previous_day_close = self.hist_underlying_day[previous_day]['Close']
            underlying_price_open = self.hist_underlying_day[trading_day]['Open'] if underlying_price == None else underlying_price
        except:
            logging.error(f"[E] {trading_day} is not a trading day")
            return -1

        deriv_price_open = self.hist_deriv[trading_day]['Open'] if operation_price == None else operation_price

        #daily operation
        self.stock = self.number_of_stock * deriv_price_open
        
        operation_price = deriv_price_open if operation_price == None else operation_price

        event = None
        if month != self.current_month: #first day of a month
            if self.state != State.WAIT_IN:
                self.target_value = self.target_value * (self.growth ** (1 / 12)) #Only grow target value when it is above 12 month sma
                self.cash = self.cash * (self.cash_growth ** (1 / 12))

            if self.state != State.WAIT_IN: 
                self.target_value += self.cash_in_per_month
            self.cash += self.cash_in_per_month
            self.cost += self.cash_in_per_month

            if self.state == State.WAIT_IN:
                if underlying_price_open > (previous_month_sma * self.buy_in_threshold):
                    if self.stock < self.target_value:
                        event = self.action(Action.ENRTRY, operation_price)
            elif self.state == State.WAIT_OUT:
                if underlying_price_open > previous_month_sma:
                    if self.tp1_counter == self.tp1_max:
                        event = self.action(Action.TAKE_PROF2, operation_price)
                    elif self.stock < self.target_value:
                        event = self.action(Action.BUY_UP_TO, operation_price)
                    else:
                        event = self.action(Action.TAKE_PROF1, operation_price)
                else:
                    event = self.action(Action.SELL_ALL, operation_price)
            elif self.state == State.SL_ONE:
                if underlying_price_open > (previous_month_sma * self.buy_in_threshold):
                    event = self.action(Action.BUY_UP_TO, operation_price)
                elif underlying_price_open < previous_month_sma:
                    event = self.action(Action.SELL_ALL, operation_price)
            if event == None:
                event = self.action(Action.NO_ACTION, operation_price)
            event.cash_in = self.cash_in_per_month
            self.current_month = month
        if event == None:
            if self.state == State.WAIT_OUT:
                if previous_day_close < previous_month_sma:
                    event = self.action(Action.SELL_HALF, operation_price)
            elif self.state == State.WAIT_IN:
                if previous_month_close > previous_month_sma and this_month_open > previous_month_sma and previous_day_close > (previous_month_sma * self.buy_in_threshold):
                    event = self.action(Action.ENRTRY, operation_price)
            elif self.state == State.SL_ONE:
                if this_month_open > previous_month_sma and previous_day_close > (previous_month_sma * self.buy_in_threshold):
                    event = self.action(Action.BUY_UP_TO, operation_price)
        
        if event == None and self.record_daily == True:
            event = self.action(Action.NO_ACTION, operation_price)

        if event != None:
            event.date = trading_day
            event.target_value = self.target_value
            event.stock = self.stock
            event.cash = self.cash
            event.number_of_stocks = self.number_of_stock
            event.cost = self.cost
            event.state = self.state
            event.tp1_counter = self.tp1_counter
            event.tp2_counter = self.tp2_counter
            event.wait_in_and_previous_is_higher_than_sma = self.wait_in_and_previous_is_higher_than_sma
            
            event.previous_month_sma = previous_month_sma
            event.previous_month_close = previous_month_close
            event.previous_day_close = previous_day_close
            event.underlying_price_open = underlying_price_open
            event.deriv_price_open = deriv_price_open

            event.mdd = self.stat.calculate_mdd(event)

            self.stat.add_event(event)
            self.events.append(event)

        return 0

    def normal(self, trading_day, operation_price=None, underlying_price=None):
        if int(self.latest_processed_date) >= int(trading_day):
            logging.error(f"[E] Requested date[{trading_day}] is before the latestest processed date[{self.latest_processed_date}]. Exit")
            return -1

        retry = 0
        while 0 != self.check(trading_day, operation_price, underlying_price):
            self._get_data()
            time.sleep(1)
            retry += 1
            if retry == 60:
                return -1

        return 0

    def replay(self, start_date, end_date=date.today().strftime('%Y%m%d')):
        self.target_value = self.init_cash
        self.cash = self.init_cash
        self.cost = self.init_cash
        for trading_day, _ in self.hist_underlying_day.items():
            if int(trading_day) < int(start_date) or int(trading_day) > int(end_date):
                continue
            
            self.check(trading_day)

        return 0