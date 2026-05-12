# 本地语音 Agent 路由器

这是一个本地 Push-to-Talk 语音入口，用语音把任务路由给 Claude Code 或 Codex CLI。

## 启动

```powershell
python app.py
```

默认会启动浏览器实时听写模式，不会加载本地 Whisper 模型。

## 桌面 App 模式

双击：

```text
start_app.vbs
```

它会以独立桌面窗口打开，并在后台自动启动本地 Agent 服务，不显示控制台。

只在后台启动服务、不打开窗口：

```text
start_background.vbs
```

停止后台服务：

```powershell
powershell -ExecutionPolicy Bypass -File .\stop_voice_agent.ps1
```

开机自启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_startup.ps1
```

取消开机自启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall_startup.ps1
```

## 后台 F8 语音模式

双击：

```text
start_f8_voice_agent.vbs
```

然后：

- 按 `F8` 开始录音
- 再按 `F8` 停止录音并自动发送给 Agent
- 程序会自动判断 Claude / Codex
- Agent 完成后只播报摘要
- 按 `Esc` 停止当前播报

光标听写发送：

- 把光标放到任意输入框
- 按 `F7` 开始录音，再按 `F7` 停止录音
- 有线耳机中键也会触发同样的开始/停止逻辑
- 程序会用本地模型识别，把文本写入剪贴板，再自动发送 `Shift+Insert` 和 `Enter`
- 开始/结束录音会播放项目内自动生成的叮咚提示音

看日志：

```text
data/logs/background.log
```

实时刷新日志窗口：

```text
open_live_log.vbs
```

小型悬浮日志窗：

```text
open_log_overlay.vbs
```

这个窗口支持像微信/QQ 一样隐藏到系统托盘：最小化或关闭窗口时不会退出，点托盘图标或菜单“显示日志”可以恢复。

调试启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_f8_voice_agent_debug.ps1
```

预下载/校验模型：

```powershell
python tools/download_models.py
python tools/check_model_cache.py
```

如果要把模型放在项目目录里，按 [MODELS.md](MODELS.md) 执行：

```powershell
python tools/download_project_models.py
```

快捷键：

- 按一下 `F8` 开始说话，再按一下 `F8` 停止并发送
- 按一下 `F7` 或有线耳机中键开始光标听写，再按一下停止、粘贴并回车
- 直接说 `Claude ...` 或 `Codex ...` 指定目标
- 不指定目标时发送给 `config.yaml` 里的默认 Agent
- 按 `Esc` 停止当前语音播报
- 按 `Ctrl+C` 退出程序

第一次语音识别会下载并加载 `faster-whisper` 模型，耗时会比后续更久。

## 文本调试

不录音，直接测试路由：

```powershell
python app.py --text "Claude 解释当前项目" --agent codex
python app.py --text "Codex 修复这个错误" --agent claude
python app.py --text "停止朗读"
```

如果想用旧版本地 Whisper 图形界面：

```powershell
python app.py --local-gui
```

如果想用旧版控制台热键模式：

```powershell
python app.py --console
```

## 实时听写模式

如果你需要“边说边出字”，启动 Web 版：

```powershell
python web_app.py
```

然后用 Edge 或 Chrome 打开：

```text
http://127.0.0.1:8765
```

这个模式使用浏览器实时语音识别：光标放在左侧文本框里，点“开始实时听写”，文字会实时插入。完成后点“发送给 Agent”。

## 测试

启动前可以先跑：

```powershell
python run_tests.py
```

测试会覆盖配置加载、路由、高风险确认、控制器创建和 GUI 创建。

## 配置

主要配置在 `config.yaml`：

- `input`: 快捷键
- `stt`: Whisper 模型、语言、速度/准确率参数
- `agents`: Claude/Codex CLI 命令和超时时间
- `routing`: 本地命令和显式 Agent 路由
- `safety`: 需要二次确认的高风险关键词
- `output`: TTS 语音、播报开关、按键提示音和 F7 粘贴回车延迟

F7 光标听写相关配置：

```yaml
input:
  headset_middle_key: media_play_pause

output:
  beep_enabled: true
  f7_send_delay_ms: 1000
```

如果不想语音播报，可以设置：

```yaml
output:
  tts_enabled: false
```

识别速度优先的默认配置是：

```yaml
stt:
  profile: fast
  model: base
  beam_size: 1
```

如果你更在意准确率，可以改成：

```yaml
stt:
  profile: accurate
  model: small
  beam_size: 5
```

## 数据目录

运行时会自动生成：

- `data/recordings`: 录音 wav
- `data/transcripts`: 识别文本
- `data/tts`: 播报音频
- `data/sounds`: F7 开始/结束录音的叮咚提示音

## 版本记录

### 当前版本

- 修复 FunASR 本地识别在缺少 ffmpeg 时的处理方式。
- 增加日志面板里的模型与参数配置入口。
- 增加系统托盘隐藏/恢复日志面板能力。
- 增加 F7 光标听写模式，并支持有线耳机中键触发。
- F7 识别后固定写入剪贴板，发送 `Shift+Insert` 粘贴，再发送 `Enter`。
- 修复 Windows `SendInput` 结构体大小错误导致自动粘贴/回车失败的问题。
- 将开始/结束录音提示音换成项目生成的叮咚 wav。
