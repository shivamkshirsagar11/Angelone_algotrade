from datetime import datetime

def parse_ist_time(ist_time_str):
    return datetime.strptime(ist_time_str, "%d-%b-%Y %H:%M:%S")

def time_difference(time1, time2):
    time1 = parse_ist_time(time1)
    time2 = parse_ist_time(time2)
    
    difference = time1 - time2
    return difference.total_seconds()

def get_stopping_time(hour=0, minute=0):
    today = datetime.now()
    today = today.replace(hour=hour, minute=minute, second=0)
    return today.strftime("%d-%b-%Y %H:%M:%S")


a = get_stopping_time(3, 14)
b = get_stopping_time(3, 15)

print(time_difference(a, b))
# print(a, b)