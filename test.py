import requests
try:
    res=requests.head("https://www.google.com",proxies={'https':'sock://127.0.0.1:10808'})    
    #res=requests.head("https://www.google.com",proxies={'https':'sock://127.0.0.1:10808'})    
    #res=requests.head("https://www.google.com",proxies={"https":""})    
    print(f'{res=}')
except Exception as e:
    print("#########")
    print(e)
    print("#########")
