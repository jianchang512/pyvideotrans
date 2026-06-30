import json
import os
from pathlib import Path
from typing import Union

from videotrans import translator
from videotrans.configure.config import tr, ROOT_DIR, settings, logger
from videotrans.configure import contants
from videotrans.configure.excepts import VideoTransError
from videotrans.util.help_srt import get_subtitle_from_srt, simple_wrap, set_ass_font


class SubtitleMixin:

    def _process_subtitles(self) -> Union[tuple[str, str], None]:
        logger.debug(f"\n======准备要嵌入的字幕:{self.cfg.subtitle_type=}=====")
        if not Path(self.cfg.target_sub).exists() :
            raise VideoTransError(tr("No valid subtitle file exists")+self.cfg.target_sub)

        if not Path(self.cfg.source_sub).exists() or (self.cfg.source_language_code == self.cfg.target_language_code):
            if self.cfg.subtitle_type == 3:
                self.cfg.subtitle_type = 1
            elif self.cfg.subtitle_type == 4:
                self.cfg.subtitle_type = 2

        process_end_subtitle = self.cfg.cache_folder + f'/end.srt'
        maxlen = int(
            settings.get('cjk_len', 15) if self.cfg.target_language_code[:2] in contants.CJK_LANG else
            settings.get('other_len', 60))
        target_sub_list = get_subtitle_from_srt(self.cfg.target_sub)

        srt_string = ""
        _join_flag = ''
        if self.cfg.subtitle_type in [3, 4]:
            source_sub_list = get_subtitle_from_srt(self.cfg.source_sub)
            source_length = len(source_sub_list)
            source_maxlen = int(
                settings.get('cjk_len', 15) if self.cfg.source_language_code[:2] in ["zh", "ja", "jp", "ko",
                                                                                     'yu'] else
                settings.get('other_len', 60))

            _join_flag = self._get_join_flag()

            for i, it in enumerate(target_sub_list):
                _text = simple_wrap(it['text'].strip(), maxlen, self.cfg.target_language_code)
                srt_string += f"{it['line']}\n{it['time']}\n"
                if source_length > 0 and i < source_length:
                    _text_source = simple_wrap(source_sub_list[i]['text'], source_maxlen,
                                                     self.cfg.source_language_code)
                    _text = f'{_text_source}\n{_join_flag}{_text}' if self.cfg.output_srt == 1 else f'{_text}\n{_join_flag}{_text_source}'
                srt_string += f"{_text}\n\n"
            srt_string = srt_string.strip()
            process_end_subtitle = f"{self.cfg.cache_folder}/shuang.srt"
            Path(process_end_subtitle).write_text(srt_string, encoding='utf-8')
            Path(self.cfg.target_dir + "/shuang.srt").write_text(
                srt_string.replace('###', '') if _join_flag == '###' else srt_string, encoding='utf-8')
        else:
            for i, it in enumerate(target_sub_list):
                tmp = simple_wrap(it['text'].strip(), maxlen, self.cfg.target_language_code)
                srt_string += f"{it['line']}\n{it['time']}\n{tmp.strip()}\n\n"
            with Path(process_end_subtitle).open('w', encoding='utf-8') as f:
                f.write(srt_string)

        subtitle_langcode = translator.get_subtitle_code(show_target=self.cfg.target_language)
        logger.debug(
            f'最终确定字幕嵌入类型:{self.cfg.subtitle_type} ,目标字幕语言:{subtitle_langcode}, 字幕文件:{process_end_subtitle}\n')
        if self.cfg.subtitle_type in [2, 4]:
            return os.path.basename(process_end_subtitle), subtitle_langcode

        process_end_subtitle_ass = set_ass_font(process_end_subtitle)
        basename = os.path.basename(process_end_subtitle_ass)
        return basename, subtitle_langcode

    def _get_join_flag(self):
        _join_flag = ""
        if self.cfg.subtitle_type != 3 or not Path(f'{ROOT_DIR}/videotrans/ass.json').exists():
            return _join_flag
        try:
            assjson = json.loads(Path(f'{ROOT_DIR}/videotrans/ass.json').read_text(encoding='utf-8'))
        except Exception:
            logger.warning(f'未自定义样式 ass.json ，忽略')
            return _join_flag
        else:
            for k, v in assjson.items():
                if k.startswith('Bottom_') and v != assjson.get(k[7:]):
                    _join_flag = '###'
                    break
        return _join_flag
