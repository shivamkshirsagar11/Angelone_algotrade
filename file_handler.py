import json

def read_file(filename, mode='r', encoding='utf-8'):
    data = None
    with open(filename, mode) as f:
        data = json.load(f)
    return data

def save_file(filename, data, mode='w', encoding='utf-8'):
    with open(filename, mode) as f:
        json.dump(data, f, indent=4)