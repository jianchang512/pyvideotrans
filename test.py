try:
    5/6
    raise Exception("raise")
except ZeroDivisionError as  e:
    print(f"除以0{str(e)}")
except Exception as e:
    print(f'except=={str(e)}')