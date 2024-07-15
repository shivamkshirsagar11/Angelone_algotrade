from SmartApi import SmartConnect #or from SmartApi.smartConnect import SmartConnect
from threading import Thread
from file_handler import read_file
from authentication import processLogin
from datetime import datetime, timedelta
import json
import time

sObj = processLogin()

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


def BUY_STOCK(**params):
    print("Buying stock..................")
    defaultParams = {
        "variety": "NORMAL",
        "tradingsymbol": "IDEA-EQ",
        "symboltoken": "14366",
        "transactiontype": "BUY",
        "exchange": "NSE",
        "ordertype": "LIMIT",
        "producttype": "INTRADAY",
        "duration": "DAY",
        "price": "16.59",
        "squareoff": "0",
        "stoploss": "0",
        "quantity": "1"
        }

    defaultParams.update(params)
    orderid = sObj.placeOrder(defaultParams)
    print("Stock bought..................")
    print(f"Order ID: {orderid}")

# BUY_STOCK()
# time.sleep(100)
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
    start_time = time_calc(days=-trading_params['earliest'], hours=9, minutes=30, replace=True)
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
    return ist_time_str

def get_stopping_time():
    today = datetime.now()
    today = today.replace(hour=3, minute=14, second=0)
    return today.strftime("%d-%b-%Y %H:%M:%S")

def parse_ist_time(ist_time_str):
    return datetime.strptime(ist_time_str, "%d-%b-%Y %H:%M:%S")

def time_difference(time1, time2, isLive=False):
    time1 = parse_ist_time(time1)
    time2 = parse_ist_time(time2)
    if not isLive:
        difference = abs(time2 - time1)
    else:
        difference = time1 - time2
    return difference.total_seconds()

def trading_for_stock(token, filename):
    firstCandle = None
    firstHigh = firstLow = None
    firstOpen = None
    OPEN = HIGH = LOW = CLOSE = None
    candleTime = 0
    isCompleted = False
    log_lines = []
    stoppingTime = get_stopping_time()
    candleMeet = False
    target = None
    stopLoss = None
    while not isCompleted:
        try:
            data = sObj.getMarketData(mode="FULL", exchangeTokens={"NSE": [f"{token}"]})
            data = data['data']['fetched'][0]
            ltp = float(data['ltp'])
            tradeTime = data['exchFeedTime']
            print("Current time: ", convert_utc_to_ist(tradeTime))
            if time_difference(tradeTime, stoppingTime, True) <= 0:
                log_lines.append(f"[{convert_utc_to_ist(tradeTime)}]No exit for today so sqaring off for 3:15\n")
                break
            if firstCandle is None:
                firstCandle = tradeTime
                firstHigh = ltp
                firstLow = ltp
                firstOpen = ltp
                OPEN = firstOpen
            elif firstCandle and candleMeet is False:
                if candleTime < trading_params["increment"] * 60:
                    HIGH = max(firstHigh,ltp)
                    LOW = min(firstLow, ltp)
                    candleTime = time_difference(firstCandle, tradeTime)
                
                if candleTime >= trading_params["increment"] * 60:
                    CLOSE = ltp
                    candleMeet = True
                    target = HIGH + abs(LOW - HIGH)
                    stopLoss = round(LOW / 1.00025, 2)
                    log_lines.append(f"1 Minute candle found: OHLC{OPEN, HIGH, LOW, CLOSE}\n")
                    log_lines.append(f"Target = {target}, StopLoss = {stopLoss}\n")
                    log_lines.append(f"[{convert_utc_to_ist(tradeTime)}][BUY] OHLC{OPEN, HIGH, LOW, CLOSE}\n")
                    print(candleTime, convert_utc_to_ist(firstCandle), convert_utc_to_ist(tradeTime))
                    print(f"OHLC({OPEN, HIGH, LOW, CLOSE})")
            elif firstCandle is not None and candleMeet is True:
                if ltp >= target:
                    log_lines.append(f"[{convert_utc_to_ist(tradeTime)}][SELL] Target = {target} is Hit, price = {ltp}\n")
                    isCompleted = True
                if ltp <= stopLoss:
                    log_lines.append(f"[{convert_utc_to_ist(tradeTime)}][SELL] StopLoss = {stopLoss} is Met, price = {ltp}\n")
                    isCompleted = True            
            time.sleep(3)
        except Exception as e:
            print(e)
            print(token)
            time.sleep(3)

    else:
        if not isCompleted:
            log_lines.append(f"[SELL] selling the stock as end of market time")
        with open(filename, 'w') as f:
            f.writelines(log_lines)


def wait_till_next_minute(delta=0):
    import time

    print("waiting till the next minute starts...")
    time.sleep(60 - delta - time.localtime().tm_sec)


def read_stocks_and_filter(file_path):
    import pandas as pd
    # Load the CSV file
    data = pd.read_csv(file_path)
    
    # Convert the '% Chg' column to numeric values
    data['% Chg'] = data['% Chg'].str.rstrip('%').astype(float)
    
    # Filter the stocks with percentage change between 1.25 and 2.5
    filtered_stocks = data[(data['% Chg'] >= 1.25) & (data['% Chg'] <= 2.5)]
    
    # Append "-EQ" to the stock symbols
    filtered_stocks['Symbol'] = filtered_stocks['Symbol'] + '-EQ'
    
    # Get the list of filtered stock symbols
    stock_symbols = filtered_stocks['Symbol'].tolist()
    
    return stock_symbols

def wait_for_stocks_files(fileprefix:str=trading_params['increment']):
    data = None
    import os
    file_found = False
    print(f"Waiting for {fileprefix}m.csv....")
    while not file_found:
        if os.path.exists(f"{fileprefix}m.csv") and os.path.isfile(f"{fileprefix}m.csv"):
            file_found = True
            print(f"{fileprefix}m.csv Found!")
        else:
            time.sleep(0.05)
    data = read_stocks_and_filter(f"{fileprefix}m.csv")
    
    print("saving stocks to loacal filter json file...")
    with open("filter_local.json", 'w') as file:
        demo = {
            "symbol":data
        }

        json.dump(demo, file)
    
    print("filtering the stocks and saving important information...")
    os.system("python utility.py")
    os.system(f"rename {trading_params['increment']}m.csv {trading_params['increment']}m-old.csv")

wait_for_stocks_files()

if trading_params["testing"] is False and trading_params["historicData"] is False:
    wait_for_stocks_files()
    read_filtered()
    sObj.timeout = trading_params["increment"] * 60
    threads = []
    for stock in filtered_stocks:
        thread = Thread(target=trading_for_stock, args=(stock["token"], f"liveTrading/{stock['symbol']}.txt"))
        threads.append(thread)
        thread.start()
        time.sleep(1)

    for thread in threads:
        thread.join()
