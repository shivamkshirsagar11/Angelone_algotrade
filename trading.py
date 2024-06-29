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

def time_calc(days=0, hours=0, minutes=0, ttime='', replace=False):
    ttime = datetime.now() if ttime == '' else datetime.strptime(ttime, "%Y-%m-%d %H:%M")
    ttime = ttime - timedelta(days=abs(days)) if days < 0 else ttime + timedelta(days=days)
    ttime = ttime - timedelta(minutes=abs(minutes)) if minutes < 0 else ttime + timedelta(minutes=minutes)
    if replace is True:
        ttime = ttime.replace(hour=abs(hours), minute=abs(minutes))
    return ttime.strftime("%Y-%m-%d %H:%M")

sObj = SmartConnect(api_key=config.get('api_key'))
sObj.setAccessToken(config.get('jwtToken'))

trading_params = read_file("trading_params.json")

def get_historic_data(historic_params, start_time,increments=trading_params["increment"]):
    stop_time = time_calc(days=-trading_params['latest'], hours=3, minutes=15, replace=True)
    stop_time = time_calc(minutes=increments, ttime=stop_time)
    print(start_time, stop_time)
    while start_time != stop_time:
        historic_params["fromdate"] = start_time
        historic_params["todate"] = start_time
        data = sObj.getCandleData(historic_params)
        print(json.dumps(data, indent=4))
        start_time = time_calc(minutes=increments, ttime=start_time)
        print(f"next candle time: {start_time}")
        time.sleep(trading_params["increment"] * 60)



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
        thread = Thread(target=get_historic_data, args=(historicParam.copy(), start_time))
        threads.append(thread)
        thread.start()
        time.sleep(1)

    for thread in threads:
        thread.join()

    