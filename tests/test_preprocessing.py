from pathlib import Path

from app.services.audio_preprocessing import preprocess_file


audio_path = Path("samples/sample.mp3")
x = preprocess_file(audio_path)

print("Shape:", x.shape)
print("Dtype:", x.dtype)
print("Min:", x.min())
print("Max:", x.max())
