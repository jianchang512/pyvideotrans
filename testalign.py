# forcealign对齐
text="""在古老星系中发现了有机分子
我们离第三类接触还有多远啊？
微博正式展开拍摄任务，已经届满周年。最近也传过来许多过去难以
拍摄到的照片
六月初，天文学家在《自然》期刊上发表了这张照片
在蓝色核心外环绕着一圈橘黄色的光芒，这是一个星系规模的甜甜圈
这是一个传送门
这是外星文明的代生环
其实这是一个含有有机物多环芳香烃的古老星系，它的名字是SPT零四一八 dash 四十七，因为名
字很长，以下我们就简称为 S P T 零四一八八，好像没有简称到
这个结果有什么特殊意义？这代表我们发现外星生命了吗？
本集节目是饭团会员选题。我们每个月都会制作由会员投票出来的题目。
如果你也有好题目，
希望我们做一集来讲解或讨论。
马上点击加入按钮，成为我们的会员吧

"""
from videotrans.util import tools
import torch,re
from qwen_asr import Qwen3ForcedAligner
def segmentation_asr_data(asr_data, 
                            min_duration=1.0, 
                            max_pref_duration=3.0, 
                            max_hard_duration=10.0, 
                            silence_threshold=0.2):
    """
    将ASR字词级数据重组为1-6秒的句子。
    
    Args:
        asr_data (list): ASR原始json列表
        min_duration (float): 最小句子时长(秒)，尽量不切分比这短的
        max_pref_duration (float): 期望最大时长(秒)，超过这个长度会倾向于切分
        max_hard_duration (float): 绝对最大时长(秒)，不得超过
        silence_threshold (float): 词与词之间超过多少秒视为静音断句点

    Returns:
        list: 格式化后的句子字典列表
    """
    if not asr_data:
        return []

    # 1. 定义多语言标点符号正则 (包括中文、英文、日文等常见标点)
    # 覆盖范围：,.?;!: 以及对应的全角符号
    punc_pattern = re.compile(r'[。.?？!！;；:：,，、\u3002\uff0c\uff1f\uff01]')
    
    # 2. 判断字符是否为CJK (中日韩) 用于决定拼接是否加空格
    def is_cjk(char):
        if not char: return False
        code = ord(char[0])
        # CJK Unified Ideographs scope roughly
        return 0x4E00 <= code <= 0x9FFF or \
               0x3040 <= code <= 0x309F or \
               0x30A0 <= code <= 0x30FF

    segments = []
    current_buffer = []
    
    def flush_buffer(buffer):
        """将当前缓存的词列表合并为一个句子字典"""
        if not buffer:
            return None
            
        start_ms = int(buffer[0]['start_time'] * 1000)
        end_ms = int(buffer[-1]['end_time'] * 1000)
        
        # 智能拼接文本
        text_parts = []
        for i, token in enumerate(buffer):
            word = token['text']
            if i == 0:
                text_parts.append(word)
            else:
                prev_word = buffer[i-1]['text']
                # 如果前一个词结尾和当前词开头都是CJK字符，则直接拼接，否则加空格
                # 注意：这里取prev_word[-1]和word[0]来判断
                if prev_word and word and is_cjk(prev_word[-1]) and is_cjk(word[0]):
                    text_parts.append(word)
                else:
                    # 对于非CJK语言（如英文），或者中英混排，加空格
                    # 特殊情况：如果当前词仅仅是标点符号，通常不需要前置空格(取决于ASR格式，这里简化处理)
                    if punc_pattern.match(word) and len(word) == 1:
                        text_parts.append(word)
                    else:
                        text_parts.append(" " + word) # 默认加空格
                        
        # 清理可能产生的多余空格 (例如中文里夹杂的空格)
        full_text = "".join(text_parts).strip()
        
        endraw=tools.ms_to_time_string(ms=end_ms)
        startraw=tools.ms_to_time_string(ms=start_ms)
        
        return {
            "start_time": start_ms,
            "end_time": end_ms,
            "endraw":endraw,
            "startraw":startraw,
            "time":f"{startraw} -> {endraw}",
            "text": full_text
        }

    # 3. 遍历数据进行切分
    for i, token in enumerate(asr_data):
        # 获取当前token信息
        token_text = token.get('text', '')
        token_start = token.get('start_time', 0.0)
        token_end = token.get('end_time', 0.0)
        
        # 计算与上一个词的静音间隙
        silence_gap = 0.0
        if i > 0:
            silence_gap = token_start - asr_data[i-1]['end_time']
        
        # 即使 buffer 为空，我们也先把它放进去，再判断是否要在此处结束
        # 但为了逻辑清晰，我们先判断是否要“结算”之前的 buffer
        
        should_split = False
        
        if current_buffer:
            buf_start = current_buffer[0]['start_time']
            current_duration = token_end - buf_start # 加上当前词后的总时长
            prev_duration = current_buffer[-1]['end_time'] - buf_start # 加当前词之前的时长
            
            has_punc = bool(punc_pattern.search(current_buffer[-1]['text']))
            is_long_silence = silence_gap >= silence_threshold
            
            # --- 断句决策逻辑 ---
            
            # 1. 硬限制：加上当前词会超过 8s，必须在当前词之前切断
            if current_duration > max_hard_duration:
                should_split = True
            
            # 2. 理想区间断句 (1s - 6s)：如果有标点 或 有长静音
            elif prev_duration >= min_duration:
                if has_punc:
                    should_split = True
                elif is_long_silence:
                    should_split = True
                # 3. 超过期望最大时长 (6s)：开始寻找任何断句机会（哪怕没有标点）
                # 这里我们利用静音作为弱分割点，只要有微弱停顿就切
                elif prev_duration >= max_pref_duration:
                    should_split = True
            
        if should_split:
            seg = flush_buffer(current_buffer)
            if seg: segments.append(seg)
            current_buffer = []
        current_buffer.append(token)

    # 4. 处理剩余的 buffer
    if current_buffer:
        seg = flush_buffer(current_buffer)
        if seg: segments.append(seg)
    return segments



def align_timestamps_to_lines(original_text, asr_data):
    """
    将对齐后的 Token 时间戳映射回原始文本的行结构。
    
    Args:
        original_text (str): 包含换行符和标点的原始文本
        asr_data (list): ForcedAlignItem 对象列表或字典列表
    
    Returns:
        list: 包含 text, start_time, end_time 的句子列表
    """
    
    # 1. 预处理原始文本：按换行符切分，如果一行太长也可以在此处按标点二次切分
    # 这里我们假设原始文本的换行就是用户想要的字幕行
    raw_lines = original_text.strip().split('\n')
    raw_lines = [line.strip() for line in raw_lines if line.strip()] # 去除空行
    
    # 2. 准备对齐数据：提取纯文本以便匹配
    # 兼容对象属性访问 (item.text) 和 字典访问 (item['text'])
    tokens = []
    for item in asr_data:
        text = item.text if hasattr(item, 'text') else item.get('text', '')
        start = item.start_time if hasattr(item, 'start_time') else item.get('start_time', 0)
        end = item.end_time if hasattr(item, 'end_time') else item.get('end_time', 0)
        tokens.append({'text': text, 'start': start, 'end': end})

    # 3. 核心匹配逻辑
    results = []
    token_idx = 0
    total_tokens = len(tokens)
    
    # 用于标准化的正则：去除所有标点、空格、特殊符号，只保留汉字、字母、数字
    # 这样可以忽略 "dash" 和 "-" 的区别，或者 "SPT" 和 "S P T" 的空格区别
    def normalize(s):
        return re.sub(r'[^\w\u4e00-\u9fa5]', '', s).lower()

    for line in raw_lines:
        line_clean = normalize(line)
        if not line_clean:
            continue # 跳过只有标点的行
            
        # 寻找当前行的起始 Token
        # 我们需要从 token_idx 开始，向后累加 token 的文本，直到能够覆盖 line_clean
        
        current_acc_text = ""
        start_token_idx = token_idx
        
        while token_idx < total_tokens:
            token_text = normalize(tokens[token_idx]['text'])
            
            # 累加当前 token
            current_acc_text += token_text
            token_idx += 1
            
            # 检查是否匹配完成
            # 注意：强制对齐模型有时候会丢字或者多字（幻觉），或者将 "dash" 对齐为 "-"
            # 这里使用简单的长度判断和包含判断。
            # 如果累加的长度 >= 原始行长度，我们认为这一行结束了
            if len(current_acc_text) >= len(line_clean):
                break
        
        # 提取时间戳
        # 起始时间是这一段匹配序列的第一个 token 的开始时间
        # 结束时间是这一段匹配序列的最后一个 token 的结束时间
        if start_token_idx < token_idx:
            # 获取实际匹配到的 token 片段
            matched_tokens = tokens[start_token_idx : token_idx]
            
            # 修正：有时候行末的标点符号在原始文本有，但 token 里没有
            # 我们只要保证 token 里的内容大体对应即可。
            
            seg_start = matched_tokens[0]['start']
            seg_end = matched_tokens[-1]['end']
            
            # 格式化时间字符串 (假设你有 tools.ms_to_time_string)
            # 这里仅演示逻辑，直接返回秒数或毫秒
            results.append({
                "text": line,  # 使用原始文本（保留了标点和空格）
                "start_time": int(seg_start * 1000),
                "end_time": int(seg_end * 1000),
                # "startraw": tools.ms_to_time_string(ms=int(seg_start * 1000)),
                # "endraw": tools.ms_to_time_string(ms=int(seg_end * 1000))
            })
        else:
            # 没匹配到 Token（可能是空行或异常）
            pass

    return results


m=Qwen3ForcedAligner.from_pretrained("./models/models--Qwen--Qwen3-ForcedAligner-0.6B",dtype=torch.float32,
                device_map='cpu',)

asr_data=m.align("60.wav",text=text,language='Chinese')
final_segments = align_timestamps_to_lines(text, asr_data[0].items)

# 打印结果
for seg in final_segments:
    print(f"[{seg['start_time']}ms -> {seg['end_time']}ms] {seg['text']}")

'''
if asr_data and asr_data[0].items:
    srts=[{"text":it.text,"start_time":it.start_time,"end_time":it.end_time} for it in asr_data[0].items]
    s=segmentation_asr_data(srts)
    for it in s:
        print(f'{it["start_time"]}:{it["end_time"]}  {it["text"]}')
'''
exit()
def a(a=None,b=None):
    print('cc')

a(c=123)
exit()
from videotrans.util import tools


tools.remove_silence_wav('10-1.wav')
exit()
from modelscope.hub.file_download import model_file_download

# 举例：下载 qwen/Qwen-7B-Chat 模型中的某个文件
path = model_file_download(model_id='himyworld/fasterwhisper', file_path='tiny/model.bin',local_dir='./models')
print(f"文件已下载至: {path}")
exit()
import os
os.environ['https_proxy']='http://127.0.0.1:10808'
try:
    import flash_attn
except ImportError as e:
    print(e)
exit()
tools.check_and_down_ms('Qwen/Qwen3-TTS-12Hz-0.6B-Base',local_dir='./models/models--Qwen--Qwen3-TTS-12Hz-0.6B-Base')
#tools.check_and_down_hf('Qwen3-TTS', repo_id='Qwen/Qwen3-TTS-12Hz-0.6B-Base',local_dir='./models/models--Qwen--Qwen3-TTS-12Hz-0.6B-Base')

exit()
tools.check_and_down_hf(model_name='large-v1',repo_id='Systran/faster-whisper-large-v1',local_dir='./models/large-v1')
tools.check_and_down_hf(model_name='large-v2',repo_id='Systran/faster-whisper-large-v2',local_dir='./models/large-v2')
tools.check_and_down_hf(model_name='large-v3',repo_id='Systran/faster-whisper-large-v3',local_dir='./models/large-v3')

exit()
tools.check_and_down_hf(model_name='tiny',repo_id='Systran/faster-whisper-tiny',local_dir='./models/tiny')
tools.check_and_down_hf(model_name='tiny.en',repo_id='Systran/faster-whisper-tiny.en',local_dir='./models/tiny.en')

tools.check_and_down_hf(model_name='base',repo_id='Systran/faster-whisper-base',local_dir='./models/base')
tools.check_and_down_hf(model_name='base.en',repo_id='Systran/faster-whisper-base.en',local_dir='./models/base.en')

tools.check_and_down_hf(model_name='small',repo_id='Systran/faster-whisper-small',local_dir='./models/small')
tools.check_and_down_hf(model_name='small.en',repo_id='Systran/faster-whisper-small.en',local_dir='./models/small.en')

tools.check_and_down_hf(model_name='medium',repo_id='Systran/faster-whisper-medium',local_dir='./models/medium')
tools.check_and_down_hf(model_name='medium.en',repo_id='Systran/faster-whisper-medium.en',local_dir='./models/medium.en')

tools.check_and_down_hf(model_name='large-v3-turbo',repo_id='dropbox-dash/faster-whisper-large-v3-turbo',local_dir='./models/large-v3-turbo')


tools.check_and_down_hf(model_name='distil-large-v3',repo_id='Systran/faster-distil-whisper-large-v3',local_dir='./models/distil-large-v3')

tools.check_and_down_hf(model_name='distil-large-v3.5',repo_id='distil-whisper/distil-large-v3.5-ct2',local_dir='./models/distil-large-v3.5')




exit()
import json

with open('./videotrans/language/en.json','r',encoding='utf-8') as f:
    print(json.loads(f.read()))

exit()
import os
import subprocess
import uuid
import time
import math

def highlight_region_in_video(video_file, sec, temp_dir, te, be, le, re):
    """
    从视频指定时间截取帧，并根据百分比参数绘制红色矩形框。
    
    参数:
        video_file (str): 视频文件的绝对路径
        sec (float): 截取的时间点（秒）
        temp_dir (str): 临时文件保存目录
        te (float): Top Edge，矩形顶边距离视频底边的百分比 (0-100)
        be (float): Bottom Edge，矩形底边距离视频底边的百分比 (0-100)
        le (float): Left Edge，矩形左边距离视频左边的百分比 (0-100)
        re (float): Right Edge，矩形右边距离视频左边的百分比 (0-100)
        
    返回:
        str: 生成图片的完整路径，如果出错则返回 None
    """
    
    # 1. 确保临时目录存在
    if not os.path.exists(temp_dir):
        try:
            os.makedirs(temp_dir)
        except OSError as e:
            print(f"创建目录失败: {e}")
            return None

    # 2. 生成随机文件名 (使用时间戳+UUID)
    file_name = f"{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
    out_path = os.path.join(temp_dir, file_name)
    
    # 3. 构建 FFmpeg 的 drawbox 过滤器字符串
    # 逻辑说明：
    # iw: 输入宽度 (input width)
    # ih: 输入高度 (input height)
    # x: 从左边开始的像素 = iw * (le / 100)
    # y: 从顶边开始的像素 = ih * (1 - te / 100)  <-- 注意这里做了坐标转换
    # w: 宽度 = iw * ((re - le) / 100)
    # h: 高度 = ih * ((te - be) / 100)
    
    # 简单的参数校验，防止负数宽高导致 FFmpeg 报错
    if te < be:
        print("警告: te (Top) 应该大于 be (Bottom)")
        te, be = be, te # 交换以修正
    if re < le:
        print("警告: re (Right) 应该大于 le (Left)")
        re, le = le, re # 交换以修正

    # color=red: 红色
    # t=3: 线条粗细为 3 像素

    vf_cmd = (
        f"drawbox="
        f"x=iw*{le}/100:"
        f"y=ih*{te}/100:"
        f"w=iw*(100-{re}-{le})/100:"
        f"h=ih*(100-{te}-{be})/100:"
        f"color=red:t=3"
    )

    # 4. 组装 FFmpeg 命令
    # -ss 放在 -i 之前可以启用快速跳转 (fast seek)
    # -vframes 1 代表只输出 1 帧
    # -q:v 2 代表高质量 JPG (范围 1-31, 越小质量越高)
    cmd = [
        'ffmpeg',
        '-y',               # 覆盖已存在文件
        '-ss', str(sec),    # 跳转时间
        '-i', video_file,   # 输入文件
        '-vf', vf_cmd,      # 视频过滤器(画框)
        '-frames:v', '1',   # 截取一帧
        '-q:v', '2',        # 图片质量
        out_path            # 输出路径
    ]

    # 5. 执行命令
    try:
        # capture_output=True 用于捕获日志，避免直接打印到控制台，除非出错
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return os.path.abspath(out_path)
    except subprocess.CalledProcessError as e:
        print("FFmpeg 执行出错:")
        print(e.stderr.decode('utf-8', errors='ignore'))
        return None

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 假设有一个视频文件路径
    video_path = r"C:\Users\c1\Videos\10.mp4" 
    temp_folder = r"./tmp"
    
    # 设定参数：
    # 想画一个框：
    # 顶部距离底边 80% (即画面上方)
    # 底部距离底边 20% (即画面下方)
    # 左边距离左侧 30%
    # 右边距离左侧 70%
    # 这将在画面中心绘制一个较大的矩形
    
    result_path = highlight_region_in_video(
        video_file=video_path,
        sec=5.5,          # 第 5.5 秒
        temp_dir=temp_folder,
        te=20,            # Top: 80%
        be=20,            # Bottom: 20%
        le=20,            # Left: 30%
        re=20             # Right: 70%
    )

    if result_path:
        print(f"成功生成图片: {result_path}")
    else:
        print("生成失败")


exit()
from transformers import pipeline

corrector = pipeline("text2text-generation", model="bmd1905/vietnamese-correction-v2")
# Example
MAX_LENGTH = 512

# Define the text samples
texts = [
    "côn viec kin doanh thì rất kho khan nên toi quyết dinh chuyển sang nghề khac  ",
    "toi dang là sinh diên nam hai ở truong đạ hoc khoa jọc tự nhiên , trogn năm ke tiep toi sẽ chọn chuyen nganh về trí tue nhana tạo",
]

# Batch prediction
predictions = corrector(texts, max_length=MAX_LENGTH)

# Print predictions
s=[]
for text, pred in zip(texts, predictions):
    s.append(pred['generated_text'])
    print("- " + pred['generated_text'])

with open("test.txt","w",encoding='utf-8') as f:
    f.write("\n".join(s))

exit()

import requests
import json,os
import shutil,subprocess


p = subprocess.run(['E:/python/uni/Umi-OCR_Paddle_v2.1.5/Umi-OCR.exe','--hide'], 
capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
print(p.stdout)     
print(p)     
exit()           
try:
    res=requests.head("http://127.0.0.1:1224/api/ocr")
    print(res.status_code)
except requests.exceptions.ConnectionError:
    print('连接失败')


url = "http://127.0.0.1:1224/api/ocr"
data = {
    "base64": "iVBORw0KGgoAAAANSUhEUgAAAC4AAAAXCAIAAAD7ruoFAAAACXBIWXMAABnWAAAZ1gEY0crtAAAAEXRFWHRTb2Z0d2FyZQBTbmlwYXN0ZV0Xzt0AAAHjSURBVEiJ7ZYrcsMwEEBXnR7FLuj0BPIJHJOi0DAZ2qSsMCxEgjYrDQqJdALrBJ2ASndRgeNI8ledutOCLrLl1e7T/mRkjIG/IXe/DWBldRTNEoQSpgNURe5puiiaJehrMuJSXSTgbaby0A1WzLrCCQCmyn0FwoN0V06QONWAt1nUxfnjHYA8p65GjhDKxcjedVH6JOejBPwYh21eE0Wzfe0tqIsEkGXcVcpoMH4CRZ+P0lsQp/pWJ4ripf1XFDFe8GHSHlYcSo9Es31t60RdFlN1RUmrma5oTzTVB8ZUaeeYEC9GmL6kNkDw9BANAQYo3xTNdqUkvHq+rYhDKW0Bj3RSEIpmyWyBaZaMTCrCK+tJ5Jsa07fs3E7esE66HzralRLgJKp0/BD6fJRSxvmDsb6joqkcFXGqMVVFFEHDL2gTxwCAaTabnkFUWhDCHTd9iYrGcAL1ZnqIp5Vpiqh7bCfua7FA4qN0INMcN1+cgCzj+UFxtbmvwdZvGIrI41JiqhZBWhhF8WxorkYPpQwJiWYJeA3rXE4hzcwJ+B96F9zCFHC0FcVegghvFul7oeEE8PvHeJqC0w0AUbbFIT8JnEwGbPKcS2OxU3HMTqD0r4wgEIuiKJ7i4MS16+og8/+bPZRPLa+6Ld2DSzcAAAAASUVORK5CYII=",
    # 可选参数示例
    "options": {
        "data.format": "text",
    }
}
headers = {"Content-Type": "application/json"}
data_str = json.dumps(data)
response = requests.post(url, data=data_str, headers=headers)
response.raise_for_status()
res_dict = json.loads(response.text)
print(res_dict)
exit()
from openai import OpenAI
import os

client = OpenAI(api_key='12314', base_url='http://38.207.176.164:7899/v1')
with  client.audio.speech.with_streaming_response.create( model='tts-1', voice='zh-CN-XiaoyiNeural', input='你好啊，亲爱的朋友们,今天天气不错哦，挺风和日丽的', speed=1.0    ) as response:
  with open('./test.mp3', 'wb') as f:
    for chunk in response.iter_bytes():
      f.write(chunk)
os.system("ffplay test.mp3")
exit()
from multiprocessing import freeze_support

from videotrans.task._speech2text import SpeechToText
from videotrans.task._translate_srt import TranslateSrt
from videotrans.task.trans_create import TransCreate

if __name__ == '__main__':
    freeze_support()
    from videotrans.configure import config
    from videotrans.task._dubbing import DubbingSrt
    from videotrans.task.taskcfg import TaskCfg
    from videotrans.util import gpus,tools
    config.exit_soft=False

    def tts_fun():
        config.box_tts='ing'
        uuid="sgdasgasa32"
        cfg={
            "name":"C:/users/c1/videos/1.srt",
            "noextname":"1",
            "cache_folder": f'{config.TEMP_ROOT}/{uuid}',
            "target_dir": f'{config.ROOT_DIR}/output/{uuid}',
            "target_language_code": "zh-cn",
            "voice_role":"Yunyang(Male/CN)",
            "voice_rate": '+0%',
            "volume": '+0%',
            "uuid": uuid,
            "pitch": '+0Hz',
            "tts_type": 0,
            "voice_autorate": True,
            "align_sub_audio":False
        }
        trk = DubbingSrt(cfg=TaskCfg(**cfg),out_ext='wav')
        trk.dubbing()
        trk.align()
        trk.task_done()

    def stt_fun():
        config.box_recogn='ing'
        uuid="sgdasgasa32"
        cfg={
            "name":"C:/Users/c1/Videos/test/10.mp4",
            "noextname":"10",
            "target_dir": f'{config.ROOT_DIR}/output/{uuid}',
            "cache_folder": f'{config.TEMP_ROOT}/{uuid}',
            "recogn_type":0,
            "model_name":"tiny",
            "cuda":False,
            "detect_language":"zh",
            "remove_noise": False,
            "enable_diariz": False,
            "nums_diariz": -1,
            "rephrase": 0,
            "fix_punc": False
        }
        trk = SpeechToText(cfg=TaskCfg(**cfg),out_format='srt')
        trk.prepare()
        trk.recogn()
        trk.diariz()
        trk.task_done()

    def tsrt_fun():
        config.box_trans='ing'
        uuid="sgdasgasa32"
        cfg={
            "name":"C:/Users/c1/Videos/1.srt",
            "noextname":"1",
            "target_dir": f'{config.ROOT_DIR}/output/{uuid}',
            "cache_folder": f'{config.TEMP_ROOT}/{uuid}',
            "translate_type": 0,
            "source_language_code": 'auto',
            "target_language_code": 'en'
        }
        trk = TranslateSrt(cfg=TaskCfg(**cfg),out_format=0)
        trk.trans()
        trk.task_done()

    def vtv_fun():
        config.current_status='ing'
        uuid="sgdasgasa32"
        cfg={
            "name": "C:/Users/c1/Videos/test/10.mp4",
            "noextname": "10",
            "target_dir": f'{config.ROOT_DIR}/output/{uuid}',
            "cache_folder": f'{config.TEMP_DIR}/{uuid}',
            "recogn_type": 0,
            "model_name": "tiny",
            "cuda": False,
            "detect_language": "zh",
            "remove_noise": False,
            "enable_diariz": False,
            "nums_diariz": -1,
            "rephrase": 0,
            "fix_punc": False,

            "voice_role":"Thomas(Male/GB)",
            "voice_rate": '+0%',
            "volume": '+0%',
            "uuid": uuid,
            "pitch": '+0Hz',
            "tts_type": 0,
            "voice_autorate": True,
            "align_sub_audio":False,


            "translate_type": 0,
            "source_language_code": 'zh-cn',
            "target_language_code": 'en',

            "is_separate":False,
            "recogn2pass":False,
            "subtitle_type":1,
            "clear_cache":True
        }
        trk = TransCreate(cfg=TaskCfg(**cfg))
        trk.prepare()
        trk.recogn()
        trk.trans()
        trk.dubbing()
        trk.align()
        trk.assembling()
        trk.task_done()

    vtv_fun()
    exit()
    print(gpus.getset_gpu())
    print(gpus.get_cudaX())
    # print(tools.simple_wrap("Mark, how are you feeling about China?is just because we didn't get an extra, another bazooka of stimulus on the fiscal side today,just because we got only incremental steps.Just because we only got a little, you know, thin details on the guidelines, inventors,are implementing the fiscal side.It doesn't negate, we got a whole suite of packages before the break, that was drove withthis momentum.Sure, we got excess speculation over the holidays, sure, things got carried away.We are talking about the moves last week being bonkers on the top side.And the fact is, we're still across every single greater China market, 25% is the moment onemonth return, or more than that.",55,language="en"))
    print(tools.simple_wrap("""中国国家发展改革委提出，着力打通供需良性循环的卡点堵点，进一步畅通国内大循环。据财联社报道，中国国家发展改革委国民经济综合司司长周陈星期二（1月20日）在国新办新闻发布会上表示，国务院近期已部署实施财政金融协同，促进内需一揽子政策，主要就是通过贷款贴息、担保补偿形成1+1>2的政策效果。周陈说，这既是宏观调控和逆周期跨周期调节的综合创新，也是一种转移支付，国家发改委还将积极利用改革创新办法，着力打通供需良性循环的一些卡点堵点，包括清理消费领域的不合理限制，推进消费新业态、新模式、新场景试点，优化投融资机制，完善民营企业参与国家重大项目建设的长效机制等，加快推进全国统一大市场建设，进一步畅通国内大循环。""",3,language="zh"))
    exit()


    exit()
    from videotrans.util import tools


    from transformers import pipeline
    import torch
    pipe = pipeline(
        "image-text-to-text",
        model="google/translategemma-4b-it",
        device="cpu",
        dtype=torch.int8
    )

    # ---- Text Translation ----
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "source_lang_code": "zh",
                    "target_lang_code": "en",
                    "text": "你好啊我的朋友.",
                }
            ],
        }
    ]

    output = pipe(text=messages, max_new_tokens=200)
    print(output[0]["generated_text"][-1]["content"])




    exit()
    def _pro(args):
        print(f'{args=}')


    def down_from_modelscope(model_id,callback=None):
        from modelscope.hub.callback import ProgressCallback
        from modelscope.hub.snapshot_download import snapshot_download
        class Pro(ProgressCallback):
            def __init__(self,*args):
                super().__init__(*args)
            def update(self,size):
                if callback:
                    callback(f'Downloading {self.filename}:{size*100/self.file_size:.2f}%')
                else:
                    print(f'{self.filename=},{self.file_size=},{size=}')
        try:
            snapshot_download(model_id=model_id,local_files_only=True,progress_callbacks=[Pro])
        except ValueError  as e:
            if str(e).find('local_files_only')>-1:
                return snapshot_download(model_id=model_id,progress_callbacks=[Pro])
            raise
        except:
            raise

    down_from_modelscope('iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch',callback=_pro)
    exit()
    from videotrans.util import tools
    def _pro(args):
        print(f'{args=}')

    #tools.down_zip("./models",'https://modelscope.cn/models/himyworld/videotrans/resolve/master/vits-tts.zip',_pro)
    #tools.down_zip("./models",'https://modelscope.cn/models/himyworld/videotrans/resolve/master/m2m100_12b_model.zip',_pro)
    tools.down_zip("./models/real",'https://modelscope.cn/models/himyworld/videotrans/resolve/master/realtimestt.zip',_pro)
    exit()
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks

    inference_pipline = pipeline(
        task=Tasks.speech_timestamp,
        model='iic/speech_timestamp_prediction-v1-16k-offline',
        model_revision="v2.0.4",)

    wav_file = "./20.wav"
    text_file = "五老星系中发现的有机分子，我们离第三类接触还有多远?韦博正式展开拍摄任务已经届满周年,最近也传来了许多过去难以拍摄到的照片。六月初，天文学家在《自然》期刊上发表了这张照片，在蓝色核心外，还绕着一圈橘黄色的光芒，这是一个星系规模的甜甜圈。"
    rec_result = inference_pipline(input=(wav_file, text_file), data_type=("sound", "text"))
    print(rec_result)


    exit()
    def biaodian():
        from funasr import AutoModel

        model = AutoModel(model="ct-punc", model_revision="v2.0.4")

        res = model.generate(input="在五老星系中發現了有幾分子零第三類接觸還有多人啊微波真是展開拍攝任務已經近滿周年最近也傳過來許多過去難以拍攝到的照片6月初天威學家在自然期看上發表了正常照片在藍色核心外 環繞著一圈橘黃色的光芒這是一個新系規模的甜甜圈這是一個傳送門這是外星文明的代生環其實這是一個還有有機務多環方向聽的古老新系他的名字")
        print(res)


    def jiangzoa():
        from modelscope.pipelines import pipeline
        from modelscope.utils.constant import Tasks


        ans = pipeline(
            Tasks.acoustic_noise_suppression,
            model='iic/speech_frcrn_ans_cirm_16k')
        result = ans('60.wav',
            output_path='output.wav')

    def shuohuaren():
        # 版本要求 modelscope version 升级至最新版本 funasr 升级至最新版本
        from modelscope.pipelines import pipeline
        sd_pipeline = pipeline(
            task='speaker-diarization',
            model='iic/speech_campplus_speaker-diarization_common'
        )
        input_wav = 'eng.wav'
        result = sd_pipeline(input_wav)

        # 如果有先验信息，输入实际的说话人数，会得到更准确的预测结果
        result = sd_pipeline(input_wav, oracle_num=2)
        print(result)



    from videotrans.process.prepare_audio import *
    import re

    kw={
        "text_dict":{
        '1': re.sub(r'[,.?!，。？！]',' ','Mark, how are you feeling about China?'),
        '2': re.sub(r'[,.?!，。？！]',' ','Still extremely bullish.'),
        '3': re.sub(r'[,.?!，。？！]',' ','I find some of the perspectives today quite bizarre from investors.'),
        '4': re.sub(r'[,.?!，。？！]',' ',"I thought we'd back out lined it perfectly."),
        '5': re.sub(r'[,.?!，。？！]',' ',"在五老星系中發現了有幾分子零第三類接觸還有多人啊微波真是展開拍攝任務已經近滿周年最近也傳過來許多過去難以拍攝到的照片6月初天威學家在自然期看上發表了正常照片在藍色核心外")
        }
    }
    subs=[
    [0, 2000],
    [3000, 8000],
    [5000, 10000],
    [13000, 18000],
    [23000, 28000],
    [33000, 58000],
    [63000, 108000],
    [113000, 128000],
    [13000, 158000],
    ]
    #out=vocal_bgm(**{"input_file":"10.wav","vocal_file":"10-vocal.wav","instr_file":"10-bgm.wav"})
    out=remove_noise(**{"input_file":"10.wav","output_file":"10-nose.wav"})
    #out=fix_punc(**kw)

    #out=cam_speakers(**{"input_file":"eng.wav","subtitles":subs,"num_speakers":2})
    #out=pyannote_speakers(**{"input_file":"eng.wav","subtitles":subs,"num_speakers":2})
    #out=reverb_speakers(**{"input_file":"eng.wav","subtitles":subs,"num_speakers":2})
    #out=built_speakers(**{"input_file":"eng.wav","subtitles":subs,"num_speakers":2,"language":"en"})
    print(f"{out=}")
    exit()


    exit()
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks
    from funasr import AutoModel
    def param():
        inference_pipeline = pipeline(
            task=Tasks.auto_speech_recognition,
            model='iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch', model_revision="v2.0.4",
            vad_model='iic/speech_fsmn_vad_zh-cn-16k-common-pytorch', vad_model_revision="v2.0.4",
            punc_model='iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch', punc_model_revision="v2.0.3",
            spk_model="iic/speech_campplus_sv_zh-cn_16k-common",
            spk_model_revision="v2.0.2",
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            #trust_remote_code=True,
        )
        rec_result = inference_pipeline('zh20.wav',disable_pbar=True)
        print(rec_result)


    def sense():
        from modelscope.pipelines import pipeline
        from modelscope.utils.constant import Tasks

        inference_pipeline = pipeline(
            task=Tasks.auto_speech_recognition,
            model='iic/SenseVoiceSmall',
            model_revision="master",
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            device="cpu"
            )

        rec_result = inference_pipeline(["zh20.wav","10.wav"],batch_size=2,disable_pbar=True)
        print(rec_result)

    def fun():
        model_name='FunAudioLLM/Fun-ASR-Nano-2512'
        from videotrans.codes.model import FunASRNano
        model = AutoModel(
            model=model_name,
            trust_remote_code=False,
            #vad_model="fsmn-vad",
            #vad_kwargs={"max_single_segment_time": 5000},
            #remote_code=f"{config.ROOT_DIR}/videotrans/codes/model.py",
            device="cpu",
        )
        res = model.generate(input=["zh.wav"], cache={}, batch_size=1)
        #text = res[0]["text"]
        print(res)

    fun()

    exit()
    from modelscope.hub.snapshot_download import snapshot_download


    '''
    _pzh = f'{ROOT_DIR}/models/models/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch'
    for it in ['iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch','iic/fsmn-vad','ct-punc']
    if not Path(_pzh).exists():
        snapshot_download(
            model_id="iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
            local_dir="./models/models/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
        )
    '''









    exit()
    from videotrans.recognition._base import BaseRecogn
    import os, requests, shutil, re, time
    from pathlib import Path

    kwargs = {
        "detect_language": 'zh',
        "audio_file": 'c:/users/c1/videos/240m.wav',
        "cache_folder": './tmp',
        "model_name": 'tiny',
        "uuid": 'asdgaga',
        "is_cuda": False,
        "subtitle_type": 0,
        "recogn_type": 0,
    }

    b = BaseRecogn(**kwargs)

    s = time.time()
    b.get_speech_timestamp('c:/users/c1/videos/240m.wav')

    print(f'用时 {time.time() - s}s')

    exit()
    '''
    
    'kotoba-tech/kotoba-whisper-v2.0',
                #'suzii/vi-whisper-large-v3-turbo-v1',
                'reazon-research/japanese-wav2vec2-large-rs35kh',
                'jonatasgrosman/wav2vec2-large-xlsr-53-japanese'
    '''

    # model_name='kotoba-tech/kotoba-whisper-v2.0'
    # model_name='reazon-research/japanese-wav2vec2-large-rs35kh'
    model_name = 'jonatasgrosman/wav2vec2-large-xlsr-53-japanese'
    # model_name='suzii/vi-whisper-large-v3-turbo-v1'
    local_dir = f'{config.ROOT_DIR}/models/models--' + model_name.replace('/', '--')


    def _whisper_large_japanese(model_name, local_dir):
        _get_modeldir_download(model_name, local_dir)
        p = pipeline(
            task="automatic-speech-recognition",
            model=local_dir,
            device_map="auto",
        )
        generate_kwargs = {"language": 'ja', "task": "transcribe"}

        res = p('ja20.wav', ignore_warning=True, generate_kwargs=generate_kwargs)
        print(res)
        # print(re.sub(r'<unk>|</unk>','',res['text']+"\n"))


    def _get_modeldir_download(model_name, local_dir):
        """
        下载模型到指定目录，保持干净的文件结构。
        """
        Path(local_dir).mkdir(exist_ok=True, parents=True)
        is_file = False
        if [it for it in Path(local_dir).glob('*.bin')] or [it for it in Path(local_dir).glob('*.safetensors')]:
            is_file = True
        if is_file:
            print('已存在模型')
            return
        from huggingface_hub import snapshot_download
        # 先测试能否连接 huggingface.co, 中国大陆地区不可访问，除非使用VPN
        try:
            requests.head('https://huggingface.co', timeout=5)
        except Exception:
            print('无法连接 huggingface.co, 使用镜像替换: hf-mirror.com')
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            os.environ["HF_HUB_DISABLE_XET"] = "1"
        else:
            print('可以使用 huggingface.co')
            os.environ['HF_ENDPOINT'] = 'https://huggingface.co'
            os.environ["HF_HUB_DISABLE_XET"] = "0"
        try:
            snapshot_download(
                repo_id=model_name,
                local_dir=local_dir,
                local_dir_use_symlinks=False,
                endpoint=os.environ.get('HF_ENDPOINT'),
                ignore_patterns=["*.msgpack", "*.h5", ".git*"]
            )
        except Exception as e:
            raise RuntimeError(
                config.tr('downloading all files', local_dir) + f'\n[https://huggingface.co/{model_name}/tree/main]\n\n')

        """删除 huggingface_hub 下载时产生的缓存文件夹"""
        junk_paths = [
            ".cache",
            "blobs",
            "refs",
            "snapshots",
            ".no_exist"
        ]

        for junk in junk_paths:
            full_path = Path(local_dir) / junk
            if full_path.exists():
                try:
                    if full_path.is_dir():
                        shutil.rmtree(full_path)  # 强制删除文件夹
                    else:
                        os.remove(full_path)  # 删除文件
                    print(f"已清理: {junk}")
                except Exception as e:
                    print(f"清理 {junk} 失败: {e}")


    _whisper_large_japanese(model_name, local_dir)

    exit()


    # jonatasgrosman/wav2vec2-large-xlsr-53-japanese'
    def _wav2vec2_large_japanese(self):
        self._signal(text=f"load {self.model_name}")
        raws = self.cut_audio()
        import torch
        import librosa
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

        # 1. 加载处理器和模型
        processor = Wav2Vec2Processor.from_pretrained(self.local_dir)
        model = Wav2Vec2ForCTC.from_pretrained(self.local_dir)
        if self.is_cuda:
            model = model.to('cuda')

        for i, it in enumerate(raws):
            speech_array, sampling_rate = librosa.load(it['file'], sr=16_000)

            # 3. 预处理音频数据
            # 将音频数据转换为模型所需的 tensor 格式
            inputs = processor(speech_array, sampling_rate=16_000, return_tensors="pt", padding=True)
            if self.is_cuda:
                inputs = inputs.to('cuda')
            # 4. 模型推理
            print("Transcribing...")
            with torch.no_grad():
                # 获取模型的 logits 输出
                logits = model(inputs.input_values, attention_mask=inputs.attention_mask).logits

            # 5. 解码预测结果
            predicted_ids = torch.argmax(logits, dim=-1)
            # batch_decode 返回的是一个列表，我们要取第一个结果 [0]
            text = processor.batch_decode(predicted_ids)[0]
            del it['file']
            if text:
                it['text'] = text
                self._signal(text=f'{text}\n', type="subtitle")
                self._signal(text=f' Subtitles {i + 1} ')
        try:
            if processor:
                del processor
            if model:
                del model
            if predicted_ids:
                del predicted_ids
        except:
            pass

        return raws


    # reazon-research/japanese-wav2vec2-large-rs35kh
    def _reazon(self):
        self._signal(text=f"load {self.model_name}")
        raws = self.cut_audio()
        import librosa, torch
        import numpy as np
        from transformers import AutoProcessor, Wav2Vec2ForCTC

        # 1. 加载处理器和模型

        model = Wav2Vec2ForCTC.from_pretrained(
            self.local_dir,
            # torch_dtype=torch.bfloat32 if not self.is_cuda else torch.bfloat16,
            # attn_implementation="flash_attention_2",
        )  # .to("cuda")
        if self.is_cuda:
            model.to('cuda')
        processor = AutoProcessor.from_pretrained(self.local_dir)

        for i, it in enumerate(raws):
            audio, _ = librosa.load(it['file'], sr=16_000)
            # audio = np.pad(audio)  # Recommend to pad audio before inference
            input_values = processor(
                audio,
                return_tensors="pt",
                sampling_rate=16_000
            ).input_values
            if self.is_cuda:
                input_values = input_values.to("cuda")  # .to(torch.bfloat16)

            with torch.inference_mode():
                logits = model(input_values).logits.cpu()
            predicted_ids = torch.argmax(logits, dim=-1)[0]
            text = processor.decode(predicted_ids, skip_special_tokens=True)  # .removeprefix("▁")
            del it['file']
            print(text)
            if text:
                it['text'] = text
                self._signal(text=f'{text}\n', type="subtitle")
                self._signal(text=f' Subtitles {i + 1} ')
        try:
            if model:
                del model
            if pipe:
                del pipe
            if processor:
                del processor
        except:
            pass

        return raws


    import torch
    from videotrans.configure import config

    import torch
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

    device = "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    model_id = "efwkjn/whisper-ja-anime-v0.3"

    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
    )
    model.to(device)

    processor = AutoProcessor.from_pretrained(model_id)

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype,
        device=device,
    )

    result = pipe("ja20.wav", generate_kwargs={"language": "japanese", "task": "transcribe"})
    print(result["text"])

    exit()
    from videotrans.configure import config
    import os

    os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:10808'
    print(os.environ['HF_TOKEN_PATH'])
    print(os.environ.get('HF_HUB_DISABLE_IMPLICIT_TOKEN'))
    import torch, torchaudio
    import sys

    import pyannote.audio

    torch.serialization.add_safe_globals([
        torch.torch_version.TorchVersion,
        pyannote.audio.core.task.Specifications,
        pyannote.audio.core.task.Problem,
        pyannote.audio.core.task.Resolution
    ])

    from pyannote.audio import Pipeline

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        # f"{os.getcwd()}/models/pyannote",

        # use_auth_token="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",
        cache_dir="./models"

    )

    # send pipeline to GPU (when available)
    # import torch
    # pipeline.to(torch.device("cuda"))

    # apply pretrained pipeline
    waveform, sample_rate = torchaudio.load("523eng.wav")
    diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate}, num_speakers=4)

    # diarization = pipeline("523eng.wav")

    # print the result
    # for turn, _, speaker in diarization.itertracks(yield_label=True):
    #    print(f"start={int(turn.start*1000)}s stop={int(turn.end*1000)}s {speaker=}")


    output = []
    # 获取的说话人数字id可能很乱，并非顺序增长，需要重新整理为0-n递增
    speaker_list = set()
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speaker = speaker.replace('SPEAKER_', '')
        print(f"start={int(turn.start * 1000)}s stop={int(turn.end * 1000)}s {speaker=}")
        speaker_list.add(f'spk{speaker}')
        output.append([[int(turn.start * 1000), int(turn.end * 1000)], f'spk{speaker}'])
    speaker_list = sorted(list(speaker_list))

    # 映射
    spk_neworder_dict = {}
    for i, it in enumerate(speaker_list):
        spk_neworder_dict[it] = f'spk{i}'
    print(f'原始说话人排序后：{speaker_list=}')
    print(f'映射为新说话人标识：{spk_neworder_dict=}')

    print(output)
    for i, it in enumerate(output):
        output[i][1] = spk_neworder_dict.get(it[1], 'spk0')
    print(output)

    exit()
    import os
    import ctranslate2
    import sentencepiece as spm
    from typing import List


    # Adapted from:
    # https://gist.github.com/ymoslem/a414a0ead0d3e50f4d7ff7110b1d1c0d
    # https://github.com/ymoslem/DesktopTranslator

    class M2M100Translator():
        # Refer to https://github.com/ymoslem/DesktopTranslator/blob/main/utils/m2m_languages.json
        # other languages can be added as well
        _LANGUAGE_CODE_MAP = {
            "en": "__en__",
            "zh": "__zh__",
            "fr": "__fr__",
            "de": "__de__",
            "ja": "__ja__",
            "ko": "__ko__",
            "ru": "__ru__",
            "es": "__es__",
            "th": "__th__",
            "it": "__it__",
            "pt": "__pt__",
            "vi": "__vi__",
            "ar": "__ar__",
            "tr": "__tr__",
            "hi": "__hi__",
            "hu": "__hu__",
            "uk": "__uk__",
            "id": "__id__",
            "ms": "__ms__",
            "kk": "__kk__",
            "cs": "__cs__",
            "pl": "__pl__",
            "nl": "__nl__",
            "sv": "__sv__",
            "he": "__he__",
            "bn": "__bn__",
            "fa": "__fa__",
            "fi": "__tl__",
            "ur": "__ur__",
            "yu": "__zh__"
        }

        def __init__(self):
            self.model = ctranslate2.Translator(
                model_path='./models/m2m100_12b',
                device="cpu",
                device_index=0,
            )
            self.model.load_model()
            self.sentence_piece_processor = spm.SentencePieceProcessor(model_file='./models/m2m100_12b/sentencepiece.model')

        def _unload(self):
            self.model.unload_model()
            del self.model
            del self.sentence_piece_processor

        def infer(self, from_lang: str, to_lang: str, queries: List[str]):
            if not from_lang or from_lang == 'auto':
                from_lang = 'auto'
            else:
                from_lang = self._LANGUAGE_CODE_MAP.get(from_lang, 'auto')
            to_lang = self._LANGUAGE_CODE_MAP.get(to_lang)
            queries_tokenized = self.tokenize(queries, from_lang)
            translated_tokenized = self.model.translate_batch(
                source=queries_tokenized,
                target_prefix=[[to_lang]] * len(queries),
                beam_size=5,
                max_batch_size=1024,
                return_alternatives=False,
                disable_unk=True,
                replace_unknowns=True,
                repetition_penalty=3,
            )
            translated = self.detokenize(list(map(lambda t: t[0]['tokens'], translated_tokenized)), to_lang)
            return translated

        def tokenize(self, queries, lang):
            sp = self.sentence_piece_processor
            if isinstance(queries, list):
                return sp.encode(queries, out_type=str)
            else:
                return [sp.encode(queries, out_type=str)]

        def detokenize(self, queries, lang):
            sp = self.sentence_piece_processor
            translation = sp.decode(queries)
            prefix_len = len(lang) + 1
            translation = [''.join(query)[prefix_len:] for query in translation]
            return translation


