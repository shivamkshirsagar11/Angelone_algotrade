import requests
from file_handler import save_file

data = []

def download_and_save(link, filename):
    response = requests.get(link, verify=False, timeout=60)
    globals()['data'] = response.json()
    save_file(filename, globals()['data'])

download_and_save("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", "tickers_local.json")