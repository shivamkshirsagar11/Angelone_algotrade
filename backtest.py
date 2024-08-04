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
        return data['data']
    except Exception as e:
        backtest_main_logger.error(f"[getHistoricOHLC] ERROR={e}")
        return []

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
    if time1 and time2:
        time1 = parse_ist_time(time1)
        time2 = parse_ist_time(time2)
        
        difference = time1 - time2
        return difference.total_seconds()
    return 0

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

def batchwise_get_candle_from_bulk(candledata, bind_candles, iterated_candles, start_time):
    backtest_main_logger.info(f"batchwise getting batches of candles...[{start_time}]")
    count = 0
    MIN, MAX, OPEN, CLOSE, Date = float("inf"), float("-inf"), None, None, None

    while iterated_candles < len(candledata) and count != bind_candles:
        [Date, O, H, L, C,_] = candledata[iterated_candles]
        Date = datetime.strptime(Date, "%Y-%m-%dT%H:%M:%S%z")
        Date = Date.strftime("%Y-%m-%d %H:%M")
        if time_difference(Date, start_time) < 0:
            backtest_main_logger.info(f"[SKIP] {Date} till {start_time}")
            iterated_candles += 1
        else:
            CLOSE = C
            MIN = min(L, MIN)
            MAX = max(H, MAX)
            if OPEN is None:
                backtest_main_logger.info(f"batchwise getting batches of candles starting[{Date}]")
                OPEN = O
            count += 1
            iterated_candles += 1
    return OPEN, MAX, MIN, CLOSE, iterated_candles, Date

def backtest(instrument, candles, earliest):
    backtest_main_logger.info(f"[backtest] backtesting for {instrument['name']}")
    increment = backtest_params["fi"]

    first_candle = False
    trigger_candle = False
    todate = None
    trade_config = {
        "open":None,
        "high":None,
        "low":None,
        "close":None,
        "target":None,
        "stoploss":None,
        "entry":None
    }
    entry_time = ''
    exit_time = ''
    trade_type = ''
    entry = ''
    exitt = ''
    profit = ''
    csv_lines = []
    sold = False
    bought = False
    error = False
    ohlc = None
    bind = 15
    iterated_candles = 0
    start_time = time_calc(days = -earliest, minutes=backtest_params["start_time_min"], hours=backtest_params["start_time_hr"], replace=True)
    stop_time = get_stopping_time(hour=backtest_params["end_time_hr"], minute=backtest_params["end_time_min"], today=start_time)
    TRADECALL = None
    while True:
        data = batchwise_get_candle_from_bulk(candles, increment, iterated_candles, start_time)
        ohlc = data[:4]
        iterated_candles, fromdate = data[4:]
        backtest_main_logger.info(f"[backtest][{fromdate}] data={data}")

        if ohlc and not first_candle and ohlc[0] is None:
            backtest_main_logger.critical(f"[backtest] Some error occured so skipping this day")
            error = True
            break

        if time_difference(fromdate, stop_time) >= 0:
            backtest_main_logger.info(f"[backtest][time difference] {fromdate}:{stop_time}, {time_difference(fromdate, stop_time)}")
            break

        if first_candle and (not bought and not sold):
            SIZE = abs(trade_config['high'] - trade_config['low'])
            if ohlc[0] and ohlc[-1] >= trade_config['high']:
                TRADECALL = "BUY"
                trade_config["target"] = round(trade_config['high'] + SIZE * backtest_params['target_margin'], 2)
                trade_config["stoploss"] = round(trade_config['low'] - SIZE * backtest_params['stoploss_margin'], 2)
                if SIZE >= backtest_params['candle_size']:
                    trade_config["target"] = round(trade_config['high'] + backtest_params['target_margin_second'] * SIZE, 2)
                    trade_config["stoploss"] = round(trade_config['low'] - SIZE * backtest_params['stoploss_margin_second'], 2)
                trade_config["entry"] = trade_config['high']
            elif ohlc[0] and ohlc[-1] <= trade_config['high']:
                TRADECALL = "SELL"
                trade_config["target"] = round(trade_config["low"] - SIZE * backtest_params['target_margin'], 2)
                trade_config["stoploss"] = round(trade_config["high"] - SIZE * backtest_params['stoploss_margin'], 2)
                if SIZE >= backtest_params['candle_size']:
                    trade_config["target"] = round(trade_config["low"] - backtest_params['target_margin_second'] * SIZE, 2)
                    trade_config["stoploss"] = round(trade_config['high'] - SIZE * backtest_params['stoploss_margin_second'], 2)
                trade_config["entry"] = trade_config["low"]

        if not first_candle:
            first_candle = True
            trade_config["open"] = ohlc[0]
            trade_config["high"] = ohlc[1]
            trade_config["low"] = ohlc[2]
            trade_config["close"] = ohlc[3]
            increment = backtest_params["si"]
            first_candle = True
        elif TRADECALL == "BUY" and first_candle and not bought:
            if ohlc[0] >= trade_config['entry']:
                entry_time = fromdate
                entry = ohlc[0]
                bought = True
        elif TRADECALL == "BUY" and first_candle and bought:
            if ohlc[0] >= trade_config['target']:
                exit_time = fromdate
                exitt = ohlc[0]
                trade_type = "TARGET"
                profit = ohlc[0] - entry
                csv_lines = [TRADECALL, entry_time, exit_time, trade_type, entry, exitt, round(profit, 2)]
                sold = True
                return csv_lines
            if ohlc[0] <= trade_config['stoploss']:
                exit_time = fromdate
                exitt = ohlc[0]
                trade_type = "STOPLOSS"
                profit = ohlc[0] - entry
                csv_lines = [TRADECALL, entry_time, exit_time, trade_type, entry, exitt, round(profit, 2)]
                sold = True
                return csv_lines
        elif TRADECALL == "SELL" and first_candle and not sold:
            if ohlc[-1] <= trade_config['entry']:
                entry_time = fromdate
                entry = ohlc[0]
                sold = True
        elif TRADECALL == "SELL" and first_candle and sold:
            if ohlc[0] <= trade_config['target']:
                exit_time = fromdate
                exitt = ohlc[0]
                trade_type = "TARGET"
                profit = entry - ohlc[0]
                csv_lines = [TRADECALL, entry_time, exit_time, trade_type, entry, exitt, round(profit, 2)]
                bought = True
                return csv_lines
            if ohlc[0] >= trade_config['stoploss']:
                exit_time = fromdate
                exitt = ohlc[0]
                trade_type = "STOPLOSS"
                profit = entry - ohlc[0]
                csv_lines = [TRADECALL, entry_time, exit_time, trade_type, entry, exitt, round(profit, 2)]
                bought = True
                return csv_lines
    if ohlc[0] and TRADECALL == "BUY" and not error and (not sold) and bought:
        exit_time = stop_time
        exitt = ohlc[-1]
        trade_type = "EXIT_3_15"
        profit = ohlc[-1] - entry
        csv_lines = [TRADECALL, entry_time, exit_time, trade_type, entry, exitt, round(profit, 2)]
    elif ohlc[0] and TRADECALL == "SELL" and not error and (not bought) and sold:
        exit_time = stop_time
        exitt = ohlc[-1]
        trade_type = "EXIT_3_15"
        profit = entry - ohlc[-1]
        csv_lines = [TRADECALL, entry_time, exit_time, trade_type, entry, exitt, round(profit, 2)]
    return csv_lines

def group_day_wise(data):
    from collections import defaultdict
    grouped = defaultdict(list)
    backtest_main_logger.info(f"grouping {len(data)} number of candles by days")

    for row in data:
        date = row[0].split("T")[0]
        grouped[date].append(row)
    
    return grouped

def get_dynamic_data(days, stock):
    backtest_main_logger.info(f"Getting dynamic data in bulk for -{days} days")
    data = []
    todate_date = -1
    historicParam={
        "exchange": stock['exch_seg'],
        "symboltoken": stock['token'],
        "interval": candle_time_mapping(1)
        }
    while days >= 0 and todate_date < 0:
        todate_date = min(0, -days + 30)
        fromdate = time_calc(days = -days, minutes=15, hours=9, replace=True)
        todate = time_calc(days = todate_date, minutes=15, hours=15, replace=True)
        backtest_main_logger.info(f"Getting dynamic data for {fromdate} -> {todate}")
        historicParam['fromdate'] = fromdate
        historicParam['todate'] = todate
        data.extend(getHistoricOHLC(historicParam))
        days = abs(todate_date) - 1
        time.sleep(1.5)
    
    return group_day_wise(data)

def date_difference(date_str):
    # Parse the given date string
    given_date = datetime.strptime(date_str, '%Y-%m-%d')
    # Get today's date
    today_date = datetime.today()
    # Calculate the difference in days
    difference = today_date - given_date
    return difference.days

def iterate_filtered_stocks():
    sObj.timeout = 300
    backtest_main_logger.info("[iterate_filtered_stocks] reading filtered stocks")
    read_filtered()
    backtest_main_logger.info("[iterate_filtered_stocks] filtered stocks read")
    for instrument in filtered_stocks:
        backtest_main_logger.info(f"[iterate_filtered_stocks] starting backtest for {instrument['name']}")
        data = []
        csv_header = ["FIRSTCALL", "Entry Time", "Exit Time", "Trade Type", "Entry", "Exit", "Profit"]
        data.append(csv_header.copy())
        filename = f"backtest/{instrument['name']}_{backtest_params['file_suffix']}.csv"
        stocks_data = get_dynamic_data(backtest_params['earliest'], instrument)
        for back_day, candles in stocks_data.items():
            backtime = date_difference(back_day)
            backtest_main_logger.info(f"[iterate_filtered_stocks] starting backtesting for -{backtime}")
            result_for_day = backtest(instrument, candles, backtime)
            if result_for_day:
                data.append(result_for_day.copy())
        csv_writer(data, filename)

if __name__ == "__main__":
    backtest_main_logger.info("[mainif] Starting iterating over earliest time")
    iterate_filtered_stocks()
    # fromdate = time_calc(days = -30, minutes=15, hours=9, replace=True)
    # todate = time_calc(days = -1, minutes=30, hours=15, replace=True)
    # historicParam={
    #     "exchange": "NSE",
    #     "symboltoken": "99926009",
    #     "interval": candle_time_mapping(1),
    #     "fromdate":fromdate,
    #     "todate":todate
    #     }
    # data = getHistoricOHLC(historicParam)

    # print(f"Getting 30 days data")
    # unique = set()
    # for row in data:
    #     print(row)
    #     date = row[0].split("T")[0]
    #     unique.add(date)
    
    # print(f"start date={fromdate}")
    # print(f"end date={todate}")
    # for d in unique:
    #     print(d)

