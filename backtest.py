from threading import Thread
from file_handler import read_file
from authentication import processLogin
from datetime import datetime, timedelta
import json
import time
import logging
import csv

# Create a logger
backtest_main_logger = logging.getLogger('backtest_main_logger')
backtest_main_logger.setLevel(logging.DEBUG)

# Create a file handler
fh = logging.FileHandler('backtest_main_logger.log', mode='w')
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
    ttime = ttime - timedelta(minutes=abs(minutes)) if minutes < 0 else ttime + timedelta(minutes=minutes)
    ttime = ttime - timedelta(minutes=abs(minutes)) if seconds < 0 else ttime + timedelta(seconds=seconds)
    if replace is True:
        ttime = ttime.replace(hour=abs(hours), minute=abs(minutes), second=seconds)
    return ttime.strftime("%Y-%m-%d %H:%M")

def get_stopping_time(hour=3, minute=14, today=''):
    today = datetime.now() if today == '' else datetime.strptime(today, "%Y-%m-%d %H:%M")
    today = today.replace(hour=hour, minute=minute, second=0)
    return today.strftime("%Y-%m-%d %H:%M")

def parse_ist_time(ist_time_str):
    return datetime.strptime(ist_time_str, "%Y-%m-%d %H:%M")

def time_difference(time1, time2):
    time1 = parse_ist_time(time1)
    time2 = parse_ist_time(time2)
    
    difference = time1 - time2
    return difference.total_seconds()

def csv_writer(data, filename):
    """
    Writes data to a CSV file.
    
    Parameters:
    data (list of lists): The data to write to the CSV file, where each sublist represents a row.
    filename (str): The name of the CSV file to write to.
    """
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(data)

def backtest(instrument, earliest):
    backtest_main_logger.info(f"[backtest] backtesting for {instrument['name']}")
    increment = backtest_params["increment"]

    first_candle = False
    first_time_after_first_candle = True
    trigger_candle = False
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
    stop_time = get_stopping_time(hour=3, minute=15)
    entry_time = ''
    exit_time = ''
    trade_type = ''
    entry = ''
    exitt = ''
    profit = ''
    csv_lines = []
    waiting_for_sell = True
    sold = False
    bought = False
    error = False
    ohlc = None

    while True:
        if not first_candle:
            fromdate = time_calc(days = -earliest, minutes=15, hours=12, replace=True)
            todate = time_calc(ttime=fromdate, minutes=45, hours=12, replace=True)
            stop_time = get_stopping_time(hour=15, minute=15, today=fromdate)
            backtest_main_logger.info(f"[backtest][first_candle] {instrument['name']} fromdate={fromdate}, todate={todate}, {stop_time}")
        
        else:
            if first_time_after_first_candle:
                fromdate = todate
                todate = time_calc(ttime=fromdate, minutes=increment)
                first_time_after_first_candle = False
            else:
                fromdate = todate
                todate = time_calc(ttime=fromdate, minutes=increment)
        
        if time_difference(fromdate, stop_time) >= 0:
            backtest_main_logger.info(f"[backtest][time difference] {fromdate}:{todate}, {time_difference(fromdate, stop_time)}")
            break
        
        historicParam={
        "exchange": instrument['exch_seg'],
        "symboltoken": instrument['token'],
        "interval": candle_time_mapping(increment),
        "fromdate":fromdate,
        "todate":todate
        }

        backtest_main_logger.info(f"[backtest]{instrument['name']} fromdate={fromdate}, todate={todate}, getting candle data")
        ohlc = getHistoricOHLC(historicParam)
        if ohlc and not first_candle and ohlc[0] == -1:
            backtest_main_logger.critical(f"[backtest] Some error occured so skipping this day")
            error = True
            break
        elif not first_candle:
            first_candle = True
            trade_config = {
                "open":None,
                "high":None,
                "low":None,
                "close":None,
                "target":None,
                "stoploss":None
            }
            trade_config["open"] = ohlc[0]
            trade_config["high"] = ohlc[1]
            trade_config["low"] = ohlc[2]
            trade_config["close"] = ohlc[3]
            trade_config["stoploss"] = trade_config["high"] - (abs(trade_config["high"] - trade_config['low']) // 2)
            increment = 3
            first_candle = True
            continue
        elif first_candle and not trigger_candle:
            if ohlc[-1] >= trade_config["high"]:
                trigger_candle = True
                trade_config["target"] = ohlc[1] + abs(ohlc[1] - trade_config['low'])
                entry_time = fromdate
                entry = ohlc[1]
                bought = True
        elif first_candle and trigger_candle and waiting_for_sell:
            if ohlc[-1] >= trade_config['target']:
                exit_time = fromdate
                exitt = ohlc[-1]
                trade_type = "TARGET"
                profit = ohlc[-1] - trade_config['high']
                csv_lines = [entry_time, exit_time, trade_type, entry, exitt, profit]
                sold = True
                break
            if ohlc[-1] <= trade_config['stoploss']:
                exit_time = fromdate
                exitt = ohlc[-1]
                trade_type = "STOPLOSS"
                profit = ohlc[-1] - trade_config['high']
                csv_lines = [entry_time, exit_time, trade_type, entry, exitt, profit]
                sold = True
                break
        time.sleep(1)
    if not error and not sold and bought:
        exit_time = stop_time
        exitt = ohlc[-1]
        trade_type = "EXIT_3_15"
        profit = ohlc[-1] - trade_config['high']
        csv_lines = [entry_time, exit_time, trade_type, entry, exitt, profit]
    return csv_lines


def iterate_filtered_stocks():
    sObj.timeout = 300
    backtest_main_logger.info("[iterate_filtered_stocks] reading filtered stocks")
    read_filtered()
    backtest_main_logger.info("[iterate_filtered_stocks] filtered stocks read")
    count = 0
    for instrument in filtered_stocks:
        backtest_main_logger.info(f"[iterate_filtered_stocks] starting backtest for {instrument['name']}")
        data = []
        csv_header = ["Entry Time", "Exit Time", "Trade Type", "Entry", "Exit", "Profit"]
        data.append(csv_header.copy())
        filename = f"backtest/{instrument['name']}.csv"
        for backtime in range(backtest_params['earliest'], 0, -1):
            count += 1
            backtest_main_logger.info(f"[iterate_filtered_stocks] starting backtesting for -{backtime}")
            result_for_day = backtest(instrument, backtime)
            if result_for_day:
                data.append(result_for_day.copy())
        csv_writer(data, filename)

if __name__ == "__main__":
    backtest_main_logger.info("[mainif] Starting iterating over earliest time")
    iterate_filtered_stocks()