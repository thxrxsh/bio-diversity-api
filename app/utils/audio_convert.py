from __future__ import annotations

import os
import subprocess
from pathlib import Path


class AudioConversionError(Exception):
    pass


def normalize_audio_to_wav(
    input_path: str | Path,
    output_dir: str | Path,
    output_name: str | None = None,
    sample_rate: int = 16000,
    channels: int = 1,
) -> str:
    """
    Convert any uploaded audio file to a normalized WAV file.
    Output is PCM 16-bit mono WAV at the given sample rate.
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if output_name is None:
      output_name = f"{input_path.stem}_normalized.wav"

    output_path = output_dir / output_name

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ac",
        str(channels),
        "-ar",
        str(sample_rate),
        "-acodec",
        "pcm_s16le",
        str(output_path),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise AudioConversionError(
            f"ffmpeg conversion failed: {result.stderr.strip()}"
        )

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise AudioConversionError("Converted WAV file was not created correctly")

    return str(output_path)


def guess_extension(filename: str | None, content_type: str | None) -> str:
    if filename and "." in filename:
        return os.path.splitext(filename)[1].lower()

    mapping = {
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/wave": ".wav",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/aac": ".aac",
        "audio/ogg": ".ogg",
        "audio/webm": ".webm",
    }

    return mapping.get((content_type or "").lower(), ".bin")