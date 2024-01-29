

try:
    1/0
except Exception as e:
    print(str(e))
    print(str(e.args))