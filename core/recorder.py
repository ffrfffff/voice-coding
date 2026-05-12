from __future__ import annotations

from datetime import datetime
from pathlib import Path
import wave

import numpy as np


class Recorder:
    def __init__(self, output_dir: Path, sample_rate: int = 16000, channels: int = 1):
        self.output_dir = output_dir
        self.sample_rate = sample_rate
        self.channels = channels
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._frames: list[np.ndarray] = []
        self._stream = None

    def start(self) -> None:
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("缺少 sounddevice，请先运行: pip install -r requirements.txt") from exc

        if self._stream is not None:
            return

        self._frames = []

        def callback(indata, frames, time_info, status):
            self._frames.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            callback=callback,
        )
        self._stream.start()

    def stop_and_save(self) -> Path | None:
        if self._stream is None:
            return None

        self._stream.stop()
        self._stream.close()
        self._stream = None

        if not self._frames:
            return None

        audio = np.concatenate(self._frames, axis=0)
        if audio.size == 0:
            return None

        audio = np.clip(audio, -1.0, 1.0)
        pcm16 = (audio * 32767).astype(np.int16)
        path = self.output_dir / f"recording-{datetime.now().strftime('%Y%m%d-%H%M%S')}.wav"
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm16.tobytes())
        return path
