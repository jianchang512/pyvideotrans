import os.path

import requests
path=r'C:\Users\c1\Music\jidu'
for i in range(0,30):
    # url=f'http://audio2.abiblica.org/bibles/app/audio/4/1/{i}.mp3'
    url=f'http://www.mei-ge.com/e/DownSys/doaction.php?enews=DownSoft&classid=19&id={11240+i}&pathid=0&pass=ab2fc9dafb1d74692b6ccb2bb349f163&p=::::::'
    print(url)
    # continue
    t=requests.get(url,timeout=600000)
    if t.status_code==200:
        with open(os.path.join(path,f'新约故事_{i+1}.mp3'),'wb') as f:
            f.write(t.content)