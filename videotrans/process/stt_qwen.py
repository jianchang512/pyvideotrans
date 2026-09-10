# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import json, traceback
import re
from pathlib import Path
from typing import List


from videotrans.configure.config import logger


def qwen3asr_fun(
        cut_audio_list=None,
        logs_file=None,
        local_dir=None,
        local_dir_align=None,
        max_speech_ms=6000,
        min_speech_ms=3000,
        model_name=None,
        detect_language=None,
        force_align=False,  # 是否需要对齐时间戳:只有明确指定属于这些语言中的某个 ["zh","en","ja",'ko','yue','fr','es','it','de','pt','ru'] 才支持
        hotword=None,
        **kw
):
    import copyreg
    copyreg.pickle(type({}.keys()), lambda k: (list, (list(k),)))


    from videotrans.task.taskcfg import SrtItem
    from videotrans.process._stt_utils import _write_log, _resegment
    import torch

    from transformers import AutoProcessor, AutoModelForMultimodalLM,AutoModelForTokenClassification

    try:
        batch_size=2
        # 8位量化，避免爆显存
        srts: List[SrtItem] = [SrtItem(**item) for item in json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))]
        if not force_align:
            processor = AutoProcessor.from_pretrained(local_dir)
            model = AutoModelForMultimodalLM.from_pretrained(local_dir, device_map=kw.get('device_name', 'auto'))
            msg = f'Load {model_name} running on {model.device}'
            _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
            logger.debug(f'QwenASR:{local_dir}，{msg}，{detect_language=}')

            # 不返还时间戳数据
            srts_chunk = [srts[i:i + batch_size] for i in range(0, len(srts), batch_size)]
            for i, it_list in enumerate(srts_chunk):
                audio = [it['filename'] for it in it_list]
                inputs = processor.apply_transcription_request(
                    audio, language=[detect_language for it in audio],
                ).to(model.device, model.dtype)

                output_ids = model.generate(**inputs, max_new_tokens=256)
                generated_ids = output_ids[:, inputs["input_ids"].shape[1]:]
                transcriptions = processor.decode(generated_ids, return_format="transcription_only")
                for i, text in enumerate(transcriptions):
                    it_list[i]['text'] = text
                
                _write_log(logs_file, json.dumps({"type": "subtitle", "text": "\n".join([it['text'] for it in it_list])}))

            return srts, None
            
        

        # 需要返回时间戳
        texts = [{
            "start": 0,
            "end": 0,
            "text": "",
            "words": []
        }]
        language = None
        asr_processor = AutoProcessor.from_pretrained(local_dir)
        asr_model = AutoModelForMultimodalLM.from_pretrained(local_dir, device_map=kw.get('device_name', 'auto'))

        aligner_processor = AutoProcessor.from_pretrained(local_dir_align)
        aligner_model = AutoModelForTokenClassification.from_pretrained(
    local_dir_align, dtype='auto', device_map=kw.get('device_name', 'auto'))
        msg = f'Load {model_name} running on {asr_model.device}'
        _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
        logger.debug(f'QwenASR:{local_dir}，{msg}，{detect_language=}, {force_align=}')
 

        for i, it in enumerate(srts):
            inputs = asr_processor.apply_transcription_request(audio=it['filename'],language=detect_language)
            inputs = inputs.to(asr_model.device, asr_model.dtype)
            output_ids = asr_model.generate(**inputs, max_new_tokens=1024)
            generated_ids = output_ids[:, inputs["input_ids"].shape[1]:]
            parsed = asr_processor.decode(generated_ids, return_format="parsed")[0]
            transcript = parsed["transcription"]
            language = parsed["language"] or "English"
            # Step 2: Prepare alignment inputs
            aligner_inputs, word_lists = aligner_processor.prepare_forced_aligner_inputs(
                audio=it['filename'], 
                transcript=transcript, 
                language=language,
            )
            aligner_inputs = aligner_inputs.to(aligner_model.device, aligner_model.dtype)
            # Step 3: Run forced aligner
            with torch.inference_mode():
                outputs = aligner_model(**aligner_inputs)
            # Step 4: Decode timestamps
            timestamps = aligner_processor.decode_forced_alignment(
                logits=outputs.logits,
                input_ids=aligner_inputs["input_ids"],
                word_lists=word_lists,
                timestamp_token_id=aligner_model.config.timestamp_token_id,
            )[0]

                    
            offset = it['start_time'] / 1000.0

            if i == 0:
                texts[0]['start'] = float(timestamps[0]['start_time']) + offset

            for item in timestamps:
                texts[0]['words'].append({
                    "word": item['text'], 
                    "start": float(item['start_time']) + offset, 
                    "end": float(item['end_time']) + offset
                })
                
            _write_log(logs_file, json.dumps({"type": "subtitle", "text":transcript[:90]+"..." }))
            
            if i == len(srts) - 1:
                texts[0]['end'] = float(timestamps[-1]['end_time']) + offset

        srts = _resegment(texts, "zh" if language in ["Chinese", "Cantonese", "Japanese", "Korean"] else 'en', max_speech_ms, min_speech_ms, logs_file)
        return srts, None
    except BaseException as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'
