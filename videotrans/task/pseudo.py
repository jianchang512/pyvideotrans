"""
音频处理脚本 - 保留人声、音效、环境音，降低/移除背景音乐
用于规避 YouTube 原创检测
"""

import os
import sys
import numpy as np
import librosa
import soundfile as sf
import argparse
import subprocess
import shutil
from pathlib import Path



class Config:
    # 处理强度 0.0-1.0，越高降得越多（但可能影响人声）
    # 推荐: 0.6-0.85，太高可能影响人声
    INTENSITY = 1.0

    # 保留音乐比例 0.0-1.0，设为0则完全移除背景音乐
    # 推荐: 0.0 完全移除 / 0.2-0.3 保留一点音乐感
    KEEP_MUSIC_RATIO = 0.9

    # 是否保留环境音（低于80Hz的风声、雷声等）
    KEEP_AMBIENT = True

    # 人声增强（略微增强人声让对话更清晰）
    VOICE_BOOST = 1.0

    # 输出格式: 'video' 输出处理后的视频, 'audio' 只输出音频
    OUTPUT_MODE = 'audio'

    # 音频采样率
    SAMPLE_RATE = 48000


def spectral_subtraction(y, sr, intensity=1.0):
    """
    谱减法 - 降低背景音乐成分
    """
    y_mono = librosa.to_mono(y)

    stft = librosa.stft(y_mono, n_fft=2048, hop_length=512)
    magnitude = np.abs(stft)
    phase = np.angle(stft)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)

    mask = np.ones_like(magnitude)

    # 背景音乐主要频段 50-400Hz（连续低频）
    music_band = (freqs >= 50) & (freqs <= 400)
    mask[music_band, :] *= (1.0 - intensity * 0.75)

    # 降低 400-800Hz（音乐中频）
    mid_band = (freqs > 400) & (freqs <= 800)
    mask[mid_band, :] *= (1.0 - intensity * 0.5)

    magnitude_processed = magnitude * mask
    stft_processed = magnitude_processed * np.exp(1j * phase)
    y_processed = librosa.istft(stft_processed, hop_length=512)

    return y_processed


def preserve_voice_and_ambient(y, sr, keep_ambient=True, voice_boost=1.0):
    """
    保护人声和环境音
    """
    stft = librosa.stft(y, n_fft=2048, hop_length=512)
    magnitude = np.abs(stft)
    phase = np.angle(stft)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)

    mask = np.ones_like(magnitude)

    # 核心人声基频 (80-280Hz)
    fundamental = (freqs >= 80) & (freqs <= 280)
    mask[fundamental, :] = voice_boost

    # 人声泛音 (280Hz - 4kHz)
    harmonics = (freqs > 280) & (freqs <= 4000)
    mask[harmonics, :] = 0.9 * voice_boost

    # 环境音保护 (<80Hz)
    if keep_ambient:
        ambient_low = freqs < 80
        mask[ambient_low, :] = 1.0

    # 高频音效 (>6kHz)
    ambient_high = freqs > 6000
    mask[ambient_high, :] = 0.7

    # 保留瞬态峰值（音效）
    transient_threshold = np.percentile(magnitude, 90)
    is_transient = magnitude > transient_threshold
    mask[is_transient] = 1.0

    magnitude_protected = magnitude * mask
    stft_protected = magnitude_protected * np.exp(1j * phase)
    y_protected = librosa.istft(stft_protected, hop_length=512)

    return y_protected


def process_audio(audio_path, output_path=None):
    """
    处理音频文件
    """
    config = Config()
    #print("  📂 加载音频...")
    y, sr = librosa.load(audio_path, sr=config.SAMPLE_RATE, mono=False)

    if y.ndim == 1:
        y = np.array([y, y])

    duration = y.shape[-1] / sr
    #print(f"    时长: {duration:.1f}秒 | 采样率: {sr}Hz")

    # 步骤1: 谱减法降低音乐
    #print("  🔊 降低背景音乐...")
    y1 = spectral_subtraction(y, sr, intensity=config.INTENSITY)

    # 步骤2: 保护人声和环境音
    #print("  🎤 保护人声和环境音...")
    y2 = preserve_voice_and_ambient(y1, sr, keep_ambient=config.KEEP_AMBIENT, voice_boost=config.VOICE_BOOST)

    # 步骤3: 进一步清理
    #print("  ✨ 最终处理...")
    y_final = spectral_subtraction(y2, sr, intensity=config.INTENSITY * 0.5)

    # 归一化
    y_final = y_final / (np.max(np.abs(y_final)) + 1e-10) * 0.95



    sf.write(output_path, y_final.T, sr)

    return output_path


