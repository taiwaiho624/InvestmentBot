import datetime as datetime
from datetime import date
from investmentbot.utils import *
import statistics
from investmentbot.define import *
import pandas as pd
from openpyxl import load_workbook
import logging

class Stat:
    def __init__(self):
        self.events = {}

    def _get_ytd_for_event(self, event):
        event_year = int(event.date[0:4])
        event_previous_year = str(event_year - 1)
        ref_event = None
        first_event = None
        is_first_event_set = False
        for date, previous_event in self.events.items():
            if is_first_event_set == False:
                first_event = previous_event
                is_first_event_set = True
            if date[0:6] == f"{event_previous_year}12":
                ref_event = previous_event
                break
        if ref_event == None:
            ref_event = first_event
        if ref_event != None:
            ytd = (event.total_value - ref_event.total_value) / ref_event.total_value * 100
            return ytd
        return 0

    def dump(self):
        self._get_stat()
        logging.info(f"Cash Raio Median[{self.median_cash_ratio}] Cash Raio Mean[{self.mean_cash_ratio}]")

    def _get_stat(self):
        cash_ratio = []
        returns = []
        for _, event in self.events.items():
            if event.state == State.WAIT_OUT:
                cash_ratio.append(event.cash / (event.stock + event.cash) * 100)
            returns.append(event.stock + event.cash)
        self.median_cash_ratio = statistics.median(cash_ratio)
        self.mean_cash_ratio = statistics.mean(cash_ratio)

    def add_event(self, event):
        self.events[event.date] = event

class ValueAverageTradingBot:
    def __init__(self, market_feeder):
        self.market_feeder = market_feeder
        
        # Algo
        self.underlying_ticker = 'QQQ'
        self.deriv_ticker = 'QLD'
        self.cash_growth = 1
        self.buy_in_threshold = 1.04
        self.growth = 1.22
        self.init_cash = 63694
        self.cash_in_per_month = 0
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
        self.hist_underlying_month = self.market_feeder.get_last_prices(ticker=self.underlying_ticker, period='max', interval='1mo', sma_rolling_period=12)
        self.hist_underlying_day = self.market_feeder.get_last_prices(ticker=self.underlying_ticker, period='max', interval='1d')
        self.hist_deriv = self.market_feeder.get_last_prices(ticker=self.deriv_ticker, period='max', interval='1d')
        self.stat = Stat()

        self.file_name = None
        self.commit_file = False

    def dump_algo_params_to_file(self):
        wb = load_workbook(self.file_name)
        sheet = None
        if 'Parameters' in wb.sheetnames:
            wb.remove(wb['Parameters'])
            
        sheet = wb.create_sheet(title='Parameters')
        sheet.append(['Underlying', self.underlying_ticker])
        sheet.append(['Deriv_ticker', self.deriv_ticker])
        sheet.append(['Cash Growth rate', self.cash_growth])
        sheet.append(['Deriv Growth rate', self.growth])
        sheet.append(['Buy in threshold', self.buy_in_threshold])
        sheet.append(['TP ratio', self.tp_increment])
        sheet.append(['TP1 Max', self.tp1_max])
        sheet.append(['TP2 Max', self.tp2_max])
        wb.save(self.file_name)

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
            value_to_buy = min((self.target_value - self.stock), self.cash)
            number_of_stocks = int(value_to_buy / operation_price)
            self.buy(number_of_stocks, operation_price)
            side = Side.BUY
        elif action == Action.TAKE_PROF1 or action == Action.TAKE_PROF2:
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
            number_of_stocks = int(self.number_of_stock / 2)
            self.sell(number_of_stocks, operation_price)
            side = Side.SELL
        elif action == Action.SELL_ALL:
            self._reset_tp_counter()
            number_of_stocks = self.number_of_stock
            self.sell(number_of_stocks, operation_price)
            side = Side.SELL

        return Event(action, operation_price, f"{side.name:<5} {number_of_stocks}@{operation_price:.3f}")

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
            
    def _init_from_file(self):
        try:
            data = pd.read_excel(self.file_name).to_dict(orient='records')[-1]
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

            return True
        except FileNotFoundError:
            logging.error(f"[E] File {self.file_name} does not exist. Exit")
            return False

    def check(self, trading_day, operation_price=None):
        month = get_month_by_day(trading_day)
        previous_month = get_previous_month_by_day(trading_day)
        previous_month_sma = self.hist_underlying_month[previous_month]['SMA']
        previous_month_close = self.hist_underlying_month[previous_month]['Close']
        try:
            underlying_price_open = self.hist_underlying_day[trading_day]['Open']
            underlying_price_low = self.hist_underlying_day[trading_day]['Low']
            underlying_price_high = self.hist_underlying_day[trading_day]['High']
        except:
            logging.error(f"[E] {trading_day} is not a trading day")
            return

        deriv_price_high = self.hist_deriv[trading_day]['High']
        deriv_price_open = self.hist_deriv[trading_day]['Open']
        deriv_price_low = self.hist_deriv[trading_day]['Low']

        #daily operation
        self.stock = self.number_of_stock * deriv_price_open
        
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
                        self.state = State.WAIT_OUT
                        self.wait_in_and_previous_is_higher_than_sma = False
                        operation_price = deriv_price_open if operation_price == None else operation_price
                        event = self.action(Action.ENRTRY, operation_price)
                elif previous_month_close > previous_month_sma:
                    self.wait_in_and_previous_is_higher_than_sma = True
            elif self.state == State.WAIT_OUT or self.state == State.SL_ONE:
                if underlying_price_open > previous_month_sma:
                    if self.state == State.SL_ONE:
                        self.state = State.WAIT_OUT
                    if self.tp1_counter == 10:
                        operation_price = deriv_price_open if operation_price == None else operation_price
                        event = self.action(Action.TAKE_PROF2, operation_price)
                    elif self.stock < self.target_value:
                        operation_price = deriv_price_open if operation_price == None else operation_price
                        event = self.action(Action.BUY_UP_TO, operation_price)
                    else:
                        operation_price = deriv_price_open if operation_price == None else operation_price
                        event = self.action(Action.TAKE_PROF1, operation_price)
                else:
                    # sell all
                    self.state = State.WAIT_IN
                    operation_price = deriv_price_open if operation_price == None else operation_price
                    event = self.action(Action.SELL_ALL, operation_price)
            
            if event == None:
                operation_price = deriv_price_open if operation_price == None else operation_price
                event = self.action(Action.NO_ACTION, operation_price)
            event.cash_in = self.cash_in_per_month

            self.current_month = month

        if self.state == State.WAIT_OUT and underlying_price_low < previous_month_sma:
            self.state = State.SL_ONE
            operation_price = deriv_price_low if operation_price == None else operation_price
            event = self.action(Action.SELL_HALF, operation_price)
        
        if self.state == State.WAIT_IN and self.wait_in_and_previous_is_higher_than_sma == True and underlying_price_high > (previous_month_sma * self.buy_in_threshold):
            self.state = State.WAIT_OUT
            self.wait_in_and_previous_is_higher_than_sma = False
            operation_price = deriv_price_high if operation_price == None else operation_price
            event = self.action(Action.ENRTRY, operation_price)

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
            event.underlying_price_open = underlying_price_open
            event.underlying_price_low = underlying_price_low
            event.underlying_price_high = underlying_price_high
            event.deriv_price_high = deriv_price_high
            event.deriv_price_open = deriv_price_open
            event.deriv_price_low =  deriv_price_low
            self.stat.add_event(event)

            logging.info(event)
            if self.file_name != None and self.commit_file == True:
                event.to_file(self.file_name)

    def normal(self, trading_day, operation_price=None):
        if self._init_from_file() == False:
            return

        if int(self.latest_processed_date) > int(trading_day):
            logging.error(f"[E] Requested date[{trading_day}] is before the latestest processed date[{self.latest_processed_date}]. Exit")
            return

        self.check(trading_day, operation_price)
        self.dump_algo_params_to_file()

    def replay(self, start_date, end_date=date.today().strftime('%Y%m%d')):
        self.target_value = self.init_cash
        self.cash = self.init_cash
        self.cost = self.init_cash
        for trading_day, _ in self.hist_underlying_day.items():
            if int(trading_day) < int(start_date) or int(trading_day) > int(end_date):
                continue
            
            self.check(trading_day)

        self.stat.dump()
        self.dump_algo_params_to_file()
