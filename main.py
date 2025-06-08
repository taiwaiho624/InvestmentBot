from MarketFeeder import MarketFeeder
from ValueAverageTradingBot import ValueAverageTradingBot
from datetime import date, timedelta, datetime

import argparse

if __name__ == '__main__':
    value_average_trading_bot = ValueAverageTradingBot(MarketFeeder())

    parser = argparse.ArgumentParser()

    parser.add_argument('--mode', type=str, help='replay or normal', required=True)
    parser.add_argument('--file', type=str, help='filename', required=False)
    parser.add_argument('--start_date', type=str, help='start', required=False, default=date.today().strftime('%Y%m%d'))
    parser.add_argument('--commit_file', type=bool, help='to write to file')
    parser.add_argument('--deriv_price', type=float, help='price_of_instrument', default=None)
    parser.add_argument('--cash_in', type=int, help='cash to put in')
    args = parser.parse_args()

    if args.file:
        value_average_trading_bot.file_name = f"output/{args.file}.xlsx"

    if args.commit_file:
        value_average_trading_bot.commit_file = True

    if args.cash_in:
        value_average_trading_bot.cash_in_per_month = args.cash_in

    if args.mode == 'replay':
        value_average_trading_bot.replay(start_date=args.start_date)
    elif args.mode == 'normal':
        value_average_trading_bot.normal(args.start_date, operation_price=args.deriv_price)
    elif args.mode == 'backtest_normal':
        start_date = datetime.strptime(args.start_date, '%Y%m%d')
        today = datetime.today()
        current_date = start_date
        while current_date <= today:
            value_average_trading_bot.normal(current_date.strftime('%Y%m%d'))
            current_date += timedelta(days=1)