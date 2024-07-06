from file_handler import *

def filter_dict(data, filters):
    filtered = []

    for ticker in data:
        all_filters_match = True
        for filter_key, value in filters.items():
            if isinstance(value, str):
                if filter_key in ticker and ticker[filter_key] != value:
                    all_filters_match = False
                    break

            elif isinstance(value,list):
                check_if_matched_anyone = False
                for filter_value in value:
                    if filter_key in ticker and ticker[filter_key] == filter_value:
                        check_if_matched_anyone = True
                        break
                if check_if_matched_anyone is False:
                    all_filters_match = False
                    break

        if all_filters_match is True:
            filtered.append(ticker)
    save_file('filtered_dict_local.json', filtered)

def filter_ticker():
    tickers_data = read_file('tickers_local.json')
    filters = read_file('filter_local.json')
    print(filters)
    filter_dict(tickers_data, filters)

filter_ticker()