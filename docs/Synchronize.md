# 音频视频时间轴对齐原理说明

本文档详细说明 pyVideoTrans 中「配音、字幕、视频对齐」模块（`videotrans/task/_rate.py`）的实现原理。该模块负责将翻译后的配音音频与原始无声视频在时间轴上精确对齐，最终合并为流畅的新视频。

---

## 目录

- [一、问题背景](#一问题背景)
- [二、核心挑战](#二核心挑战)
- [三、对齐策略总览](#三对齐策略总览)
- [四、数据预处理：时间轴扩展](#四数据预处理时间轴扩展)
- [五、模式一：仅音频加速](#五模式一仅音频加速)
- [六、模式二：仅视频慢速](#六模式二仅视频慢速)
- [七、模式三：音频+视频协同](#七模式三音频视频协同)
- [八、模式四：无变速拼接](#八模式四无变速拼接)
- [九、音频变速实现细节](#九音频变速实现细节)
- [十、视频变速实现细节](#十视频变速实现细节)
- [十一、最终音频拼接对齐](#十一最终音频拼接对齐)
- [十二、视频片段拼接](#十二视频片段拼接)
- [十三、TtsSpeedRate：纯配音场景](#十三ttsspeedrate纯配音场景)
- [十四、跨平台兼容性](#十四跨平台兼容性)
- [十五、已知限制与注意事项](#十五已知限制与注意事项)

---

## 一、问题背景

pyVideoTrans 将视频从 A 语言翻译为 B 语言的完整流程：

```text
原始视频(A语言)
    │
    ├─→ 分离无声视频流 (novoice.mp4)
    ├─→ 提取音频 → 语音识别(ASR) → A语言字幕
    ├─→ 翻译 → B语言字幕
    ├─→ 配音(TTS) → 逐条B语言配音音频(wav)
    │
    └─→ 【本模块】将 B语言配音 + B语言字幕 + 无声视频 → 对齐合并 → 新视频
```

**核心矛盾**：不同语言表达同一意思时，音节数和语法结构不同，导致配音时长与原始字幕时长不一致。

**示例**：
- 原始中文字幕片段：`0:03.000 ~ 0:06.000`（时长 3 秒）
- 翻译后英文配音：实际生成 4.2 秒的音频
- 差值：`4.2 - 3.0 = 1.2` 秒的溢出

如果不处理，会导致：
1. 配音与视频画面错位（嘴巴动了但声音还没到）
2. 字幕与声音不同步
3. 多条字幕的时间轴累积漂移

---

## 二、核心挑战

### 2.1 FFmpeg 的精度限制

FFmpeg 处理视频无法精确到毫秒级。使用 PTS（Presentation Time Stamp）进行变速时，最终输出的视频可能比期望时长略短或略长。这种误差在单个片段中很小（几毫秒），但在数百个片段拼接后会累积。

### 2.2 帧率不固定

视频帧率可能是 25fps、29.97fps、30fps 等。某些片段时长可能小于 1 帧，FFmpeg 对这类极短片段进行变速处理大概率会失败。

### 2.3 语言差异的不可预测性

配音时长的变化取决于：
- 源语言和目标语言的音节密度差异
- TTS 引擎的语速特性
- 句子的语法结构差异
- 是否使用了声音克隆（克隆模式下时长变化更不可控）

---

## 三、对齐策略总览

pyVideoTrans 提供四种对齐模式，由两个布尔标志位控制：

| 模式 | `should_audiorate` | `should_videorate` | 说明 |
|------|:---:|:---:|------|
| **仅音频加速** | ✅ | ✗ | 加速配音以匹配字幕时长 |
| **仅视频慢速** | ✗ | ✅ | 慢放视频以匹配配音时长 |
| **音频+视频协同** | ✅ | ✅ | 两者各负担一半时间差 |
| **无变速拼接** | ✗ | ✗ | 直接拼接，用静音填充间隙 |

```text
                    ┌─────────────────────┐
                    │  配音时长 > 字幕时长？  │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │                      │
                   否                      是
                    │                      │
            ┌───────┴───────┐    ┌────────┴────────┐
            │  无需处理      │    │  计算加速倍率     │
            │  直接拼接      │    │  ratio = 配音/字幕 │
            └───────────────┘    └────────┬────────┘
                                          │
                              ┌───────────┴───────────┐
                              │                       │
                     ratio ≤ 1.2               ratio > 1.2
                              │                       │
                     ┌────────┴────────┐    ┌────────┴────────┐
                     │ 仅加速音频      │    │ 音频+视频各半    │
                     │ 无需视频慢速    │    │ 分担时间差       │
                     └─────────────────┘    └─────────────────┘
```

---

## 四、数据预处理：时间轴扩展

### 4.1 问题：字幕间的静音间隙

原始字幕的时间轴通常包含间隙：

```text
字幕1: 0:00.000 ~ 0:03.000  (3s)
       ─────── 静音 0.5s ───────
字幕2: 0:03.500 ~ 0:07.000  (3.5s)
```

如果直接对字幕1的配音加速到 3s，而实际可用空间是 3.5s（到下条字幕开始），就会浪费 0.5s 的缓冲空间，导致不必要的加速。

### 4.2 解决方案：扩展每条字幕的结束时间

在预处理阶段，将每条字幕的 `end_time` 修改为下一条字幕的 `start_time`，从而将静音间隙纳入当前字幕的可用时间范围：

```text
处理前:
字幕1: start=0ms,    end=3000ms   (3s)
字幕2: start=3500ms, end=7000ms   (3.5s)

处理后:
字幕1: start=0ms,    end=3500ms   (3.5s) ← 扩展到下条开始
字幕2: start=3500ms, end=7000ms   (3.5s) ← 最后一条扩展到视频末尾
```

### 4.3 关键代码

```python
def _prepare_data(self):
    """数据清洗与预处理"""
    for i in range(len(self.queue_tts)):
        current = self.queue_tts[i]

        # 保存原始开始时间
        current['start_time_source'] = current['start_time']

        # 有视频慢速且第一条字幕开始时间 < 100ms，从0开始
        if self.should_videorate and i == 0 and current['start_time'] < 100:
            current['start_time_source'] = 0

        # 关键：将结束时间扩展到下一条字幕的开始时间
        if i < len(self.queue_tts) - 1:
            next_sub = self.queue_tts[i + 1]
            current['end_time_source'] = next_sub['start_time']
            current['end_time'] = next_sub['start_time']
        else:
            # 最后一条：扩展到视频末尾
            current['end_time_source'] = self.raw_total_time
            current['end_time'] = self.raw_total_time

        # 计算扩展后的可用时长
        current['source_duration'] = current['end_time_source'] - current['start_time_source']
```

### 4.4 效果对比

```text
假设原始数据:
字幕1: start=1000ms, end=3000ms (2s), 配音=3.5s
字幕2: start=3500ms, end=6000ms (2.5s), 配音=2.0s

处理后:
字幕1: source_duration = 3500 - 1000 = 2500ms (扩展了500ms静音间隙)
字幕2: source_duration = 6000 - 3500 = 2500ms

加速倍率:
字幕1: 3.5 / 2.5 = 1.4x (原本需要 3.5/2.0 = 1.75x)
字幕2: 无需加速 (2.0 < 2.5)
```

**结论**：时间轴扩展将字幕1的加速倍率从 1.75x 降低到 1.4x，显著减少了音频加速的幅度，提升了音质。

---

## 五、模式一：仅音频加速

### 5.1 策略

当配音时长 > 字幕可用时长时，将音频加速到匹配字幕时长。加速倍率不得超过 `max_audio_speed_rate`（默认 100）。

```text
配音: ═══════════════════════  (3500ms)
字幕: ══════════════           (2500ms)
                    ↓ 加速 1.4x
结果: ══════════════           (2500ms) + 静音填充
```

### 5.2 关键代码

```python
# 仅音频加速
if self.should_audiorate and not self.should_videorate:
    if dubb_dur > source_dur:
        ratio = dubb_dur / source_dur
        if ratio > self.max_audio_speed_rate:
            # 超过最大加速倍率，限制加速幅度
            audio_target = int(dubb_dur / self.max_audio_speed_rate)
        else:
            # 加速到匹配字幕时长
            audio_target = source_dur
```

### 5.3 注册加速任务

```python
if self.should_audiorate and audio_target < dubb_dur:
    self.audio_data.append({
        "filename": it['filename'],       # 配音文件路径
        "dubb_time": dubb_dur,            # 原始配音时长
        "target_time": audio_target        # 目标时长（加速后）
    })
```

---

## 六、模式二：仅视频慢速

### 6.1 策略

当配音时长 > 字幕可用时长时，将对应视频片段慢速播放，延长视频时长以匹配配音。PTS 倍率不得超过 `max_video_pts_rate`（默认 10）。

```text
视频片段: ══════════════       (2500ms)
配音:     ═══════════════════  (3500ms)
                      ↓ 慢速 PTS=1.4
结果:     ═══════════════════  (3500ms)
```

### 6.2 PTS 原理

PTS（Presentation Time Stamp）控制视频帧的显示时间。FFmpeg 的 `setpts` 滤镜可以改变 PTS：

```text
setpts=1.0*PTS  → 正常速度
setpts=2.0*PTS  → 慢速 2 倍（每帧显示时间翻倍）
setpts=0.5*PTS  → 加速 2 倍（每帧显示时间减半）
```

### 6.3 关键代码

```python
# 仅视频慢速
elif not self.should_audiorate and self.should_videorate:
    if dubb_dur > source_dur:
        video_target = dubb_dur  # 视频目标时长 = 配音时长
        pts = video_target / source_dur
        if pts > self.max_video_pts_rate:
            # 超过最大慢速倍率，限制慢速幅度
            video_target = int(source_dur * self.max_video_pts_rate)
```

### 6.4 注册视频片段

```python
if self.should_videorate:
    pts = video_target / source_dur if source_dur > 0 else 1.0
    self.video_for_clips.append({
        "start": it['start_time_source'],   # 视频裁切起点
        "end": it['end_time_source'],        # 视频裁切终点
        "target_time": video_target,         # 目标输出时长
        "pts": pts,                          # PTS 倍率
        "tts_index": i,                      # 对应字幕索引
        "line": it['line']                   # 字幕行号
    })
```

---

## 七、模式三：音频+视频协同

### 7.1 策略

当音频加速和视频慢速同时启用时，根据配音/字幕倍率选择不同的协同策略：

| 倍率 (ratio) | 策略 | 说明 |
|:---:|------|------|
| ≤ 1.2 | 仅加速音频 | 倍率较小，音频加速对音质影响小，无需慢速视频 |
| > 1.2 | 各负担一半 | 音频加速和视频慢速各自分担一半时间差 |

```text
示例：字幕 2500ms，配音 6000ms，ratio = 2.4

策略 A（ratio ≤ 1.2）：
  音频加速到 2500ms (2.4x) → 音质损失大
  视频不变 → 2500ms

策略 B（ratio > 1.2，实际使用）：
  diff = 6000 - 2500 = 3500ms
  joint_target = 2500 + 3500/2 = 4250ms
  音频加速到 4250ms (1.41x) → 音质损失小
  视频慢速到 4250ms (PTS=1.7) → 画面略慢但可接受
```

### 7.2 关键代码

```python
elif self.should_audiorate and self.should_videorate:
    if dubb_dur > source_dur:
        ratio = dubb_dur / source_dur
        if ratio <= self.BOTH_MODE_AUDIO_ONLY_THRESHOLD:  # 1.2
            # 倍率较小，仅加速音频即可，无需视频慢速
            audio_target = source_dur
            video_target = source_dur
        else:
            # 倍率较大，音频加速和视频慢速各自负担一半时间差
            diff = dubb_dur - source_dur
            joint_target = int(source_dur + (diff / 2))
            audio_target = joint_target
            video_target = joint_target
```

### 7.3 为什么选择 1.2 作为阈值？

- **音频加速 ≤ 1.2x**：人耳几乎察觉不到音质变化
- **超过 1.2x**：单一手段的副作用开始明显，需要协同分担

---

## 八、模式四：无变速拼接

### 8.1 策略

当音频加速和视频慢速都未启用时，直接按字幕时间轴拼接配音音频，用静音填充间隙，或者当选择了移除静音时直接移除。
如果选择了对齐字幕时间轴，则根据实际音频时长，修改字幕时间轴，以便实现声音开始时字幕显示，声音结束时字幕消失

### 8.2 拼接规则

```text
字幕时间轴:
├── 0ms ──── 1000ms ──── 3500ms ──── 6000ms ──── 8000ms
│   静音      字幕1        字幕2        字幕3
│  (1000ms)  (2500ms)     (2500ms)     (2000ms)

拼接结果:
├── [静音1000ms] + [配音1] + [配音2] + [配音3] + [尾部静音]
```

### 8.3 关键代码

```python
def _run_no_rate_change_mode(self):
    audio_concat_list = []
    total_audio_duration = 0

    for i, it in enumerate(self.queue_tts):
        prev_end = 0 if i == 0 else self.queue_tts[i-1].get('end_pos_for_concat', 0)
        start_time = it['start_time']

        # 计算与前一条的间隙
        gap = start_time - prev_end

        # 如果不移除静音间隙，填充静音
        if not self.remove_silent_mid and gap > 0:
            audio_concat_list.append(self._create_silen_file(f"gap_{i}", gap))
            total_audio_duration += gap

        # 拼接配音文件
        if it.get('filename') and Path(it['filename']).exists():
            audio_concat_list.append(it['filename'])
            dubb_len = len(AudioSegment.from_file(it['filename']))
        # ...

        total_audio_duration += dubb_len
        it['end_pos_for_concat'] = total_audio_duration

        # 对齐字幕时间轴
        if self.align_sub_audio:
            it['start_time'] = total_audio_duration - dubb_len
            it['end_time'] = total_audio_duration

    # 尾部静音：如果音频总时长 < 视频总时长
    if self.raw_total_time > total_audio_duration:
        audio_concat_list.append(
            self._create_silen_file("tail_end", self.raw_total_time - total_audio_duration)
        )
```

---

## 九、音频变速实现细节

### 9.1 两种变速引擎

pyVideoTrans 支持两种音频变速方式，按优先级自动选择：

| 引擎 | 优先级 | 依赖 | 特点 |
|------|:---:|------|------|
| **Rubber Band** | 高 | `pyrubberband` + `rubberband` CLI | 音质最佳，保留音高不变 |
| **FFmpeg atempo** | 低 | FFmpeg（内置） | 无需额外依赖，音质略差 |

### 9.2 Rubber Band 变速

```python
def _change_speed_rubberband(input_path, target_duration):
    # 读取音频
    y, sr = sf.read(input_path)
    current_duration = round((len(y) / sr) * 1000)

    # 计算变速倍率
    time_stretch_rate = current_duration / target_duration
    time_stretch_rate = max(0.2, min(time_stretch_rate, 50.0))

    # 执行变速（保留音高）
    y_stretched = pyrb.time_stretch(y, sr, time_stretch_rate)

    # 单声道转双声道
    if y_stretched.ndim == 1:
        y_stretched = np.column_stack((y_stretched, y_stretched))

    # 写回文件
    sf.write(input_path, y_stretched, sr)
```

**Rubber Band 的优势**：
- 使用 Phase Vocoder 算法，变速时保持音高不变
- 支持大倍率变速（最高 50x）而不会产生明显的音质损失
- 处理速度快，支持多线程

### 9.3 FFmpeg atempo 变速（回退方案）

```python
def _precise_speed_up_audio(input_path, target_duration):
    current_duration_ms = len(AudioSegment.from_file(input_path, format='wav'))

    # atempo 限制：参数必须在 [0.5, 2.0] 之间
    # 超出范围时，链式串联多个 atempo
    atempo_list = []
    speed_factor = current_duration_ms / target_duration

    while speed_factor > 2.0:
        atempo_list.append("atempo=2.0")
        speed_factor /= 2.0

    atempo_list.append(f"atempo={speed_factor}")
    filter_str = ",".join(atempo_list)

    # 示例：8x 加速 → "atempo=2.0,atempo=2.0,atempo=2.0"
    cmd = [
        '-y', '-i', input_path,
        '-filter:a', filter_str,
        '-t', f"{target_duration/1000.0}",  # 强制裁剪到目标时长
        '-ar', "48000", '-ac', "2",
        '-c:a', 'pcm_s16le',
        f'{input_path}-after.wav'
    ]
    tools.runffmpeg(cmd)
    shutil.copy2(f'{input_path}-after.wav', input_path)
```

**atempo 链式串联原理**：

```text
atempo 范围: [0.5, 2.0]

需要 8x 加速:
  8.0 = 2.0 × 2.0 × 2.0
  → "atempo=2.0,atempo=2.0,atempo=2.0"

需要 3x 加速:
  3.0 = 2.0 × 1.5
  → "atempo=2.0,atempo=1.5"

需要 1.3x 加速:
  1.3 < 2.0，无需拆分
  → "atempo=1.3"
```

### 9.4 多进程并行加速

音频变速任务通过 `ProcessPoolExecutor` 并行执行：

```python
def _execute_audio_speedup_rubberband(self):
    _wok = min(12, len(self.audio_data), max(os.cpu_count() - 1, 1))

    with ProcessPoolExecutor(max_workers=int(_wok)) as pool:
        for i, d in enumerate(self.audio_data):
            pool.submit(
                _change_speed_rubberband if HAS_RUBBERBAND else _precise_speed_up_audio,
                d['filename'],
                d['target_time']
            )
```

---

## 十、视频变速实现细节

### 10.1 PTS 变速原理

FFmpeg 的 `setpts` 滤镜通过修改 PTS 实现变速：

```text
原始帧序列:
  帧1(0ms) → 帧2(33ms) → 帧3(66ms) → 帧4(100ms)  [30fps]

setpts=2.0*PTS (慢速 2x):
  帧1(0ms) → 帧2(66ms) → 帧3(132ms) → 帧4(200ms)

setpts=0.5*PTS (加速 2x):
  帧1(0ms) → 帧2(16ms) → 帧3(33ms) → 帧4(50ms)
```

### 10.2 FFmpeg 命令构建

```python
def _cut_video_get_duration(i, task, novoice_mp4_original, preset, crf, fps_mode):
    # 裁切参数
    ss_time = tools.ms_to_time_string(ms=task['start'], sepflag='.')
    source_duration_s = (task['end'] - task['start']) / 1000.0
    target_duration_s = task.get('target_time', source_duration_ms) / 1000.0
    pts_factor = task.get('pts', 1.0)

    cmd = [
        '-y',
        '-ss', ss_time,                    # 起始时间
        '-t', f'{source_duration_s:.6f}',  # 裁切时长
        '-i', input_video_path,
        '-an',                             # 去除音频
        '-c:v', 'libx264',                # 视频编码器
        '-g', '1',                         # GOP=1，确保精确裁切
        '-preset', preset,                 # 编码速度
        '-crf', crf,                       # 质量
        '-pix_fmt', 'yuv420p'              # 像素格式
    ]

    # PTS 变速滤镜
    if abs(pts_factor - 1.0) >= 0.001:
        cmd.extend(['-vf', f'setpts={pts_factor}*PTS'])
    else:
        cmd.extend(['-vf', 'setpts=PTS'])

    cmd.extend(fps_mode)  # VFR 或 CFR 模式
    cmd.extend(['-t', f'{target_duration_s:.6f}'])  # 强制限制输出时长
    cmd.append(os.path.basename(task['filename']))
```

### 10.3 帧率模式选择

```python
self.fps_mode = ["-fps_mode", "vfr"]  # 默认可变帧率

if settings.get('fps_mode') == 'cfr':
    video_fps = tools.get_video_info(novoice_mp4, video_fps=True)
    self.fps_mode = ["-r", f"{video_fps}", "-fps_mode", "cfr"]
```

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| **VFR** (可变帧率) | 允许帧率变化，变速效果更好 | 默认推荐 |
| **CFR** (固定帧率) | 强制固定帧率，兼容性更好 | 某些播放器兼容性问题时使用 |

### 10.4 兜底机制

如果变速处理失败（输出文件 < 1024B），自动回退到无变速裁切：

```python
if not file_path.exists() or file_path.stat().st_size < 1024:
    # 兜底：无变速裁切
    cmd_backup = [
        '-y', '-ss', ss_time,
        '-t', f'{source_duration_s:.6f}',
        '-i', input_video_path,
        '-an', '-c:v', 'libx264',
        '-g', '1', '-preset', preset, '-crf', crf,
        '-pix_fmt', 'yuv420p',
        '-vf', 'setpts=PTS',  # 显式保持原始 PTS
    ] + fps_mode
    cmd_backup.append(os.path.basename(task['filename']))
    tools.runffmpeg(cmd_backup, force_cpu=True, cmd_dir=work_dir)
```

### 10.5 多进程并行处理

```python
def _video_speeddown(self):
    _wok = min(12, len(data), max(os.cpu_count() - 1, 1))

    with ProcessPoolExecutor(max_workers=int(_wok)) as pool:
        for i, d in enumerate(data):
            pool.submit(_cut_video_get_duration, i, d,
                       self.novoice_mp4_original,
                       self.preset, self.crf, self.fps_mode)
```

---

## 十一、最终音频拼接对齐

### 11.1 对齐原则

无论使用哪种变速模式，最终的音频拼接都遵循相同的原则：

1. **每条配音占据一个"槽位"**，槽位时长由变速策略决定
2. **配音短于槽位**：末尾填充静音
3. **配音长于槽位**：截断音频以匹配槽位
4. **配音等于槽位**：直接放入

```text
时间轴:
├── [槽位1: 3500ms] ├── [槽位2: 2500ms] ├── [槽位3: 2000ms] ──→

槽位1 内容:
├── [配音1: 3200ms] + [静音: 300ms]

槽位2 内容:
├── [配音2: 2500ms]  (精确匹配)

槽位3 内容:
├── [配音3: 2800ms] → 截断为 2000ms
```

### 11.2 关键代码

```python
def _concat_audio_aligned(self):
    audio_list = []
    current_timeline = self.queue_tts[0]['start_time']

    # 首部静音
    if current_timeline > 0:
        audio_list.append(self._create_silen_file("head_0", current_timeline))

    for i, it in enumerate(self.queue_tts):
        # 槽位时长：有视频慢速时用视频实际时长，否则用字幕区间时长
        slot_duration = it.get('final_duration', it['source_duration'])

        # 兜底：槽位时长为0时回退
        if slot_duration <= 0:
            slot_duration = max(1, it['source_duration'])

        # 读取配音文件
        seg = AudioSegment.from_file(audio_file)
        current_slot_audio_len = len(seg)

        # 三种情况
        if current_slot_audio_len > slot_duration:
            # 溢出：截断
            cut_seg = seg[:slot_duration]
            cut_seg.export(final_slot_path, format='wav')
            audio_list.append(final_slot_path)

        elif current_slot_audio_len < slot_duration:
            # 不足：补静音
            diff = slot_duration - current_slot_audio_len
            audio_list.append(audio_file)
            audio_list.append(self._create_silen_file(f"tail_{i}", diff))

        else:
            # 精确匹配
            audio_list.append(audio_file)

        # 更新字幕时间轴
        it['start_time'] = current_timeline
        it['end_time'] = current_timeline + slot_duration
        current_timeline += slot_duration

    self._exec_concat_audio(audio_list)
```

### 11.3 静音文件生成

```python
def _create_silen_file(self, name, duration_ms):
    path = Path(self.cache_folder, f"silence_{name}.wav").as_posix()
    duration_ms = max(1, int(duration_ms))
    AudioSegment.silent(duration=duration_ms, frame_rate=48000) \
                .set_channels(2) \
                .export(path, format="wav")
    return path
```

### 11.4 FFmpeg 拼接

```python
def _exec_concat_audio(self, file_list):
    # 生成拼接列表文件
    concat_txt = Path(self.cache_folder, 'final_audio_concat.txt').as_posix()
    tools.create_concat_txt(file_list, concat_txt=concat_txt)

    # FFmpeg concat 拼接
    cmd = [
        '-y', '-f', 'concat', '-safe', '0',
        '-i', concat_txt,
        '-c:a', 'copy',  # 直接复制，不重新编码
        temp_wav
    ]
    tools.runffmpeg(cmd, force_cpu=True, cmd_dir=self.cache_folder)
```

---

## 十二、视频片段拼接

### 12.1 流程

```text
原始无声视频 (novoice.mp4)
    │
    ├─→ 裁切片段1 (clip_0_1.400.mp4)  ← PTS=1.4 慢速
    ├─→ 裁切片段2 (clip_1_1.000.mp4)  ← PTS=1.0 不变
    ├─→ 裁切片段3 (clip_2_1.700.mp4)  ← PTS=1.7 慢速
    │
    └─→ FFmpeg concat 合并 → 新的 novoice.mp4
```

### 12.2 拼接命令

```python
def _concat_video(self, processed_clips):
    # 生成拼接列表
    txt_content = []
    for clip in processed_clips:
        if clip.get('actual_duration', 0) > 0 and Path(clip['filename']).exists():
            txt_content.append(f"file '{clip['filename']}'")

    # FFmpeg concat（直接复制，不重新编码）
    cmd = [
        '-y', '-f', 'concat', '-safe', '0',
        '-i', concat_list,
        '-c', 'copy',  # 无损拼接
        output_path
    ]
    tools.runffmpeg(cmd, force_cpu=True, cmd_dir=self.cache_folder)

    # 替换原始视频
    shutil.move(output_path, self.novoice_mp4)
```

---

## 十三、TtsSpeedRate：纯配音场景

### 13.1 与 SpeedRate 的区别

`TtsSpeedRate` 继承自 `SpeedRate`，专门用于「批量为字幕配音」场景：

| 特性 | SpeedRate | TtsSpeedRate |
|------|-----------|-------------|
| 视频慢速 | 支持 | **禁用**（`should_videorate=False`） |
| 最大加速倍率 | 可配置（默认 100） | 固定 100 |
| 时间轴扩展 | 完整（保存 `start_time_source`） | 简化（仅移动 `end_time`） |
| 输出 | 视频 + 音频 | 仅音频 |

### 13.2 简化的预处理

```python
class TtsSpeedRate(SpeedRate):
    def _prepare_data(self):
        _len = len(self.queue_tts)
        for i in range(_len):
            current = self.queue_tts[i]
            if i < _len - 1:
                # 仅移动结束时间，不保存原始开始时间
                current['end_time'] = self.queue_tts[i + 1]['start_time']

            current['source_duration'] = current['end_time'] - current['start_time']
            # ...
```

### 13.3 简化的计算策略

```python
def _calculate_adjustments(self):
    for i, it in enumerate(self.queue_tts):
        source_dur = it['source_duration']
        dubb_dur = it['dubb_time']

        if dubb_dur > source_dur:
            # 无限制，强制加速到对齐
            self.audio_data.append({
                "filename": it['filename'],
                "dubb_time": dubb_dur,
                "target_time": source_dur
            })
```

---

## 十四、跨平台兼容性

### 14.1 路径处理

所有文件路径使用 `Path.as_posix()` 转换为正斜杠格式，确保 FFmpeg 在 Windows/Linux/macOS 上都能正确解析：

```python
input_video_path = Path(novoice_mp4_original).resolve().as_posix()
work_dir = Path(task['filename']).parent.as_posix()
```

### 14.2 FFmpeg 调用

通过 `tools.runffmpeg()` 统一调用 FFmpeg，自动处理：
- Windows 上的路径空格问题
- FFmpeg 可执行文件的查找（系统 PATH 或内置 `ffmpeg/` 目录）
- 命令参数的正确拼接

### 14.3 进程池

使用 `ProcessPoolExecutor` 而非 `multiprocessing.Pool`，提供更好的跨平台兼容性和资源管理。

### 14.4 文件清理

使用 `Path.glob()` + `Path.unlink()` 替代 `os.scandir()` + `os.remove()`，保持 API 一致性。

---

## 十五、已知限制与注意事项

### 15.1 FFmpeg 精度限制

- FFmpeg 无法精确到毫秒级，PTS 变速后的视频可能比期望时长略短或略长
- 单个片段误差约 10-50ms，数百个片段拼接后可能累积到秒级
- **缓解措施**：最终音频拼接时统一截断或补静音，确保总时长一致

### 15.2 极短片段处理

- 时长 < 1 帧的片段（如 30fps 下 < 33ms）FFmpeg 变速大概率失败
- **缓解措施**：预处理阶段将间隙合并到当前字幕，确保每个片段至少有数百毫秒

### 15.3 音频加速的音质损失

- Rubber Band：加速 ≤ 3x 时音质损失极小，> 5x 时开始出现机械感
- FFmpeg atempo：加速 > 2x 时可能出现轻微的音色变化
- **建议**：对于需要大幅加速的场景（> 3x），考虑同时启用视频慢速协同处理

### 15.4 视频慢速的画面卡顿

- PTS 慢速不会生成新的帧，只是延长每帧的显示时间
- 低帧率视频（如 24fps）慢速 2x 后，每帧显示 83ms，可能出现轻微卡顿感
- **建议**：视频慢速倍率尽量控制在 2x 以内

### 15.5 无效片段过滤

小于 1024 字节的视频片段视为无效（仅包含容器头和元数据），在拼接时自动跳过：

```python
if clip.get('actual_duration', 0) > 0 and Path(clip['filename']).exists():
    # 有效片段，加入拼接列表
    txt_content.append(f"file '{path}'")
else:
    logger.warning(f"[Video-Concat] 忽略无效片段: {clip.get('filename')}")
```

---

## 附录：完整处理流程图

```text
                    ┌──────────────────────────┐
                    │   输入: queue_tts 列表     │
                    │   (每条字幕 + 配音文件)     │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────┴─────────────┐
                    │  should_audiorate 或       │
                    │  should_videorate 启用？   │
                    └────────────┬─────────────┘
                                 │
                  ┌──────────────┴──────────────┐
                  │                             │
                 是                             否
                  │                             │
         ┌────────┴────────┐          ┌─────────┴─────────┐
         │ _prepare_data() │          │ _run_no_rate_      │
         │ 时间轴扩展       │          │ change_mode()      │
         └────────┬────────┘          │ 无变速直接拼接      │
                  │                   └─────────┬─────────┘
         ┌────────┴────────┐                     │
         │ _calculate_     │                     │
         │ adjustments()   │                     │
         │ 计算变速策略     │                     │
         └────────┬────────┘                     │
                  │                              │
    ┌─────────────┴─────────────┐                │
    │                           │                │
 音频变速                    视频变速             │
    │                           │                │
 ┌──┴──┐                  ┌─────┴─────┐          │
 │RB/  │                  │_cut_video │          │
 │atempo│                 │_get_dur-  │          │
 │加速  │                  │ation()   │          │
 └──┬──┘                  │PTS变速    │          │
    │                     └─────┬─────┘          │
    │                           │                │
    │                     ┌─────┴─────┐          │
    │                     │_concat_   │          │
    │                     │video()    │          │
    │                     │拼接视频   │          │
    │                     └─────┬─────┘          │
    │                           │                │
    └─────────────┬─────────────┘                │
                  │                              │
         ┌────────┴────────┐                     │
         │ _concat_audio_  │◄────────────────────┘
         │ aligned()       │
         │ 音频对齐拼接     │
         └────────┬────────┘
                  │
         ┌────────┴────────┐
         │ _exec_concat_   │
         │ audio()         │
         │ FFmpeg 合并      │
         └────────┬────────┘
                  │
         ┌────────┴────────┐
         │ 输出: 最终音频   │
         │ + 更新字幕时间轴 │
         └─────────────────┘
```
