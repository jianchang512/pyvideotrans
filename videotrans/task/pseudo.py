import numpy as np
import librosa
import soundfile as sf
import random

def process_audio(
    input_wav,
    output_wav,
    pitch_cents_range=(-20, 20),   # 随机音高偏移范围（音分）
    noise_level_db=-70,            # 噪声电平（dB，满幅参考）
    seed=None
):
    """
    对音频进行不可感知的处理，改变声学指纹，但保持：
      - 采样率不变
      - 声道数不变
      - 时长完全不变
      - 听感与原版几乎无差异

    参数
    ----
    input_wav : str  输入 WAV 路径
    output_wav : str 输出 WAV 路径
    pitch_cents_range : tuple  音高随机偏移范围，单位为音分（默认 ±20）
    noise_level_db : float   叠加白噪声的 RMS 电平（默认 -70 dB，完全不可闻）
    seed : int               随机种子，用于结果可复现
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    # 读取原始音频（保持原始采样率，单/立体声自适应）
    y, sr = librosa.load(input_wav, sr=None, mono=False)

    # 统一为 (channels, samples) 格式
    if y.ndim == 1:
        y = y[np.newaxis, :]      # 单声道 -> (1, n)

    original_length = y.shape[1]  # 记录原始样本数

    # -------------------- 1. 微音高偏移（时长不变）--------------------
    n_steps = random.uniform(*pitch_cents_range) / 100.0   # 音分 → 半音数
    if abs(n_steps) > 1e-6:
        for ch in range(y.shape[0]):
            # pitch_shift 内部保证输出长度与输入一致
            y[ch] = librosa.effects.pitch_shift(
                y[ch], sr=sr, n_steps=n_steps
            )

    # -------------------- 2. 叠加极低电平白噪声 --------------------
    if noise_level_db > -120:
        noise_rms = 10 ** (noise_level_db / 20.0)   # 线性 RMS 值
        noise = np.random.randn(*y.shape).astype(np.float32)
        # 将噪声 RMS 调整到目标电平
        noise *= noise_rms / (np.sqrt(np.mean(noise ** 2)) + 1e-10)
        y = y + noise

    # 再次确认长度不变（理论上 pitch_shift 不会改变长度，此处做保护）
    assert y.shape[1] == original_length, "时长意外改变！"

    # -------------------- 3. 防止削波 --------------------
    max_val = np.max(np.abs(y))
    if max_val > 1.0:
        y = y / max_val * 0.99

    # -------------------- 4. 保存为 16-bit WAV --------------------
    if y.shape[0] > 1:
        y_out = y.T          # soundfile 需要 (samples, channels)
    else:
        y_out = y[0]         # 单声道用 1D

    sf.write(output_wav, y_out, sr, subtype='PCM_16')

    print(
        f"处理完成：音高偏移 {n_steps*100:.1f} 音分，"
        f"噪声电平 {noise_level_db} dB，"
        f"输出采样率 {sr} Hz，时长 {original_length/sr:.3f} 秒（不变）"
    )
    return output_wav

