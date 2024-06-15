from file_handler import *

def filter_dict(data, filters):
    filtered = []
    for ticker in data:
        all_filters_match = True
        for filter_key, value in filters.items():
            if filter_key != "symbol" and filter_key in ticker and ticker[filter_key] != value:
                all_filters_match = False
                break
            elif filter_key == "symbol" and filter_key in ticker and not ticker[filter_key].endswith(value):
                all_filters_match = False
                break
        if all_filters_match is True:
            filtered.append(ticker)
    save_file('filtered_dict_local.json', filtered)

def filter_ticker():
    tickers_data = read_file('tickers_local.json')
    filters = read_file('filter_local.json')
    filter_dict(tickers_data, filters)

filter_ticker()