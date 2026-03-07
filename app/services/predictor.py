from __future__ import annotations

from pathlib import Path

import numpy as np
from tensorflow.keras.models import load_model

from app.core.config import MODEL_PATH
from app.services.audio_preprocessing import load_audio_bytes, preprocess_bytes
from app.services.distance_estimator import estimate_distance

CLASS_NAMES = ["leopard", "non_leopard"]


class LeopardPredictor:
    def __init__(self, model_path: str | Path = MODEL_PATH) -> None:
        self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(f"Leopard model not found at {self.model_path}")

        self.model = load_model(self.model_path)

    def predict(self, audio_bytes: bytes) -> dict:
        x = preprocess_bytes(audio_bytes)
        x = np.expand_dims(x, axis=0)

        probs = self.model.predict(x, verbose=0)[0]
        class_idx = int(np.argmax(probs))
        confidence = float(probs[class_idx])
        label = CLASS_NAMES[class_idx]

        audio_wave = load_audio_bytes(audio_bytes)
        distance = estimate_distance(audio_wave)

        return {
            "label": label,
            "is_leopard": label == "leopard",
            "confidence": confidence,
            "probabilities": {
                "leopard": float(probs[0]),
                "non_leopard": float(probs[1]),
            },
            "distance": distance,
        }


_predictor_instance: LeopardPredictor | None = None


def get_predictor() -> LeopardPredictor:
    global _predictor_instance

    if _predictor_instance is None:
        _predictor_instance = LeopardPredictor()

    return _predictor_instance
