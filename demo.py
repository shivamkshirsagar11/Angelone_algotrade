from datetime import datetime, timedelta
import time

def parse_ist_time(ist_time_str):
    return datetime.strptime(ist_time_str, "%d-%b-%Y %H:%M:%S")

def time_difference(time1, time2):
    time1 = parse_ist_time(time1)
    time2 = parse_ist_time(time2)
    
    difference = time1 - time2
    return difference.total_seconds()

def get_stopping_time(hour=3, minute=14):
    today = datetime.now()
    today = today.replace(hour=hour, minute=minute, second=0)
    return today.strftime("%d-%b-%Y %H:%M:%S")

def time_calc(days=0, hours=0, minutes=0, seconds=0, ttime='', replace=False):
    ttime = datetime.now() if ttime == '' else datetime.strptime(ttime, "%d-%b-%Y %H:%M:%S")
    ttime = ttime - timedelta(days=abs(days)) if days < 0 else ttime + timedelta(days=days)
    ttime = ttime - timedelta(minutes=abs(minutes)) if minutes < 0 else ttime + timedelta(minutes=minutes)
    ttime = ttime - timedelta(minutes=abs(minutes)) if seconds < 0 else ttime + timedelta(seconds=seconds)
    if replace is True:
        ttime = ttime.replace(hour=abs(hours), minute=abs(minutes), second=seconds)
    return ttime.strftime("%d-%b-%Y %H:%M:%S")
a = time_calc()
b = time_calc(ttime=a, minutes=1)
x = a
while time_difference(x, b) < 0:
    x = time_calc()
    print(x, b, time_difference(x, b))
    time.sleep(10)