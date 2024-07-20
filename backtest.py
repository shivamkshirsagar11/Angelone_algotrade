from threading import Thread
from file_handler import read_file
from authentication import processLogin
from datetime import datetime, timedelta
import json
import time
import logging

# Create a logger
backtest_main_logger = logging.getLogger('backtest_main_logger')
backtest_main_logger.setLevel(logging.DEBUG)

# Create a file handler
fh = logging.FileHandler('backtest_main_logger.log')
fh.setLevel(logging.DEBUG)

# Create a formatter and set it to the handler
formatter = logging.Formatter('%(levelname)s - %(asctime)s - %(message)s')
fh.setFormatter(formatter)

# Add the handler to the backtest_main_logger
backtest_main_logger.addHandler(fh)

backtest_main_logger.info("Starting Authentication and login")

sObj = processLogin()

backtest_main_logger.info("Authentication Successfull")

config = {}
filtered_stocks = []

def read_filtered():
    globals()['filtered_stocks'] = read_file('filtered_dict_local.json')

def read_secreats():
    globals()['config'] = read_file('complete_config_local.json')

def candle_time_mapping(increment):
    candle_times = {
        1:"ONE_MINUTE",
        3:"THREE_MINUTE",
        5:"FIVE_MINUTE",
        10:"TEN_MINUTE",
        15:"FIFTEEN_MINUTE",
        30:"THIRTY_MINUTE",
        60:"ONE_HOUR",
        1440:"ONE_DAY"
    }
    return candle_times[increment]


read_secreats()

backtest_params = read_file("backtest_params.json")


def getHistoricOHLC(params):
    try:
        backtest_main_logger.info(f"[getHistoricOHLC] getting candle data")
        data = sObj.getCandleData(historicDataParams=params)
        [_, OPEN, high, low, close,_] = data['data'][0]
        backtest_main_logger.info(f"[getHistoricOHLC] candle data fetched successfull")
        return OPEN, high, low, close
    except Exception as e:
        backtest_main_logger.error(f"[getHistoricOHLC] ERROR={e}")
        return -1, -1, -1, -1

def time_calc(days=0, hours=0, minutes=0, seconds=0, ttime='', replace=False):
    ttime = datetime.now() if ttime == '' else datetime.strptime(ttime, "%Y-%m-%d %H:%M")
    ttime = ttime - timedelta(days=abs(days)) if days < 0 else ttime + timedelta(days=days)
    if not replace:
        ttime = ttime - timedelta(minutes=abs(minutes)) if minutes < 0 else ttime + timedelta(minutes=minutes)
        ttime = ttime - timedelta(minutes=abs(minutes)) if seconds < 0 else ttime + timedelta(seconds=seconds)
    if replace is True:
        ttime = ttime.replace(hour=abs(hours), minute=abs(minutes), second=seconds)
    return ttime.strftime("%Y-%m-%d %H:%M")

def backtest(instrument, earliest):
    backtest_main_logger.info(f"[backtest] backtesting for {instrument['name']}")

    first_candle = False
    fromdate = None
    todate = None
    trade_config = {
        "open":None,
        "high":None,
        "low":None,
        "close":None,
        "target":None,
        "stoploss":None
    }

    if not first_candle:
        fromdate = time_calc(days = -earliest, minutes=15, hours=12, replace=True)
        todate = time_calc(ttime=fromdate, minutes=44, hours=12, replace=True)
        backtest_main_logger.info(f"[backtest][first_candle] {instrument['name']} fromdate={fromdate}, todate={todate}")
    
    historicParam={
    "exchange": instrument['exch_seg'],
    "symboltoken": instrument['token'],
    "interval": candle_time_mapping(backtest_params["increment"]),
    "fromdate":fromdate,
    "todate":todate
    }

    backtest_main_logger.info(f"[backtest]{instrument['name']} fromdate={fromdate}, todate={todate}, getting candle data")
    ohlc = getHistoricOHLC(historicParam)
    if not first_candle and ohlc[0] == -1:
        backtest_main_logger.critical(f"[backtest] Some error occured so skipping this day")
        return
    else:
        print(earliest, ohlc)


def iterate_filtered_stocks():
    backtest_main_logger.info("[iterate_filtered_stocks] reading filtered stocks")
    read_filtered()
    backtest_main_logger.info("[iterate_filtered_stocks] filtered stocks read")
    count = 0
    for backtime in range(backtest_params['earliest'], 0, -1):
        backtest_main_logger.info(f"[iterate_filtered_stocks] starting backtesting for -{backtime}")
        for instrument in filtered_stocks:
            count += 1
            backtest_main_logger.info(f"[iterate_filtered_stocks] starting backtest for {instrument['name']}")
            backtest(instrument, backtime)
            if count % 3 == 0:
                backtest_main_logger.info("[iterate_filtered_stocks] Sleeping as limit rate will not hit")
                time.sleep(1)

if __name__ == "__main__":
    backtest_main_logger.info("[mainif] Starting iterating over earliest time")
    iterate_filtered_stocks()