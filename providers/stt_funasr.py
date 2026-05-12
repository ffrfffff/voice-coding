from __future__ import annotations

import concurrent.futures
import os
import wave
from pathlib import Path

import numpy as np

from providers.stt_whisper import FasterWhisperSTT


MODEL_ALIASES = {
    "paraformer-zh": "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    "fsmn-vad": "speech_fsmn_vad_zh-cn-16k-common-pytorch",
    "ct-punc-c": "punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
}


class FunASRSTT:
    def __init__(self, config: dict, ui):
        self.config = config
        self.ui = ui
        self._model = None
        self._fallback = None

    def transcribe(self, wav_path: Path) -> str:
        try:
            model = self._load_model_with_timeout()
        except Exception as exc:
            self._warning(f"FunASR 加载失败，回退到 Whisper: {exc}")
            return self._fallback_stt().transcribe(wav_path)

        try:
            audio = self._read_audio(wav_path)
            result = model.generate(
                input=audio,
                batch_size_s=int(self.config.get("batch_size_s", 60)),
                hotword=self.config.get("hotwords", ""),
            )
        except Exception as exc:
            self._warning(f"FunASR 识别失败，回退到 Whisper: {exc}")
            return self._fallback_stt().transcribe(wav_path)

        text = self._extract_text(result)
        self._save_transcript(wav_path, text)
        return text

    def _read_audio(self, wav_path: Path) -> np.ndarray:
        with wave.open(str(wav_path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            pcm = wav_file.readframes(frame_count)

        if sample_width != 2:
            raise RuntimeError(f"不支持的 WAV 采样宽度: {sample_width} bytes")

        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        if channels > 1:
            audio = audio.reshape(-1, channels).mean(axis=1)

        target_sample_rate = int(self.config.get("sample_rate", 16000))
        if sample_rate != target_sample_rate:
            try:
                import librosa

                audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=target_sample_rate)
            except Exception as exc:
                raise RuntimeError(f"音频采样率为 {sample_rate}，重采样到 {target_sample_rate} 失败: {exc}") from exc
        return np.asarray(audio, dtype=np.float32)

    def _load_model_with_timeout(self):
        if self._model is not None:
            return self._model
        timeout = int(self.config.get("load_timeout_seconds", 90))
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(self._load_model)
            return future.result(timeout=timeout)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _load_model(self):
        if self._model is not None:
            return self._model

        try:
            from funasr import AutoModel
        except ImportError as exc:
            raise RuntimeError("缺少 FunASR 依赖，请先运行: pip install -r requirements.txt") from exc

        model_name = self._resolve_model(self.config.get("model", "paraformer-zh"))
        vad_model = self._resolve_model(self.config.get("vad_model", "fsmn-vad"))
        punc_model = self._resolve_model(self.config.get("punc_model", "ct-punc-c"))
        model_revision = self.config.get("model_revision", "v2.0.4")
        self._status(f"正在加载 FunASR 模型: {model_name}")
        self._model = AutoModel(
            model=model_name,
            model_revision=model_revision,
            vad_model=vad_model,
            vad_model_revision=self.config.get("vad_model_revision", model_revision),
            punc_model=punc_model,
            punc_model_revision=self.config.get("punc_model_revision", model_revision),
            disable_update=True,
            device=self.config.get("device", "cpu"),
            model_hub=self.config.get("model_hub", "ms"),
        )
        return self._model

    def _resolve_model(self, model_name: str) -> str:
        if not bool(self.config.get("use_local_cache", True)):
            return model_name
        if Path(model_name).exists():
            return model_name

        cache_name = MODEL_ALIASES.get(model_name, model_name)
        configured_cache_root = self.config.get("local_cache_root")
        if configured_cache_root:
            cache_root = Path(configured_cache_root)
            if not cache_root.is_absolute():
                cache_root = Path.cwd() / cache_root
        else:
            cache_root = Path(os.environ.get("MODELSCOPE_CACHE", Path.home() / ".cache" / "modelscope"))
        candidates = [
            cache_root / "hub" / "models" / "iic" / cache_name,
            cache_root / "hub" / "models" / "damo" / cache_name,
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return model_name

    def _fallback_stt(self):
        if self._fallback is not None:
            return self._fallback
        fallback_config = {
            "provider": "faster_whisper",
            "profile": "fallback",
            "language": "zh",
            "model": self._resolve_huggingface_model(self.config.get("fallback_model", "base")),
            "device": "auto",
            "compute_type": "int8",
            "beam_size": int(self.config.get("fallback_beam_size", 2)),
            "vad_filter": True,
            "initial_prompt": "这是一段中文编程语音指令，可能会提到 Claude、Codex、代码、项目、测试、修复。",
            "hotwords": self.config.get("hotwords", ""),
        }
        self._fallback = FasterWhisperSTT(fallback_config, self.ui)
        return self._fallback

    def _resolve_huggingface_model(self, model_name: str) -> str:
        aliases = {
            "base": "models--Systran--faster-whisper-base",
            "small": "models--Systran--faster-whisper-small",
        }
        cache_root = Path(self.config.get("fallback_local_cache_root", "models/huggingface"))
        if not cache_root.is_absolute():
            cache_root = Path.cwd() / cache_root
        model_dir = cache_root / aliases.get(model_name, model_name)
        snapshots = model_dir / "snapshots"
        if snapshots.exists():
            snapshot_dirs = [path for path in snapshots.iterdir() if path.is_dir()]
            if snapshot_dirs:
                return str(snapshot_dirs[0])
        return model_name

    def _extract_text(self, result) -> str:
        if isinstance(result, str):
            return result.strip()
        if isinstance(result, dict):
            return str(result.get("text", "")).strip()
        if isinstance(result, list):
            texts = []
            for item in result:
                if isinstance(item, dict):
                    texts.append(str(item.get("text", "")).strip())
                else:
                    texts.append(str(item).strip())
            return "".join(texts).strip()
        return str(result).strip()

    def _save_transcript(self, wav_path: Path, text: str) -> None:
        transcript_dir = wav_path.parent.parent / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = transcript_dir / f"{wav_path.stem}.txt"
        transcript_path.write_text(text, encoding="utf-8")
        self._status(f"FunASR 识别完成，文本已保存: {transcript_path}")

    def _status(self, message: str) -> None:
        if self.ui is not None:
            self.ui.status(message)

    def _warning(self, message: str) -> None:
        if self.ui is not None:
            self.ui.warning(message)
