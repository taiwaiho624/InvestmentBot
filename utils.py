import re

def find_numbers_in_str(str):
    return re.findall(r'\d+', str)