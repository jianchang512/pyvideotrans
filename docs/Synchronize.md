# 音频视频时间轴对齐原理说明

> *2026-09-24 重构*
>
> 本次优化重构的核心逻辑在于：**从原有的「音视频并行各自按估算值变速」演进为「先视频变速并实测物理时长，再根据真实视频片段时长对音频进行二次精确变速」的两阶段闭环对齐机制**，从而彻底消除了 FFmpeg 视频变速无法精确到毫秒级导致的累积误差。同时补充了第一条字幕左侧强制归零与还原、末尾画面定格（`tpad`）延长等机制。
>

---


本文档详细说明 pyVideoTrans 中「配音、字幕、视频对齐」模块（`videotrans/task/_rate.py` / `SpeedRate`）的实现原理。该模块负责将翻译后的配音音频与原始无声视频在时间轴上精确对齐，最终合并为流畅、音画同步的新视频。

---

## 目录

- [一、问题背景与核心设计理念](#一问题背景与核心设计理念)
- [二、核心挑战与关键解法](#二核心挑战与关键解法)
- [三、对齐策略总览](#三对齐策略总览)
- [四、数据预处理：首尾相连与首段归零](#四数据预处理首尾相连与首段归零)
- [五、变速模式详解](#五变速模式详解)
  - [5.1 模式一：仅音频加速](#51-模式一仅音频加速)
  - [5.2 模式二：仅视频慢速](#52-模式二仅视频慢速)
  - [5.3 模式三：音频加速 + 视频慢速（协同闭环模式）](#53-模式三音频加速--视频慢速协同闭环模式)
  - [5.4 模式四：无变速普通拼接](#54-模式四无变速普通拼接)
- [六、视频慢速与实测补偿机制（第一阶段）](#六视频慢速与实测补偿机制第一阶段)
- [七、音频精确变速实现（第二阶段）](#七音频精确变速实现第二阶段)
- [八、最终音频拼接与画面定格补偿](#八最终音频拼接与画面定格补偿)
- [九、TtsSpeedRate：纯字幕配音场景](#九ttsspeedrate纯字幕配音场景)
- [十、环境配置与编码参数控制](#十环境配置与编码参数控制)
- [附录：完整双阶段执行流程图](#附录完整双阶段执行流程图)

---

## 一、问题背景与核心设计理念

在视频翻译流程中，配音（TTS）生成的时长往往与原视频说话人字幕时长不一致：
- **原始字幕**：例如中文原声 `0:03.000 ~ 0:06.000`（时长 3.0 秒）。
- **翻译配音**：例如英文译文配音实际耗时 `4.5 秒`。
- **冲突**：若直接混合，配音将溢出 1.5 秒，导致画面滞后、多句叠加或音画严重脱节。

### 核心设计理念：先视频后音频，闭环消差
传统方法同时对视频和音频按理论值做变速，但因为 **FFmpeg 视频慢速无法精确到毫秒（受 GOP、帧时间戳限制，每段有几十到数百毫秒误差），长视频随着切片增多，音画累积漂移越来越大**。

新版采用**两阶段流水线设计**：
1. **第一阶段（视频慢速）**：先对视频切片进行慢速处理，并在切片生成后**立刻探测读取实际生成的视频物理时长（`actual_duration`）**。
2. **第二阶段（音频变速）**：根据已落地的**真实视频物理时长**反向作为音频加速的目标值，利用 `pyrubberband` 的高精度时间拉伸算法，将音画误差最终收敛消除为 0。

---

## 二、核心挑战与关键解法

| 挑战 | 表现现象 | 优化解决方案 |
|------|---------|-------------|
| **FFmpeg 剪切/PTS 误差** | FFmpeg PTS 变速受帧边界限制，单片段存在 20~200ms 漂移，累加后导致大脱节 | **先视频后音频**：视频慢速后用 `get_video_duration` 实测物理时长，音频依据真实时长做精确拉伸。 |
| **片头空白段漂移** | 原视频前几秒可能无声音，若字幕不从 0 秒算起，首句处理易产生位移 | **首段强制归零**：将第 0 条字幕 `start_time` 强制设为 0 吸收间隙，拼接前再恢复左侧偏移补静音。 |
| **字幕间静音浪费** | 字幕之间存在几十至上千毫秒的停顿间隙 | **时间轴首尾相连扩展**：每条字幕 `end_time` 延伸至下一条 `start_time`，充分利用空闲区间减少加速失真。 |
| **配音超出视频总长** | 最后一句话过长或累计时长超出原视频时长 | **画面定格延长 (`tpad`)**：复制原视频最后一帧延长画面，避免结尾音频被截断或视频黑屏。 |

---

## 三、对齐策略总览

系统支持通过界面配置两个核心标志位：`should_audiorate`（音频加速）与 `should_videorate`（视频慢速）。

| 模式 | `should_audiorate` | `should_videorate` | 核心逻辑与执行流程 |
|------|:---:|:---:|------|
| **仅音频加速** | ✅ | ✗ | 视频完全不处理；配音大于字幕区间时，音频加速至字幕时长（上限受 `max_audio_speed_rate` 控制）。 |
| **仅视频慢速** | ✗ | ✅ | 音频不做变速；视频片段慢放以适应配音长度（上限受 `max_video_pts_rate` 控制）。 |
| **协同处理（推荐）** | ✅ | ✅ | **各负担一半时间差**：视频慢速至中点 -> 测量视频实际时长 -> 音频加速精确匹配视频实际时长。 |
| **无变速拼接** | ✗ | ✗ | 音视频均不变速；按时间戳插空静音直接拼接；支持移除中间静音或对齐字幕时间轴。 |

---

## 四、数据预处理：首尾相连与首段归零

在 `_prepare_data()` 中，对原始字幕时间轴与配音进行规范化清洗：

### 4.1 首段强制归零（`audio0_left_pad`）
如果第 0 条字幕开始时间大于 0（例如原片前 2.5 秒没人说话），系统将第 0 条字幕开始时间强制设为 0，并记录偏移量：
```python
if self.queue_tts[0]['start_time'] > 0:
    self.audio0_left_pad = self.queue_tts[0]['start_time']
    self.queue_tts[0]['start_time'] = 0
```
**作用**：吞并开头的短空隙，使得视频切片从 0 秒无缝开始，避免第一段视频切片遗漏开头的非语音画面。在最终音频拼接时，会根据第 0 条音频真实时长智能还原左侧静音。

### 4.2 消除字幕间隙（首尾相连）
为防止加速过于激进，将每条字幕的结束时刻无缝连接到下一条的开始时刻：
```python
if i < len(self.queue_tts) - 1:
    next_sub = self.queue_tts[i + 1]
    current['end_time'] = next_sub['start_time']
    current['end_time_source'] = next_sub['start_time']
```
最后一条字幕的结束时刻则直接锚定视频总时长 `self.raw_total_time`。这样充分利用了句子之间的停顿静音区间。

### 4.3 缺失配音占位
若某条字幕缺失配音文件，系统自动生成对应的等长静音文件占位，防止管道中断。

---

## 五、变速模式详解

### 5.1 模式一：仅音频加速
- **触发条件**：`should_audiorate=True` 且 `should_videorate=False`。
- **目标计算**：
  若配音时长 `dubb_duration > source_duration`：
  $$\text{ratio} = \frac{\text{dubb\_duration}}{\text{source\_duration}}$$
  若 $\text{ratio} > \text{max\_audio\_speed\_rate}$（默认 50），限制目标时长为 $\frac{\text{dubb\_duration}}{\text{max\_audio\_speed\_rate}}$；否则目标时长直接为字幕区间时长 `source_duration`。
- **任务注册**：直接在 `_calculate_adjustments()` 中填入 `self.audio_data`，随后并行执行音频变速。

### 5.2 模式二：仅视频慢速
- **触发条件**：`should_audiorate=False` 且 `should_videorate=True`。
- **目标计算**：
  视频目标时长 $\text{video\_target} = \text{dubb\_duration}$。
  $$\text{PTS} = \frac{\text{video\_target}}{\text{source\_duration}}$$
  PTS 限制在 `max_video_pts_rate`（默认 10）以内。
- **执行过程**：仅切片慢速并拼接视频，不向 `self.audio_data` 注册任务，音频保持原速直接拼接。

### 5.3 模式三：音频加速 + 视频慢速（协同闭环模式）
这是精度最高、音质画质平衡最好的模式。

#### 步骤 1：理论均摊
当 `dubb_duration > source_duration` 时，音频和视频**各自负担一半时间差**：
$$\text{diff} = \text{dubb\_duration} - \text{source\_duration}$$
$$\text{video\_target} = \text{round}\left(\text{source\_duration} + \frac{\text{diff}}{2}\right)$$
$$\text{PTS} = \frac{\text{video\_target}}{\text{source\_duration}}$$

#### 步骤 2：视频慢速并实测
按 `video_target` 对视频片段进行裁切变速，提取实际视频切片时长 `_actual_duration`。

#### 步骤 3：动态构建音频加速任务
在 `_video_speeddown` 完成后，使用测量出的**实际切片时长**重写音频目标时长：
```python
self.audio_data.append({
    "filename": self.queue_tts[i]['filename'],
    "dubb_time": self.queue_tts[i]['dubb_time'],  # 变速前实际配音时长
    "target_time": _actual_duration               # 变速后精确目标 = 实际视频切片物理时长
})
```
由此，音频变速在进入执行阶段前，就已经抹平了视频慢速产生的任何抖动和误差。

### 5.4 模式四：无变速普通拼接
- **触发条件**：两项均未勾选，调用 `_run_no_rate_change_mode()`。
- **特性支持**：
  1. `remove_silent_mid=False` 时：保留句子间隙，生成静音切片补齐。
  2. `remove_silent_mid=True` 时：移除句间空白，紧凑拼接。
  3. `align_sub_audio=True` 时：反向调整字幕时间轴的起始结束点，使其完全与配音声音出现时刻对齐。
  4. 若配音总长超出视频总长，自动触发画面末尾定格延长（`_video_extend`）。

---

## 六、视频慢速与实测补偿机制（第一阶段）

视频裁切变速任务由 `_cut_video_get_duration` 执行，并由 `ProcessPoolExecutor` 多进程并行：

```python
cmd = [
    '-y',
    '-ss', ss_time,
    '-t', f'{source_duration_s:.6f}',
    '-i', input_video_path,
    '-an',
    '-c:v', 'libx264',
    '-g', '1',                        # GOP=1 保证关键帧精确
    '-preset', preset,
    '-crf', crf,
    '-pix_fmt', 'yuv420p'
]
cmd.extend(fps_mode)                  # CFR 或 VFR 模式
cmd.append(os.path.basename(task['filename']))
```

### 6.1 失败安全回退（Fallback）机制
若输出文件不存在或小于 1024 字节，系统自动切换为兜底模式，加入显式 `-vf setpts=PTS` 进行无变速强制重新截取：
```python
if not file_path.exists() or file_path.stat().st_size < 1024:
    cmd_backup = [
        '-y', '-ss', ss_time,
        '-t', f'{source_duration_s:.6f}',
        '-i', input_video_path,
        '-an', '-c:v', 'libx264', '-g', '1',
        '-preset', preset, '-crf', crf, '-pix_fmt', 'yuv420p',
        '-vf', 'setpts=PTS',
    ] + fps_mode
    tools.runffmpeg(cmd_backup, force_cpu=True, cmd_dir=work_dir)
```

### 6.2 实际时长抓取
成功切片后，立刻调用 `tools.get_video_duration(task["filename"])` 获取物理媒体时长，记录在 `task['actual_duration']`，作为后续字幕时间轴重建和音频变速的基准值。

---

## 七、音频精确变速实现（第二阶段）

音频变速支持双引擎，优先使用专业时间拉伸工具 **Rubber Band**，降级使用 FFmpeg 的 **atempo**。

### 7.1 Rubber Band 引擎（推荐，音质保真且保音高）
通过 `pyrubberband` 库调用底层库，保持音高不变调整速度：
```python
def _change_speed_rubberband(input_path, target_duration):
    y, sr = sf.read(input_path)
    current_duration = round((len(y) / sr) * 1000)
    time_stretch_rate = current_duration / target_duration
    time_stretch_rate = max(0.2, min(time_stretch_rate, 50.0))

    y_stretched = pyrb.time_stretch(y, sr, time_stretch_rate)

    # 单声道自动转换为双声道，保持通道一致
    if y_stretched.ndim == 1:
        y_stretched = np.column_stack((y_stretched, y_stretched))

    sf.write(input_path, y_stretched, sr)
```

### 7.2 FFmpeg atempo 级联引擎（降级备选）
由于 FFmpeg 的 `atempo` 单个滤镜倍率限制在 `[0.5, 2.0]`，当加速比大于 2.0 时，动态构建串联管道：
```python
atempo_list = []
speed_factor = current_duration_ms / target_duration

while speed_factor > 2.0:
    atempo_list.append("atempo=2.0")
    speed_factor /= 2.0

atempo_list.append(f"atempo={speed_factor}")
filter_str = ",".join(atempo_list)
# 例如 3.0x -> "atempo=2.0,atempo=1.5"
```
最后使用 `-t` 强制截取到目标毫秒，防止样本四舍五入偏差。

---

## 八、最终音频拼接与画面定格补偿

音频变速完毕后，在 `_concat_audio_aligned()` 中组装最终音轨：

### 8.1 首段静音智能还原
预处理时第 0 条字幕被强制移到 0 秒。合并时检查第 0 条配音真实时长 `_audio0_ms` 与区间 `_sub_ms`：
```python
if self.audio0_left_pad > 0:
    _audio0_ms = len(AudioSegment.from_file(self.queue_tts[0]['filename']))
    _sub_ms = self.queue_tts[0]['end_time']
    if _sub_ms > _audio0_ms:
        # 字幕区间大于音频，将第 0 条字幕开始时间右移还原
        _start_time = min(_sub_ms - _audio0_ms, self.audio0_left_pad)
        self.queue_tts[0]['start_time'] = _start_time
        self.queue_tts[0]['source_duration'] = self.queue_tts[0]['end_time'] - _start_time

if self.queue_tts[0]['start_time'] > 0:
    audio_list.append(self._create_silen_file("head_0", self.queue_tts[0]['start_time']))
```
**效果**：确保类似“视频前 3 秒无声”的场景，配音绝不会突兀地从第 0 秒提前抢跑，而是准确从原时间点发声。

### 8.2 逐槽位装填与尾部补齐
遍历配音切片：
1. 若实际配音时长短于视频切片区间：在当前配音尾部追加生成的静音波形文件 `silence_tail_{i}.wav`，填满时间槽位。
2. 更新字幕队列的 `start_time` 和 `end_time`，确保字幕与对应声音完全同步。

### 8.3 尾部对齐与末帧定格（`_video_extend`）
处理到全片末尾时，对比累计音频时长 `_total_ms` 与视频总长 `self.raw_total_time`：
- **音频短于视频**：在音频末尾填充一段静音（`append_video_end`）。
- **音频长于视频**：调用 `_video_extend`，通过 FFmpeg 的 `tpad` 滤镜克隆最后一帧画面进行定格延展：
  ```python
  cmd = [
      '-y', '-i', os.path.basename(self.novoice_mp4),
      '-vf', f'tpad=stop_mode=clone:stop_duration={sec:.3f}',
      '-c:v', 'libx264',
      '-crf', f'{settings.get("crf", 23)}',
      '-preset', settings.get('preset', 'veryfast'),
      '-an', 'final_video_with_freeze_lastend.mp4'
  ]
  ```
  定格延展后，重新探测新视频实际时长，若仍有微小间隙，再次以静音补齐。

---

## 九、TtsSpeedRate：纯字幕配音场景

针对独立于视频的「文本/字幕批量配音」场景，`TtsSpeedRate` 继承自 `SpeedRate`，做出了轻量化裁剪：
1. **禁用视频处理**：`self.should_videorate = False`，不执行视频慢速与画面裁切。
2. **强制对齐**：只要配音时长超出字幕设定时长，无视阈值，直接将配音音频加速至字幕限定时长。
3. **保持原序拼接**：保持首部 gap 填充和段落尾部静音补充，输出纯净的单一对齐音频。

---

## 十、环境配置与编码参数控制

### 10.1 外部参数配置
模块启动时自动检测项目根目录下的配置文件：
- `crf.txt`：读取自定义画质 CRF 值（默认：`18`）。
- `preset.txt`：读取编码速度预设（默认：`veryfast`，可选 `ultrafast`, `medium`, `slow` 等）。
- `settings.get('fps_mode')`：若设置为 `cfr`，自动获取输入视频的恒定帧率并添加 `-r {fps} -fps_mode cfr` 参数。

### 10.2 并发与路径规范
- **进程数自适应**：多进程池采用 `_wok = min(12, len(tasks), max(os.cpu_count() - 1, 1))`，兼顾高吞吐与系统稳定性。
- **跨平台路径**：全面基于 `pathlib.Path` 并统一转换为 `.as_posix()`，使用 `cmd_dir=cache_folder` 作为工作目录，杜绝 Windows 中文字符及反斜杠转义问题。

---

## 附录：完整双阶段执行流程图

```text
                       ┌───────────────────────────────┐
                       │   输入: queue_tts + 视频/配音  │
                       └───────────────┬───────────────┘
                                       │
                       ┌───────────────┴───────────────┐
                       │  开启了视频慢速或音频加速？    │
                       └───────────────┬───────────────┘
                                       │
                   ┌───────────────────┴───────────────────┐
                  是                                       否
                   │                                       │
         ┌─────────┴─────────┐                   ┌─────────┴─────────┐
         │  _prepare_data()  │                   │ _run_no_rate_     │
         │ - 首首尾尾时间相连 │                   │   change_mode()   │
         │ - 首条起点设为 0  │                   │ 无变速直接拼合音频 │
         │ - 记录原音频起点  │                   └─────────┬─────────┘
         └─────────┬─────────┘                             │
                   │                                       │
         ┌─────────┴──────────┐                            │
         │_calculate_         │                            │
         │ adjustments()      │                            │
         │ 规划 PTS 与目标时长 │                            │
         └─────────┬──────────┘                            │
                   │                                       │
        ┌──────────┴──────────┐                            │
       【第一阶段：视频慢速】 │                            │
        │ 裁剪慢速切片 mp4    │                            │
        │ 实测切片 actual_dur │                            │
        │ 拼接新视频 novoice  │                            │
        └──────────┬──────────┘                            │
                   │                                       │
        ┌──────────┴──────────┐                            │
       【第二阶段：音频变速】 │                            │
        │ 以实测切片实际时长  │                            │
        │ 作为音频目标时长    │                            │
        │ Rubberband 精确变速 │                            │
        └──────────┬──────────┘                            │
                   │                                       │
         ┌─────────┴──────────┐                            │
         │_concat_audio_      │                            │
         │ aligned()          │◄───────────────────────────┘
         │ - 智能恢复首段偏移 │
         │ - 逐槽位装填补静音 │
         │ - 超长末帧定格延展 │
         └─────────┬──────────┘
                   │
         ┌─────────┴──────────┐
         │ _exec_concat_audio │
         │ FFmpeg Concat 无损 │
         └─────────┬──────────┘
                   │
         ┌─────────┴──────────┐
         │ 输出: 最终对齐新视频│
         │     + 精准对齐字幕 │
         └────────────────────┘
```