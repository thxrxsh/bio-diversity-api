from pathlib import Path

from app.services.predictor import LeopardPredictor


service = LeopardPredictor()
audio_bytes = Path("samples/sample.mp3").read_bytes()
result = service.predict(audio_bytes)

print(result)
