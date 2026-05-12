from __future__ import annotations

from pathlib import Path


class FasterWhisperSTT:
    def __init__(self, config: dict, ui):
        self.config = config
        self.ui = ui
        self._model = None

    def transcribe(self, wav_path: Path) -> str:
        model = self._load_model()
        beam_size = int(self.config.get("beam_size", self._default_beam_size()))
        segments, info = model.transcribe(
            str(wav_path),
            language=self.config.get("language", "zh"),
            vad_filter=bool(self.config.get("vad_filter", True)),
            vad_parameters=self.config.get("vad_parameters"),
            beam_size=beam_size,
            best_of=int(self.config.get("best_of", 1)),
            temperature=0,
            no_speech_threshold=self.config.get("no_speech_threshold", 0.6),
            log_prob_threshold=self.config.get("log_prob_threshold", -1.0),
            repetition_penalty=float(self.config.get("repetition_penalty", 1.0)),
            condition_on_previous_text=False,
            initial_prompt=self.config.get("initial_prompt") or None,
            hotwords=self.config.get("hotwords") or None,
        )
        text = "".join(segment.text for segment in segments).strip()
        transcript_dir = wav_path.parent.parent / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = transcript_dir / f"{wav_path.stem}.txt"
        transcript_path.write_text(text, encoding="utf-8")
        language = getattr(info, "language", "unknown")
        self.ui.status(f"\u8bc6\u522b\u5b8c\u6210\uff0c\u8bed\u8a00={language}\uff0c\u6587\u672c\u5df2\u4fdd\u5b58: {transcript_path}")
        return text

    def _default_beam_size(self) -> int:
        profile = self.config.get("profile", "fast")
        return 1 if profile == "fast" else 5

    def _load_model(self):
        if self._model is not None:
            return self._model

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("\u7f3a\u5c11 faster-whisper\uff0c\u8bf7\u5148\u8fd0\u884c: pip install -r requirements.txt") from exc

        device = self.config.get("device", "auto")
        compute_type = self.config.get("compute_type", "int8")
        model_name = self.config.get("model", "base")
        self.ui.status(f"\u6b63\u5728\u52a0\u8f7d Whisper \u6a21\u578b: {model_name} ({device}, {compute_type})")
        self._model = WhisperModel(model_name, device=device, compute_type=compute_type)
        return self._model
