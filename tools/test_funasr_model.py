from __future__ import annotations

from pathlib import Path
import math
import sys
import wave

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.config import load_config
from providers.stt_funasr import FunASRSTT


class UI:
    def status(self, message: str) -> None:
        print(f"[status] {message}", flush=True)

    def warning(self, message: str) -> None:
        print(f"[warn] {message}", flush=True)

    def error(self, message: str) -> None:
        print(f"[error] {message}", flush=True)


def make_silence_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 16000
    duration_s = 0.35
    samples = np.zeros(int(sample_rate * duration_s), dtype=np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples.tobytes())


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    config = load_config(root / "config.yaml")
    stt_config = dict(config["stt"])
    stt_config["load_timeout_seconds"] = 300
    wav_path = root / "data" / "recordings" / "funasr-smoke-test.wav"
    make_silence_wav(wav_path)

    stt = FunASRSTT(stt_config, UI())
    model = stt._load_model_with_timeout()
    print(f"loaded={type(model).__name__}", flush=True)
    text = stt.transcribe(wav_path)
    print(f"text={text!r}", flush=True)
    print("FunASR smoke test passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
