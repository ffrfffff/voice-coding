$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$copies = @(
  @{
    Source = "$env:USERPROFILE\.cache\modelscope\hub\models\iic\speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
    Dest = "$root\models\modelscope\hub\models\iic\speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
  },
  @{
    Source = "$env:USERPROFILE\.cache\modelscope\hub\models\iic\speech_fsmn_vad_zh-cn-16k-common-pytorch"
    Dest = "$root\models\modelscope\hub\models\iic\speech_fsmn_vad_zh-cn-16k-common-pytorch"
  },
  @{
    Source = "$env:USERPROFILE\.cache\modelscope\hub\models\iic\punc_ct-transformer_zh-cn-common-vocab272727-pytorch"
    Dest = "$root\models\modelscope\hub\models\iic\punc_ct-transformer_zh-cn-common-vocab272727-pytorch"
  },
  @{
    Source = "$env:USERPROFILE\.cache\huggingface\hub\models--Systran--faster-whisper-base"
    Dest = "$root\models\huggingface\models--Systran--faster-whisper-base"
  },
  @{
    Source = "$env:USERPROFILE\.cache\huggingface\hub\models--Systran--faster-whisper-small"
    Dest = "$root\models\huggingface\models--Systran--faster-whisper-small"
  }
)

foreach ($item in $copies) {
  if (!(Test-Path $item.Source)) {
    Write-Host "Missing source: $($item.Source)"
    continue
  }
  $destParent = Split-Path -Parent $item.Dest
  New-Item -ItemType Directory -Path $destParent -Force | Out-Null
  Write-Host "Copying:"
  Write-Host "  from $($item.Source)"
  Write-Host "  to   $($item.Dest)"
  Copy-Item -LiteralPath $item.Source -Destination $item.Dest -Recurse -Force
}

Write-Host "Done. Run: python tools/check_model_cache.py"
