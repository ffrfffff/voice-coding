# 模型下载说明

把模型下载到项目内，执行：

```powershell
python tools/download_project_models.py
```

如果模型已经下载在用户缓存里，可以直接复制到当前项目：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\copy_cached_models_to_project.ps1
```

FunASR 模型会放到：

```text
models/modelscope/hub/models/iic/
```

需要的模型链接：

- https://modelscope.cn/models/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch
- https://modelscope.cn/models/iic/speech_fsmn_vad_zh-cn-16k-common-pytorch
- https://modelscope.cn/models/iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch

Whisper 备用模型会放到：

```text
models/huggingface/
```

备用模型链接：

- https://huggingface.co/Systran/faster-whisper-base
- https://huggingface.co/Systran/faster-whisper-small

检查模型：

```powershell
python tools/check_model_cache.py
```
