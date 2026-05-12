from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MODELS = {
    "Project FunASR Paraformer": ROOT / "models" / "modelscope" / "hub" / "models" / "iic" / "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    "Project FunASR VAD": ROOT / "models" / "modelscope" / "hub" / "models" / "iic" / "speech_fsmn_vad_zh-cn-16k-common-pytorch",
    "Project FunASR Punctuation": ROOT / "models" / "modelscope" / "hub" / "models" / "iic" / "punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
    "Project faster-whisper base": ROOT / "models" / "huggingface" / "models--Systran--faster-whisper-base",
    "Project faster-whisper small": ROOT / "models" / "huggingface" / "models--Systran--faster-whisper-small",
    "User FunASR Paraformer": Path.home() / ".cache" / "modelscope" / "hub" / "models" / "iic" / "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    "User FunASR VAD": Path.home() / ".cache" / "modelscope" / "hub" / "models" / "iic" / "speech_fsmn_vad_zh-cn-16k-common-pytorch",
    "User FunASR Punctuation": Path.home() / ".cache" / "modelscope" / "hub" / "models" / "iic" / "punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
    "User faster-whisper base": Path.home() / ".cache" / "huggingface" / "hub" / "models--Systran--faster-whisper-base",
    "User faster-whisper small": Path.home() / ".cache" / "huggingface" / "hub" / "models--Systran--faster-whisper-small",
}


def size_mb(path: Path) -> float:
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file()) / 1024 / 1024


def main() -> int:
    print(f"Project root={ROOT}")
    for name, path in MODELS.items():
        if path.exists():
            print(f"FOUND {name}: {path} ({size_mb(path):.1f} MB)")
        else:
            print(f"MISSING {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
