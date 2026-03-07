from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_URL = "sqlite:///./biodiversity.db"
MODEL_PATH = BASE_DIR / "model" / "best_leopard_model.h5"
RECORDINGS_UPLOAD_DIR = BASE_DIR / "uploads" / "recordings"
