from SmartApi import SmartConnect #or from SmartApi.smartConnect import SmartConnect
from threading import Thread
from file_handler import read_file
from datetime import datetime, timedelta
import json
import time

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

def time_calc(days=0, hours=0, minutes=0, seconds=0, ttime='', replace=False):
    ttime = datetime.now() if ttime == '' else datetime.strptime(ttime, "%Y-%m-%d %H:%M")
    ttime = ttime - timedelta(days=abs(days)) if days < 0 else ttime + timedelta(days=days)
    ttime = ttime - timedelta(minutes=abs(minutes)) if minutes < 0 else ttime + timedelta(minutes=minutes)
    ttime = ttime - timedelta(minutes=abs(minutes)) if seconds < 0 else ttime + timedelta(seconds=seconds)
    if replace is True:
        ttime = ttime.replace(hour=abs(hours), minute=abs(minutes), second=seconds)
    return ttime.strftime("%Y-%m-%d %H:%M")

sObj = SmartConnect(api_key=config.get('api_key'))
sObj.setAccessToken(config.get('jwtToken'))

trading_params = read_file("trading_params.json")

def get_historic_data(historic_params, start_time,filename='garbage.txt', increments=trading_params["increment"]):
    stop_time = time_calc(days=-trading_params['latest'], hours=3, minutes=15, replace=True)
    stop_time = time_calc(minutes=increments, ttime=stop_time)
    print(start_time, stop_time)
    log_lines = [f"[{start_time}] Started Monitoring Stock...\n"]
    
    firstHigh = firstLow = target = stopLoss = None
    triggerHigh = triggerLow = None
    isSold = False
    waiting_for_sell = False
    EntryOnNext = False

    while start_time != stop_time and not isSold:
        historic_params["fromdate"] = start_time
        historic_params["todate"] = start_time
        data = sObj.getCandleData(historic_params)
        print(json.dumps(data, indent=4))
        [_, OPEN, high, low, close,_] = data['data'][0]
        if firstHigh is None and not isSold:
            firstHigh = high
            firstLow = low
            log_lines.append(f"[{start_time}] First Candle Data: OHLC({OPEN, high, low, close})\n")
        elif close >= firstHigh and not EntryOnNext and not waiting_for_sell and not isSold:
            triggerHigh = high
            triggerLow = low
            EntryOnNext = True
            target = close + 2 * abs(low - high)
            stopLoss = low
            log_lines.append(f"[{start_time}] Trigger Candle Data: OHLC({OPEN, high, low, close})\n")
            log_lines.append(f"[{start_time}] entryOnNextCandle = True, Target = {target}, StopLoss = {stopLoss}\n")
        elif EntryOnNext and not isSold and not waiting_for_sell:
            log_lines.append(f"[{start_time}] [BUY] previous candle triggered this candle for Entry OHLC({OPEN, high, low, close})\n")
            waiting_for_sell = True
            EntryOnNext = False
        elif waiting_for_sell and not isSold:
            if close <= stopLoss:
                log_lines.append(f"[{start_time}] [SELL] Selling the stock as StopLoss of {stopLoss} is hit, OHLC({OPEN, high, low, close})\n")
                isSold = True
                break
            elif close >= target:
                log_lines.append(f"[{start_time}] [SELL] Selling the stock as Target of {target} is hit, OHLC({OPEN, high, low, close})\n")
                isSold = True
                break
        start_time = time_calc(minutes=increments, ttime=start_time)
        print(f"next candle time: {start_time}")
        time.sleep(2)
        # time.sleep(trading_params["increment"] * 60)
    else:
        if not isSold:
            log_lines.append(f"[{start_time}] [SELL] Selling the stock as time is 3:15\n")
    
    with open(filename, 'w') as f:
        f.writelines(log_lines)



if trading_params["historicData"] is True:
    read_filtered()
    start_time = time_calc(days=-trading_params['earliest'], hours=9, minutes=15, replace=True)
    end_time = time_calc(minutes=trading_params["increment"], ttime=start_time)
    threads = []
    for stock in filtered_stocks:
        historicParam={
            "exchange": stock['exch_seg'],
            "symboltoken": stock['token'],
            "interval": candle_time_mapping(trading_params["increment"])
            }
        thread = Thread(target=get_historic_data, args=(historicParam.copy(), start_time,f"{stock['symbol']}_{stock['exch_seg']}.txt"))
        threads.append(thread)
        thread.start()
        time.sleep(1)

    for thread in threads:
        thread.join()

    