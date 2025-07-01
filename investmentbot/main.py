from investmentbot.ValueAverageTradingBot import ValueAverageTradingBot
from investmentbot.Excel import Excel
import investmentbot.logger
from datetime import date, timedelta, datetime
import logging
import argparse

def main():
    investmentbot.logger.init("investment_bot")
    value_average_trading_bot = ValueAverageTradingBot()

    parser = argparse.ArgumentParser()

    parser.add_argument('--mode', type=str, help='replay or normal', required=True)
    parser.add_argument('--file', type=str, help='filename', required=False)
    parser.add_argument('--start_date', type=str, help='start', required=False, default=date.today().strftime('%Y%m%d'))
    parser.add_argument('--end_date', type=str, help='end', required=False, default=date.today().strftime('%Y%m%d'))
    parser.add_argument('--commit',  action='store_true', help='to write to file')
    parser.add_argument('--daily',  action='store_true', help='store daily event')
    parser.add_argument('--latest_is_previous', action='store_true', help='store daily event')
    parser.add_argument('--price', type=float, help='price_of_instrument', default=None)
    parser.add_argument('--underlying_price', type=float, help='underlying_price_of_instrument', default=None)
    parser.add_argument('--cash_in', type=int, help='cash to put in')
    parser.add_argument('--target_value', type=float)
    
    args = parser.parse_args()

    if args.file:
        excel = Excel(args.file)
    
    if args.target_value:
        value_average_trading_bot.target_value = args.target_value
        value_average_trading_bot.cash = args.target_value
        value_average_trading_bot.cost = args.target_value
    if args.cash_in:
        value_average_trading_bot.cash_in_per_month = args.cash_in

    if args.daily:
        value_average_trading_bot.record_daily = args.daily

    if args.latest_is_previous:
        value_average_trading_bot.latest_is_previous = args.latest_is_previous

    if args.mode == 'replay':
        ret = value_average_trading_bot.replay(start_date=args.start_date, end_date=args.end_date)
    elif args.mode == 'normal':
        value_average_trading_bot.init_from_file(excel.from_file())
        ret = value_average_trading_bot.normal(args.start_date, operation_price=args.price, underlying_price=args.underlying_price)
    elif args.mode == 'backtest_normal':
        start_date = datetime.strptime(args.start_date, '%Y%m%d')
        today = datetime.today()
        current_date = start_date
        while current_date <= today:
            ret = value_average_trading_bot.normal(current_date.strftime('%Y%m%d'))
            current_date += timedelta(days=1)
    
    if ret < 0:
        return

    if args.file and args.commit:
        if args.mode == 'replay':
            excel.clear_sheets()
            excel.to_file(value_average_trading_bot.events, value_average_trading_bot.get_params(), stat=value_average_trading_bot.stat.get(), with_header=True)
        elif args.mode == 'normal':
            excel.to_file(value_average_trading_bot.events, value_average_trading_bot.get_params(), with_header=False)


if __name__ == '__main__':
    main()  