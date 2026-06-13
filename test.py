import requests
try:
    requests.get('http://127.0.0.1:9880')
    
    
except requests.exceptions.ConnectionError as e:
    if "Failed to establish a new connection" in str(e):
        print('需要部署并启动')