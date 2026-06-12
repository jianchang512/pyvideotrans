try:

    try:
        print('抛出')
        raise RuntimeError("yes")
    except RuntimeError as e:
        print(f'========={e}')
        raise
    except Exception as e:
        print('#######')
        
except RuntimeError:
    print('又一次捕获')