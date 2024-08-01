from SmartApi import SmartConnect #or from SmartApi.smartConnect import SmartConnect
from threading import Thread, Lock
from file_handler import read_file
from authentication import processLogin
from datetime import datetime, timedelta
import json
import time
import random
from rich.console import Console
from rich.table import Table
import shutil

sObj = processLogin()

config = {}
filtered_stocks = []
rows = []
cols = []
lock = Lock()

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


def TRADE_STOCK(**params):
    try:
        defaultParams = {
            "variety": "<STOCK-VAR>",
            "tradingsymbol": "<STOCK-SYMBOL>",
            "symboltoken": "<STOCK-TOKEN>",
            "transactiontype": "<STOCK-CALL>",
            "exchange": "<STOCK-AUTHORITY>",
            "ordertype": "<STOCK-OT>",
            "producttype": "<STOCK-PT>",
            "duration": "<STOCK-D>",
            "price": "<STOCK-PRICE>",
            "quantity": "<STOCK-QTY>"
            }

        defaultParams.update(params)
        sObj.placeOrder(defaultParams)
    except Exception as e:
        print(e)


def time_calc(days=0, hours=0, minutes=0, seconds=0, ttime='', replace=False):
    ttime = datetime.now() if ttime == '' else datetime.strptime(ttime, "%Y-%m-%d %H:%M")
    ttime = ttime - timedelta(days=abs(days)) if days < 0 else ttime + timedelta(days=days)
    ttime = ttime - timedelta(minutes=abs(minutes)) if minutes < 0 else ttime + timedelta(minutes=minutes)
    ttime = ttime - timedelta(minutes=abs(minutes)) if seconds < 0 else ttime + timedelta(seconds=seconds)
    if replace is True:
        ttime = ttime.replace(hour=abs(hours), minute=abs(minutes), second=seconds)
    return ttime.strftime("%Y-%m-%d %H:%M")


trading_params = read_file("trading_params.json")

def get_historic_data(historic_params, start_time,filename='garbage.txt', increments=trading_params["increment"]):
    stop_time = time_calc(days=-trading_params['latest'], hours=3, minutes=15, replace=True)
    stop_time = time_calc(minutes=increments, ttime=stop_time)
    print(start_time, stop_time, historic_params["symboltoken"])
    log_lines = [f"[{start_time}] Started Monitoring Stock...\n"]
    
    firstHigh = firstLow = target = stopLoss = None
    triggerHigh = triggerLow = None
    isSold = False
    waiting_for_sell = False
    EntryOnNext = False
    entry = None
    # historic_params["fromdate"] = start_time
    # historic_params["todate"] = time_calc(minutes=increments-1, ttime=start_time)
    # data = sObj.getCandleData(historic_params)
    # print(json.dumps(data, indent=4))
    while start_time != stop_time and not isSold:
        historic_params["fromdate"] = start_time
        historic_params["todate"] = time_calc(minutes=increments-1, ttime=start_time)
        data = sObj.getCandleData(historic_params)
        print(json.dumps(data, indent=4))
        [_, OPEN, high, low, close,_] = data['data'][0]

        if firstHigh is None and not isSold:
            firstHigh = high
            target = high + 2 * abs(low - high)
            stopLoss = low
            log_lines.append(f"[{start_time}] First Candle Data: OHLC({OPEN, high, low, close})\n")
            log_lines.append(f"[{start_time}] [BUY={close}] OHLC({OPEN, high, low, close})\n")
            waiting_for_sell = True

        elif not (firstHigh is None) and high >= target and waiting_for_sell and not isSold:
            waiting_for_sell = False
            isSold = True
            log_lines.append(f"[{start_time}] [SELL] [TARGET={stopLoss}] is Hit: OHLC({OPEN, high, low, close})\n")
            break

        elif not (firstHigh is None) and low <= stopLoss and waiting_for_sell and not isSold:
            waiting_for_sell = False
            isSold = True
            log_lines.append(f"[{start_time}] [SELL] [STOPLOSS={target}] is Hit: OHLC({OPEN, high, low, close})\n")
            break
    
        start_time = time_calc(minutes=increments, ttime=start_time)
        print(f"next candle time: {start_time}")
        # time.sleep(1)
        time.sleep(trading_params["increment"] * 60)
    else:
        if not isSold:
            log_lines.append(f"[{start_time}] [SELL] Selling the stock as time is 3:15\n")
    
    with open(filename, 'w') as f:
        f.writelines(log_lines)

if trading_params["testing"] is False and trading_params["historicData"] is True:
    read_filtered()
    start_time = time_calc(days=-trading_params['earliest'], hours=9, minutes=15, replace=True)
    threads = []
    for stock in filtered_stocks:
        historicParam={
            "exchange": stock['exch_seg'],
            "symboltoken": stock['token'],
            "interval": candle_time_mapping(trading_params["increment"])
            }
        thread = Thread(target=get_historic_data, args=(historicParam.copy(), start_time,f"historic/{stock['symbol']}.txt"))
        threads.append(thread)
        thread.start()
        time.sleep(1)

    for thread in threads:
        thread.join()


def convert_utc_to_ist(utc_time_str):
    # Parse the UTC time string to a datetime object
    utc_time = datetime.strptime(utc_time_str, "%d-%b-%Y %H:%M:%S")
    
    # IST is UTC + 5:30
    ist_offset = timedelta(hours=5, minutes=30)
    ist_time = utc_time + ist_offset
    
    # Format the IST time back to string
    ist_time_str = ist_time.strftime("%d-%b-%Y %H:%M:%S")
    return utc_time_str

def get_stopping_time(hour=3, minute=14):
    today = datetime.now()
    today = today.replace(hour=hour, minute=minute, second=0)
    return today.strftime("%d-%b-%Y %H:%M:%S")

def parse_ist_time(ist_time_str):
    return datetime.strptime(ist_time_str, "%d-%b-%Y %H:%M:%S")

def time_difference(time1, time2):
    time1 = parse_ist_time(time1)
    time2 = parse_ist_time(time2)
    
    difference = time1 - time2
    return difference.total_seconds()

def getFirstCandle(historicParam):
    data = sObj.getCandleData(historicParam)
    data = data['data'][0]
    return data

def trading_for_stock(stock, filename, index):
    try:
        token = stock['token']
        firstCandle = None
        OPEN = HIGH = LOW = CLOSE = ENTRY = None
        isCompleted = False
        log_lines = []
        stoppingTime = get_stopping_time(hour=15, minute=14)
        exitTime = get_stopping_time(hour=10, minute=45)
        candleMeet = False
        target = None
        stopLoss = None
        isBought = False
        isSold = False
        while not isCompleted:
            try:
                data = sObj.getMarketData(mode="FULL", exchangeTokens={"NSE": [f"{token}"]})
                data = data['data']['fetched'][0]
                ltp = float(data['ltp'])
                tradeTime = data['exchFeedTime']
                globals()['rows'][index] = [tradeTime, str(stock['symbol']), str(HIGH), str(target), str(stopLoss), str(ltp), "YES" if isBought else "NO", "YES" if isSold else "NO", "LIVE", "TBA"]

                if (not isBought and time_difference(tradeTime,exitTime) > 0) or time_difference(tradeTime,stoppingTime) > 0:
                    log_lines.append(f"[{convert_utc_to_ist(tradeTime)}][TIMEOUT] Preparing for exit...\n")
                    if not isBought:
                        log_lines.append(f"[NO-ENTRY-EXIT] No entry for stock\n")
                    else:
                        defaultParams = {
                        "variety": "NORMAL",
                        "tradingsymbol": f"{stock['symbol']}",
                        "symboltoken": f"{stock['token']}",
                        "transactiontype": "SELL",
                        "exchange": "NSE",
                        "ordertype": "LIMIT",
                        "producttype": "INTRADAY",
                        "duration": "DAY",
                        "price": f"{ltp}",
                        "quantity": "1"
                        }
                        TRADE_STOCK(**defaultParams)
                        isSold = True
                        log_lines.append(f"[SELL] selling the stock as end of market time\n")
                    log_lines.append(f"[STOPPING-MONITOR] Stopping monitoring for stock :-)\n")
                    if ENTRY:
                        profit = str(ltp - ENTRY)
                    else:
                        profit = str(ltp - HIGH)
                    globals()['rows'][index] = [tradeTime, str(stock['symbol']), str(HIGH), str(target), str(stopLoss), str(ltp), "YES" if isBought else "NO", "YES" if isSold else "NO", "TIMEOUT", profit]
                    break

                if firstCandle is None:
                    start_time = time_calc(hours=9, minutes=15, replace=True)
                    stop_time = time_calc(minutes=trading_params["increment"], ttime=start_time)
                    print(start_time, stop_time, candle_time_mapping(trading_params["increment"]))
                    historicParam={
                    "exchange": stock['exch_seg'],
                    "symboltoken": stock['token'],
                    "interval": candle_time_mapping(trading_params["increment"]),
                    "fromdate":start_time,
                    "todate":stop_time
                    }
                    [_, OPEN, high, low, close,_] = getFirstCandle(historicParam)
                    firstCandle = True
                    OPEN = OPEN
                    SIZE = abs(HIGH - LOW)
                    HIGH = round(high * 1.00025, 2)
                    LOW = low
                    CLOSE = close
                    candleMeet = True
                    target = round(HIGH + abs(HIGH - LOW), 2)
                    stopLoss = LOW
                    log_lines.append(f"{trading_params['increment']} Minute candle found: OHLC{OPEN, HIGH, LOW, CLOSE}\n")
                    log_lines.append(f"Calculated: Target = {target}, StopLoss = {stopLoss}\n")
                    if ((SIZE / LOW) * 100) > 1.5:
                        log_lines.append(f"Candle does not met requirement for <= 1.5%, Actuall: {((SIZE / LOW) * 100)}\n")
                        log_lines.append(f"[{tradeTime}] Exiting from maket for stock...\n")
                        globals()['rows'][index] = [tradeTime, str(stock['symbol']), str(HIGH), str(target), str(stopLoss), str(ltp), "NO", "NO", "EXIT@>1.5", "NIL"]
                        break
                
                elif firstCandle is not None and candleMeet is True and not isBought:
                    if ltp >= HIGH:
                        log_lines.append(f"[{convert_utc_to_ist(tradeTime)}][BUY] Price={ltp}\n")
                        isBought = True
                        defaultParams = {
                        "variety": "NORMAL",
                        "tradingsymbol": f"{stock['symbol']}",
                        "symboltoken": f"{stock['token']}",
                        "transactiontype": "BUY",
                        "exchange": "NSE",
                        "ordertype": "LIMIT",
                        "producttype": "INTRADAY",
                        "duration": "DAY",
                        "price": f"{ltp}",
                        "quantity": "1"
                        }
                        TRADE_STOCK(**defaultParams)
                        ENTRY = ltp
                
                elif firstCandle is not None and candleMeet is True and isBought:
                    if ltp >= target:
                        log_lines.append(f"[{convert_utc_to_ist(tradeTime)}][SELL] Target = {target} is Hit, price = {ltp}\n")
                        log_lines.append(f"[STOPPING-MONITOR] Stopping monitoring for stock :-)")
                        defaultParams = {
                        "variety": "NORMAL",
                        "tradingsymbol": f"{stock['symbol']}",
                        "symboltoken": f"{stock['token']}",
                        "transactiontype": "SELL",
                        "exchange": "NSE",
                        "ordertype": "LIMIT",
                        "producttype": "INTRADAY",
                        "duration": "DAY",
                        "price": f"{ltp}",
                        "quantity": "1"
                        }
                        TRADE_STOCK(**defaultParams)
                        isSold = True
                        if ENTRY:
                            profit = str(ltp - ENTRY)
                        else:
                            profit = str(ltp - HIGH)
                        globals()['rows'][index] = [tradeTime, str(stock['symbol']), str(HIGH), str(target), str(stopLoss), str(ltp), "YES" if isBought else "NO", "YES" if isSold else "NO", "TARGET", profit]
                        break
                    if ltp <= stopLoss:
                        log_lines.append(f"[{convert_utc_to_ist(tradeTime)}][SELL] StopLoss = {stopLoss} is Met, price = {ltp}\n")
                        log_lines.append(f"[STOPPING-MONITOR] Stopping monitoring for stock :-)")
                        defaultParams = {
                        "variety": "NORMAL",
                        "tradingsymbol": f"{stock['symbol']}",
                        "symboltoken": f"{stock['token']}",
                        "transactiontype": "SELL",
                        "exchange": "NSE",
                        "ordertype": "LIMIT",
                        "producttype": "INTRADAY",
                        "duration": "DAY",
                        "price": f"{ltp}",
                        "quantity": "1"
                        }
                        TRADE_STOCK(**defaultParams)
                        isSold = True
                        if ENTRY:
                            profit = str(ltp - ENTRY)
                        else:
                            profit = str(ltp - HIGH)
                        globals()['rows'][index] = [tradeTime, str(stock['symbol']), str(HIGH), str(target), str(stopLoss), str(ltp), "YES" if isBought else "NO", "YES" if isSold else "NO", "STOPLOSS", profit]
                        break            
                time.sleep(3)
            except Exception as e:
                print(e)
                print(token)
                time.sleep(9 + random.uniform(0.2, 0.9))
        with open(filename, 'w') as f:
            f.writelines(log_lines)
            globals()['rows'][index] = [tradeTime, str(stock['symbol']), str(HIGH), str(target), str(stopLoss), str(ltp), "YES" if isBought else "NO", "YES" if isSold else "NO", "LIVE", "TBA"]
        return
    except Exception as e:
        print(e)
        print(token)
        with open(filename, 'w') as f:
            f.writelines(log_lines)
        globals()['rows'][index] = ["ERROR", str(stock['symbol']), str(HIGH), str(target), str(stopLoss), str(ltp), "YES" if isBought else "NO", "YES" if isSold else "NO", "N/A", "N/A"]
        return


def wait_till_next_minute(delta=0):
    import time

    print("waiting till the next minute starts...")
    time.sleep(60 - delta - time.localtime().tm_sec)


def read_stocks_and_filter(file_path, filterit=True):
    import pandas as pd
    # Load the CSV file
    data = pd.read_csv(file_path)
    
    # Convert the '% Chg' column to numeric values
    data['% Chg'] = data['% Chg'].str.rstrip('%').astype(float)
    
    # Filter the stocks with percentage change between 1.25 and 2.5
    filtered_stocks = data.copy()
    if filterit:
        filtered_stocks = data[(data['% Chg'] >= 1.4) & (data['% Chg'] <= 2.5)]
    
    # Append "-EQ" to the stock symbols
    filtered_stocks['Symbol'] = filtered_stocks['Symbol'] + '-EQ'
    
    # Get the list of filtered stock symbols
    stock_symbols = filtered_stocks['Symbol'].tolist()
    
    return stock_symbols

def wait_for_stocks_files():
    data = None
    import os
    
    files_phase_1 = os.listdir("filter_phase_1")
    files_phase_1 = [f for f in files_phase_1 if os.path.isfile(os.path.join("filter_phase_1", f))]
    
    data = []
    for file in files_phase_1:
        data.extend(read_stocks_and_filter(f"filter_phase_1/{file}"))
    
    files_phase_2 = os.listdir("filter_phase_2")
    files_phase_2 = [f for f in files_phase_2 if os.path.isfile(os.path.join("filter_phase_2", f))]


    for file in files_phase_2:
        data.extend(read_stocks_and_filter(f"filter_phase_2/{file}", False))
    
    data = list(set(data))
    
    print("saving stocks to loacal filter json file...")
    with open("filter_local.json", 'w') as file:
        demo = {
            "symbol":data
        }

        json.dump(demo, file)
    
    print("filtering the stocks and saving important information...")
    os.system("python utility.py")
    # os.system(f"rename {trading_params['increment']}m.csv {trading_params['increment']}m-old.csv")


def ping_console_table_thread():

    console = Console()
    while True:
        table = Table(title="Stock Monitoring Console")
        for i, col in enumerate(globals()['cols']):
            if i % 2 == 0:
                table.add_column(col, justify="center", style="cyan")
            else:
                table.add_column(col, justify="center", style="magenta")

        for row in globals()['rows']:
            table.add_row(*row)    
        console.clear()
        console.print(table)
        time.sleep(1)


if trading_params["testing"] is False and trading_params["historicData"] is False:
    wait_for_stocks_files()
    read_filtered()
    sObj.timeout = trading_params["increment"] * 60
    threads = []
    globals()['rows'] = [[] for _ in range(len(filtered_stocks))]
    for index, stock in enumerate(filtered_stocks):
        thread = Thread(target=trading_for_stock, args=(stock, f"liveTrading/{stock['symbol']}.txt", index))
        threads.append(thread)
        thread.start()
        time.sleep(1)
    

    
    globals()['rows'] = [[] for _ in range(len(threads))]
    globals()['cols'] = ["Time", "Stock", "Entry", "Target", "StopLoss", "LTP", "isBought", "isSold", "TradeType", "Profit"]

    thread = Thread(target=ping_console_table_thread)
    threads.append(thread)
    thread.start()

    for thread in threads:
        thread.join()
 
if trading_params["testing"] is True:
    print("....buy sell stock demo....")

    for i in range(2):
        if i % 2 == 0:
            defaultParams = {
            "variety": "NORMAL",
            "tradingsymbol": "ASHOKLEY-EQ",
            "symboltoken": "212",
            "transactiontype": "BUY",
            "exchange": "NSE",
            "ordertype": "LIMIT",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "price": "16.59",
            "quantity": "1"
            }
            data = sObj.getMarketData(mode="FULL", exchangeTokens={"NSE": ["212"]})
            data = data['data']['fetched'][0]
            defaultParams['price'] = data['ltp']
            TRADE_STOCK(**defaultParams)
            print("Sleeping for 10 seconds for sell....")
            time.sleep(10)
        elif i % 2:
            defaultParams = {
            "variety": "NORMAL",
            "tradingsymbol": "ASHOKLEY-EQ",
            "symboltoken": "212",
            "transactiontype": "SELL",
            "exchange": "NSE",
            "ordertype": "LIMIT",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "price": "16.59",
            "quantity": "1"
            }
            data = sObj.getMarketData(mode="FULL", exchangeTokens={"NSE": ["212"]})
            data = data['data']['fetched'][0]
            defaultParams['price'] = data['ltp']
            TRADE_STOCK(**defaultParams)
