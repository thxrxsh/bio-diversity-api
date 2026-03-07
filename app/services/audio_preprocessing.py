from __future__ import annotations

import io
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

SAMPLE_RATE = 22050
DURATION = 3
TARGET_SAMPLES = SAMPLE_RATE * DURATION

N_FFT = 2048
HOP_LENGTH = 512
N_MELS = 128
N_MFCC = 40

TARGET_FEATURE_HEIGHT = 187
TARGET_FEATURE_WIDTH = 130


def load_audio(file_path: str | Path) -> np.ndarray:
    audio, _ = librosa.load(str(file_path), sr=SAMPLE_RATE, duration=DURATION, mono=True)
    audio, _ = librosa.effects.trim(audio, top_db=20)

    if audio.size > 0:
        audio = librosa.util.normalize(audio)

    if len(audio) < TARGET_SAMPLES:
        audio = np.pad(audio, (0, TARGET_SAMPLES - len(audio)), mode="constant")
    else:
        audio = audio[:TARGET_SAMPLES]

    return audio.astype(np.float32)


def load_audio_bytes(file_bytes: bytes) -> np.ndarray:
    data, sr = sf.read(io.BytesIO(file_bytes), always_2d=False)

    if getattr(data, "ndim", 1) > 1:
        data = np.mean(data, axis=1)

    data = data.astype(np.float32)

    if sr != SAMPLE_RATE:
        data = librosa.resample(data, orig_sr=sr, target_sr=SAMPLE_RATE)

    data, _ = librosa.effects.trim(data, top_db=20)

    if data.size > 0:
        data = librosa.util.normalize(data)

    if len(data) < TARGET_SAMPLES:
        data = np.pad(data, (0, TARGET_SAMPLES - len(data)), mode="constant")
    else:
        data = data[:TARGET_SAMPLES]

    return data.astype(np.float32)


def extract_features(audio: np.ndarray) -> np.ndarray:
    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=SAMPLE_RATE,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
        n_mels=N_MELS,
    )
    mel_db = librosa.power_to_db(mel, ref=np.max)

    mfcc = librosa.feature.mfcc(
        y=audio,
        sr=SAMPLE_RATE,
        n_mfcc=N_MFCC,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
    )

    chroma = librosa.feature.chroma_stft(
        y=audio,
        sr=SAMPLE_RATE,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
    )

    contrast = librosa.feature.spectral_contrast(
        y=audio,
        sr=SAMPLE_RATE,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
    )

    features = np.vstack([mel_db, mfcc, chroma, contrast]).astype(np.float32)

    if features.shape[0] != TARGET_FEATURE_HEIGHT:
        raise ValueError(
            f"Feature height mismatch. Expected {TARGET_FEATURE_HEIGHT}, got {features.shape[0]}"
        )

    return features


def normalize_features(features: np.ndarray) -> np.ndarray:
    mean = np.mean(features)
    std = np.std(features)

    if std < 1e-8:
        std = 1e-8

    return ((features - mean) / std).astype(np.float32)


def fix_feature_width(features: np.ndarray) -> np.ndarray:
    height, width = features.shape

    if height != TARGET_FEATURE_HEIGHT:
        raise ValueError(
            f"Feature height mismatch. Expected {TARGET_FEATURE_HEIGHT}, got {height}"
        )

    if width < TARGET_FEATURE_WIDTH:
        pad_width = TARGET_FEATURE_WIDTH - width
        features = np.pad(features, ((0, 0), (0, pad_width)), mode="constant")
    elif width > TARGET_FEATURE_WIDTH:
        features = features[:, :TARGET_FEATURE_WIDTH]

    return features.astype(np.float32)


def preprocess_file(file_path: str | Path) -> np.ndarray:
    audio = load_audio(file_path)
    features = extract_features(audio)
    features = normalize_features(features)
    features = fix_feature_width(features)
    return np.expand_dims(features, axis=-1).astype(np.float32)


def preprocess_bytes(file_bytes: bytes) -> np.ndarray:
    audio = load_audio_bytes(file_bytes)
    features = extract_features(audio)
    features = normalize_features(features)
    features = fix_feature_width(features)
    return np.expand_dims(features, axis=-1).astype(np.float32)
