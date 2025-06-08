import logging
import datetime
import os 

def init(appName="default"):
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    dir = "/home/test/investmentbot/log/" + date + "/"
    os.makedirs(dir, exist_ok=True)
    file_name = dir + datetime.datetime.now().strftime(appName + '_%Y_%m_%d-%H%M%S.log')
    logging.basicConfig(
        format='%(asctime)s.%(msecs)03d %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO,
        handlers=[
            logging.FileHandler(file_name),
            logging.StreamHandler()
        ]
    )
