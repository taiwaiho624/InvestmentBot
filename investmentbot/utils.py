import re
from datetime import datetime, timedelta

def find_numbers_in_str(str):
    return re.findall(r'\d+', str)

def get_month_by_day(day):
    month = f"{day[0:6]}01"
    return month

def get_previous_month_by_day(day):
    date_obj = datetime.strptime(day, '%Y%m%d')
    
    first_day_of_current_month = date_obj.replace(day=1)
    
    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
    
    return get_month_by_day(last_day_of_previous_month.strftime('%Y%m%d'))
