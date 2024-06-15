from SmartApi import SmartConnect #or from SmartApi.smartConnect import SmartConnect
import pyotp
import json

config = {}

def read_secreats():
    with open('config_local.json', 'r') as config_file:
        globals()['config'] = json.load(config_file)

def do_login():
    sObj = SmartConnect(api_key=config.get('api_key'))
    totp = pyotp.TOTP(config.get('totp')).now()
    data = sObj.generateSession(config.get('username'), config.get('pin'), totp)
    # print(json.dumps(data, indent=4))
    
    if data['status'] is True:
        data = data['data']
        jwt = data['jwtToken']
        feed = data['feedToken']
        globals()['config'].update({'jwtToken':jwt, 'feedToken':feed})   

def update_secreats():
    with open('complete_config_local.json', 'w') as file:
        json.dump(globals()['config'], file, indent=4)

read_secreats()
do_login()
update_secreats()