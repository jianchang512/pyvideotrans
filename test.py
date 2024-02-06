import requests
from PySide6.QtCore import QSettings

from videotrans.configure import config

url=QSettings("Jameson", "VideoTranslate").value("clone_api", "")
print(f'{url=}')
if not url:
    print(config.transobj['bixutianxiecloneapi'])
else:
    try:
        url = url.strip().rstrip('/') + "/init"
        res = requests.get('http://' + url.replace('http://', ''))
        if res.status_code == 200:
            print(res.json)
            print("\nOK\n")
        else:
            raise Exception(f"code={res.status_code},{config.transobj['You must deploy and start the clone-voice service']}")
    except Exception as e:
        print(f'[error]:clone-voice:{str(e)}')


input("Press Enter for quit")