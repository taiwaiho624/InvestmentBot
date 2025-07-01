from enum import Enum
from openpyxl.styles import PatternFill
import openpyxl

hkd_to_usd = 7.85

class State(Enum):
    WAIT_IN = 1
    WAIT_OUT = 2
    SL_ONE = 3

def get_state_from_string(state_string):
    try:
        return State[state_string.upper()] 
    except KeyError:
        raise ValueError(f"{state_string} is not a valid State")

class Action(Enum):
    BUY_UP_TO = 1
    ENRTRY = 2
    TAKE_PROF1= 3
    TAKE_PROF2 = 4
    SELL_HALF = 5
    SELL_ALL = 6
    NO_ACTION = 7

class Side(Enum):
    HOLD = 0
    BUY = 1
    SELL = 2

class Event:
    def __init__(self, action, operation):
        #event
        self.date = None
        self.action = action
        self.operation = operation
        self.cash_in = 0

        #account state
        self.target_value = None
        self.stock = None
        self.cash = None
        self.number_of_stocks = None
        self.cost = None
        self.state = None
        self.tp1_counter = None
        self.tp2_counter = None
        self.wait_in_and_previous_is_higher_than_sma = None

        #market state
        self.previous_month_sma = None
        self.previous_month_close = None
        self.previous_day_close = None
        self.underlying_price_open = None
        self.underlying_price_low = None
        self.underlying_price_high = None
        self.deriv_price_high = None
        self.deriv_price_open = None
        self.deriv_price_low = None
        
        #calculated
        self.mdd = None

    def __str__(self):
        event_dict = self.to_dict()
        result = ""
        for key, item in event_dict.items():
            result += f"{key}={item} "
        return result