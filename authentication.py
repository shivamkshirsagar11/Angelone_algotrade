from SmartApi import SmartConnect #or from SmartApi.smartConnect import SmartConnect
import pyotp
import json
from file_handler import read_file, save_file

config = {}

def read_secreats():
    globals()['config'] = read_file('config_local.json')

def do_login():
    sObj = SmartConnect(api_key=config.get('api_key'))
    totp = pyotp.TOTP(config.get('totp')).now()
    data = sObj.generateSession(config.get('username'), config.get('pin'), totp)
    # print(json.dumps(data, indent=4))
    
    if data['status'] is True:
        data = data['data']
        jwt = data['jwtToken']
        jwt = jwt.replace('Bearer ', '')
        feed = data['feedToken']
        globals()['config'].update({'jwtToken':jwt, 'feedToken':feed})
    return sObj 

def update_secreats():
    save_file('complete_config_local.json', globals()['config'])

def processLogin():
    read_secreats()
    sObj = do_login()
    update_secreats()

    return sObj