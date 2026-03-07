from __future__ import annotations

import librosa
import numpy as np


def estimate_distance(audio: np.ndarray, sr: int = 22050) -> dict:
    rms = float(np.mean(librosa.feature.rms(y=audio)))
    centroid = float(np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr)))

    if rms > 0.12:
        distance_m = 40
        confidence = 0.7
    elif rms > 0.07:
        distance_m = 80
        confidence = 0.6
    elif rms > 0.03:
        distance_m = 150
        confidence = 0.4
    else:
        distance_m = 250
        confidence = 0.3

    if centroid < 1500:
        distance_m *= 1.2

    distance_m = float(distance_m)

    return {
        "estimated_m": distance_m,
        "min_m": float(distance_m * 0.7),
        "max_m": float(distance_m * 1.5),
        "confidence": confidence,
    }
