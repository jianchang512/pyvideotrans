import base64
import copy
import datetime
import json
import time
from pathlib import Path

import requests

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# 线程池并发

class VolcEngineTTS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_status={
            "3001":"无效的请求,若是正式版，可能当前所用音色需要单独从字节火山购买",
            "3003":"并发超限",
            "3005":"后端服务器负载高",
            "3006":"服务中断",
            "3010":"文本长度超限",
            "3011":"参数有误或者文本为空、文本与语种不匹配、文本只含标点",
            "3030":"单次请求超过服务最长时间限制",
            "3031":"后端出现异常",
            "3032":"等待获取音频超时",
            "3040":"音色克隆链路网络异常",
            "3050":"音色克隆音色查询失败"
        }
        self.fangyan={
            "东北":"zh_dongbei",
            "粤语":"zh_yueyu",
            "上海":"zh_shanghai",
            "西安":"zh_xian",
            "成都":"zh_chengdu",
            "台湾":"zh_taipu",
            "广西":"zh_guangxi"
        }
        self.voice_type=None
    def _exec(self):
        # 并发限制为1，防止限流
        self.dub_nums=1
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        if self._exit():
            return
        if not data_item or tools.vail_file(data_item['filename']):
            return
        try:
            appid = config.params['volcenginetts_appid']
            access_token = config.params['volcenginetts_access']
            cluster = config.params['volcenginetts_cluster']
            speed = 1.0
            if self.rate:
                rate = float(self.rate.replace('%', '')) / 100
                speed += rate

            volume = 1.0
            if self.volume:
                volume += float(self.volume.replace('%', '')) / 100

            # 角色为实际名字
            role=data_item['role']
            langcode=self.language[:2].lower()
            try:
                if not self.voice_type:
                    self.voice_type = tools.get_volcenginetts_rolelist(role,self.language)
            except:
                self.error=f"角色 {role} 不存在或不支持当前语言 {self.language}"
                return
            if langcode=='zh':
                langcode=self.fangyan.get(role[:2],"cn")
            host = "openspeech.bytedance.com"
            api_url = f"https://{host}/api/v1/tts"

            header = {"Authorization": f"Bearer;{access_token}"}

            request_json = {
                "app": {
                    "appid": appid,
                    "token": "access_token",
                    "cluster": cluster
                },
                "user": {
                    "uid": datetime.datetime.now().strftime("%Y%m%d")
                },
                "audio": {
                    "voice_type": self.voice_type,
                    "encoding": "mp3",
                    "speed_ratio": speed,
                    "volume_ratio": volume,
                    "pitch_ratio": 1.0,
                    "language":langcode
                },
                "request": {
                    "reqid": str(time.time()*100000),
                    "text": data_item['text'],
                    "text_type": "plain",
                    "silence_duration":50,
                    "operation": "query",
                    "pure_english_opt":1

                }
            }
            resp = requests.post(api_url, json.dumps(request_json), headers=header,proxies={"http":"","https":""})
            if resp.status_code != 200:
                self.error = f"字节火山语音合成失败:{resp.status_code} {resp.reason}"
            resp_json = resp.json()
            if "data" in resp_json:
                data = resp_json["data"]
                with open(data_item['filename'], "wb") as f:
                    f.write(base64.b64decode(data))
            elif 'code' in resp_json:
                self.error = self.error_status.get(str(resp_json['code']),resp_json['message'])
                config.logger.info(f'字节火山语音合成失败:{resp_json=}')
        except requests.ConnectionError as e:
            self.error = str(e)
        except Exception as e:
            config.logger.exception(e,exc_info=True)
            self.error = str(e)
        finally:
            if self.error:
                self._signal(text=f'{self.error}')
            else:
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

