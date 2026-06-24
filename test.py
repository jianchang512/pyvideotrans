import requests
try:
    res=requests.head('http://127.0.0.1:108080')    
    print(f'{res=}')
except Exception as e:
    print("#########")
    print(e)
    print("#########")
