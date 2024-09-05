import requests

from videotrans.configure import config
from videotrans.configure._except import LogExcept
from videotrans.translator._base import BaseTrans


class OTT(BaseTrans):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        url = config.params['ott_address'].strip().rstrip('/').lower().replace('/translate', '') + '/translate'
        url = url.replace('//translate', '/translate')
        if not url.startswith('http'):
            url = f"http://{url}"
        self.api_url=url
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}

    # 实际发出请求获取结果
    def _get_content(self,data:list):
        jsondata={
            "q": "\n".join(data),
            "source": "auto",
            "target": self.target_language
        }
        response = requests.post(url=self.api_url, json=jsondata, proxies=self.proxies)
        if response.status_code != 200:
            raise Exception(f'{response.status_code=}')
        result = response.json()
        if "error" in result:
            raise Exception(f'{result=}')
        return result['translatedText'].strip()
