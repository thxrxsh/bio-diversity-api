from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf


@dataclass
class AudioWindow:
    chunk_index: int
    start_sec: float
    end_sec: float
    audio_bytes: bytes


def load_audio(audio_path: str | Path, target_sr: int = 22050) -> tuple[np.ndarray, int]:
    y, sr = librosa.load(str(audio_path), sr=target_sr, mono=True)
    return y, sr


def split_audio_into_windows(
    audio_path: str | Path,
    window_sec: float = 3.0,
    target_sr: int = 22050,
    include_last_partial: bool = False,
    min_last_window_sec: float | None = None,
) -> list[AudioWindow]:
    y, sr = load_audio(audio_path=audio_path, target_sr=target_sr)

    samples_per_window = int(window_sec * sr)
    total_samples = len(y)
    windows: list[AudioWindow] = []

    if total_samples == 0:
        return windows

    chunk_index = 0
    start_sample = 0

    while start_sample < total_samples:
        end_sample = start_sample + samples_per_window
        is_partial = end_sample > total_samples

        if is_partial:
            remaining_samples = total_samples - start_sample
            remaining_sec = remaining_samples / sr

            if not include_last_partial:
                break

            if min_last_window_sec is not None and remaining_sec < min_last_window_sec:
                break

        chunk = y[start_sample:min(end_sample, total_samples)]
        if len(chunk) == 0:
            break

        buffer = BytesIO()
        sf.write(buffer, chunk, sr, format="WAV")

        start_sec = start_sample / sr
        end_sec = min(end_sample, total_samples) / sr

        windows.append(
            AudioWindow(
                chunk_index=chunk_index,
                start_sec=round(start_sec, 3),
                end_sec=round(end_sec, 3),
                audio_bytes=buffer.getvalue(),
            )
        )

        chunk_index += 1
        start_sample = end_sample

    return windows
