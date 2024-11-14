from MarketFeeder import MarketFeeder
from ValueAverageTradingBot import ValueAverageTradingBot

import argparse

if __name__ == '__main__':
    value_average_trading_bot = ValueAverageTradingBot(MarketFeeder())

    parser = argparse.ArgumentParser()
    parser.add_argument('--price', type=float, help='current price of the instrument')
    parser.add_argument('--record', type=bool, help='record the event')

    args = parser.parse_args()

    value_average_trading_bot.signal(price=args.price, record=args.record)