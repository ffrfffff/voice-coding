from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODELSCOPE_DIR = ROOT / "models" / "modelscope"
HUGGINGFACE_DIR = ROOT / "models" / "huggingface"

FUNASR_MODELS = [
    "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
]

HF_MODELS = [
    "Systran/faster-whisper-base",
    "Systran/faster-whisper-small",
]


def main() -> int:
    MODELSCOPE_DIR.mkdir(parents=True, exist_ok=True)
    HUGGINGFACE_DIR.mkdir(parents=True, exist_ok=True)

    from modelscope import snapshot_download as ms_snapshot_download
    from huggingface_hub import snapshot_download as hf_snapshot_download

    print(f"Project ModelScope cache: {MODELSCOPE_DIR}")
    for model_id in FUNASR_MODELS:
        path = ms_snapshot_download(model_id=model_id, revision="v2.0.4", cache_dir=str(MODELSCOPE_DIR))
        print(f"{model_id} => {path}")

    print(f"\nProject HuggingFace cache: {HUGGINGFACE_DIR}")
    for repo_id in HF_MODELS:
        path = hf_snapshot_download(repo_id=repo_id, cache_dir=str(HUGGINGFACE_DIR))
        print(f"{repo_id} => {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
