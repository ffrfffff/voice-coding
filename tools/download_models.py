from __future__ import annotations

from pathlib import Path


FUNASR_MODELS = [
    "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
]

HF_MODELS = [
    "Systran/faster-whisper-base",
    "Systran/faster-whisper-small",
]


def dir_size_mb(path: Path) -> float:
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file()) / 1024 / 1024


def download_modelscope() -> list[Path]:
    from modelscope import snapshot_download

    paths = []
    for model_id in FUNASR_MODELS:
        print(f"Downloading/checking ModelScope model: {model_id}", flush=True)
        path = Path(snapshot_download(model_id=model_id, revision="v2.0.4"))
        print(f"  OK: {path} ({dir_size_mb(path):.1f} MB)", flush=True)
        paths.append(path)
    return paths


def download_huggingface() -> list[Path]:
    from huggingface_hub import snapshot_download

    paths = []
    for repo_id in HF_MODELS:
        print(f"Downloading/checking HuggingFace model: {repo_id}", flush=True)
        path = Path(snapshot_download(repo_id=repo_id))
        print(f"  OK: {path} ({dir_size_mb(path):.1f} MB)", flush=True)
        paths.append(path)
    return paths


def main() -> int:
    model_paths = []
    model_paths.extend(download_modelscope())
    model_paths.extend(download_huggingface())
    print("")
    print("All requested models are available locally:")
    for path in model_paths:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
