from videotrans.configure.excepts import VideoTransError

try:
    if 1:
        raise VideoTransError('测试')
except Exception as e:
    print(f'被抛出的{e}')