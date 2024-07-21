from datetime import datetime, timedelta
import time


def parse_ist_time(ist_time_str):
    return datetime.strptime(ist_time_str, "%Y-%m-%d %H:%M")


def time_difference(time1, time2):
    time1 = parse_ist_time(time1)
    time2 = parse_ist_time(time2)
    
    difference = time1 - time2
    return difference.total_seconds()


x = time_difference("2024-07-19 03:15","2024-07-19 15:24")
print(x)