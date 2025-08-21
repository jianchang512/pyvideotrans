from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional

from videotrans.configure import config
from videotrans.configure._base import BaseCon
from videotrans.util import tools


@dataclass
class BaseTask(BaseCon):
    inst: Optional[Any] = None
    cfg: Dict = field(default=None, repr=False)
    obj: Dict = field(default=None, repr=False)
    uuid: str = None
    precent: int = 1
    status_text: str = config.transobj['ing']
    # 使用 field(default_factory=list) 来防止所有实例共享同一个列表
    queue_tts: List = field(default_factory=list, repr=False)
    # 是否已结束
    hasend: bool = False

    # 名字规范化处理后，应该删除的
    shound_del_name: Any = None  # 保持原样

    # 是否需要语音识别
    shoud_recogn: bool = False

    # 是否需要字幕翻译
    shoud_trans: bool = False

    # 是否需要配音
    shoud_dubbing: bool = False

    # 是否需要人声分离
    shoud_separate: bool = False

    # 是否需要嵌入配音或字幕
    shoud_hebing: bool = False

    def __post_init__(self):
        # 调用父类的真实 __init__
        super().__init__()

        if self.obj:
            self.cfg.update(self.obj)

        if "uuid" in self.cfg and self.cfg['uuid']:
            self.uuid = self.cfg['uuid']

    # 预先处理，例如从视频中拆分音频、人声背景分离、转码等
    def prepare(self):
        pass

    # 语音识别创建原始语言字幕
    def recogn(self):
        pass

    # 将原始语言字幕翻译到目标语言字幕
    def trans(self):
        pass

    # 根据 queue_tts 进行配音
    def dubbing(self):
        pass

    # 配音加速、视频慢速对齐
    def align(self):
        pass

    # 视频、音频、字幕合并生成结果文件
    def assembling(self):
        pass

    # 删除临时文件，移动或复制，发送成功消息
    def task_done(self):
        pass

    # 字幕是否存在并且有效
    def _srt_vail(self, file):
        if not file:
            return False
        if not tools.vail_file(file):
            return False
        try:
            tools.get_subtitle_from_srt(file)
        except:
            try:
                Path(file).unlink(missing_ok=True)
            except:
                pass
            return False
        return True

    # 删掉尺寸为0的无效文件
    def _unlink_size0(self, file):
        if not file:
            return
        p = Path(file)
        if p.exists() and p.stat().st_size == 0:
            try:
                p.unlink(missing_ok=True)
            except:
                pass

    # 保存字幕文件 到目标文件夹
    def _save_srt_target(self, srtstr, file):
        # 是字幕列表形式，重新组装
        try:
            txt = tools.get_srt_from_list(srtstr)
            with open(file, "w", encoding="utf-8") as f:
                f.write(txt)
        except Exception:
            raise
        self._signal(text=Path(file).read_text(encoding='utf-8'), type='replace_subtitle')
        return True

    def _check_target_sub(self, source_srt_list, target_srt_list):
        import re, copy

        if len(source_srt_list) == 1 or len(target_srt_list) == 1:
            target_srt_list[0]['line'] = 1
            return target_srt_list[:1]
        source_len = len(source_srt_list)
        target_len = len(target_srt_list)
        config.logger.info(f'{source_srt_list=}')
        config.logger.info(f'{target_srt_list=}')
        for i, it in enumerate(source_srt_list):
            tmp = copy.deepcopy(it)
            if i > target_len - 1:
                # 超出目标字幕长度
                tmp['text'] = '  '
            elif re.sub(r'\D', '', it['time']) == re.sub(r'\D', '', target_srt_list[i]['time']):
                # 正常时间码相等
                tmp['text'] = target_srt_list[i]['text']
            elif i == 0 and source_srt_list[1]['time'] == target_srt_list[1]['time']:
                # 下一行时间码相同
                tmp['text'] = target_srt_list[i]['text']
            elif i == source_len - 1 and source_srt_list[i - 1]['time'] == target_srt_list[i - 1]['time']:
                # 上一行时间码相同
                tmp['text'] = target_srt_list[i]['text']
            elif i > 0 and i < source_len - 1 and target_len > i + 1 and source_srt_list[i - 1]['time'] == \
                    target_srt_list[i - 1]['time'] and source_srt_list[i + 1]['time'] == target_srt_list[i + 1]['time']:
                # 上下两行时间码相同
                tmp['text'] = target_srt_list[i]['text']
            else:
                # 其他情况清空目标字幕文字
                tmp['text'] = '  '
            if i > len(target_srt_list) - 1:
                target_srt_list.append(tmp)
            else:
                target_srt_list[i] = tmp
        config.logger.info(f'处理后目标字幕：{target_srt_list=}')
        return target_srt_list

    # 完整流程判断是否需退出，子功能需重写
    def _exit(self):
        if config.exit_soft or config.current_status != 'ing':
            return True
        return False
