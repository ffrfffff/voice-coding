# 本地语音 Agent 路由器

这是一个 Windows 本地语音入口。它支持通过 F8 把录音内容路由给 Claude Code 或 Codex CLI，也支持通过 F7 把语音识别结果粘贴到当前光标位置并自动回车发送。项目还提供浏览器实时听写界面、桌面 WebView 包装、后台热键服务和悬浮日志面板。

## 快速启动

安装依赖：

```powershell
pip install -r requirements.txt
```

启动默认 Web 实时听写界面：

```powershell
python app.py
```

默认地址：

```text
http://127.0.0.1:8765
```

运行测试：

```powershell
python run_tests.py
```

## 常用入口

桌面 App：

```text
start_app.vbs
```

后台 F8/F7 语音助手：

```text
start_f8_voice_agent.vbs
```

后台 Web 服务，不打开窗口：

```text
start_background.vbs
```

停止后台服务：

```powershell
powershell -ExecutionPolicy Bypass -File .\stop_voice_agent.ps1
```

调试启动后台语音助手：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_f8_voice_agent_debug.ps1
```

## 快捷键

- `F8`：开始录音；再次按下后停止录音，并把识别文本路由给 Agent。
- `F7`：开始光标听写；再次按下后停止录音，把识别文本粘贴到当前输入框并发送 `Enter`。
- 有线耳机中键：触发与 `F7` 相同的光标听写流程。
- `Esc`：停止当前 TTS 播报。
- `Ctrl+C`：退出控制台模式。

直接说或输入 `Claude ...` / `Codex ...` 可以指定目标 Agent；不指定时使用 `config.yaml` 里的默认 Agent。

## 项目结构

根目录保留用户常用入口、Windows 启动脚本、配置和文档；核心构造逻辑下沉到 `core/`，避免多个入口重复组装同一套组件。

```text
.
├── app.py                         # 主入口；默认启动 Web 实时听写，也支持 --text、--local-gui、--console
├── desktop_app.py                 # pywebview 桌面壳，供 start_app.vbs / start_background.vbs 调用
├── background_voice_agent.py      # 后台 F8 Agent 模式和 F7 光标听写模式
├── web_app.py                     # 本地 HTTP 服务、Web API、Agent 后台任务
├── log_overlay.py                 # 悬浮日志窗口和托盘入口
├── config.yaml                    # 快捷键、STT、Agent、路由、安全和输出配置
├── requirements.txt               # Python 依赖
├── MODELS.md                      # 本地模型下载和缓存说明
├── agents/                        # Claude/Codex CLI 适配层
├── core/                          # 核心逻辑和公共装配
│   ├── factory.py                 # 统一创建 Agent/STT/TTS/Router/SessionController
│   ├── web_service.py             # 端口探测和后台 HTTP 服务线程
│   ├── router.py                  # 路由判断
│   ├── risk_checker.py            # 高风险操作二次确认
│   ├── session.py                 # 录音到 Agent 的会话流程
│   ├── recorder.py                # 录音保存
│   ├── summarizer.py              # Agent 输出摘要
│   └── sendkeys.py                # Windows 按键发送
├── providers/                     # STT/TTS provider：FunASR、faster-whisper、Edge TTS
├── ui/                            # 控制台 UI 和 Tk GUI
├── web/                           # 浏览器实时听写前端
├── tools/                         # 模型下载、缓存检查、F7/FunASR 手工测试工具
├── tests/                         # 单元测试
├── models/                        # 本地模型缓存
└── data/                          # 运行时数据，自动生成，不纳入版本管理
```

## 核心流程

F8 Agent 模式：

```text
录音 -> STT 识别 -> Router 判断 Claude/Codex/本地命令 -> RiskChecker 高风险确认 -> Agent CLI -> 摘要 -> TTS 播报
```

F7 光标听写模式：

```text
录音 -> STT 识别 -> 写入剪贴板并校验 -> 等待 -> 粘贴前再次校验剪贴板 -> Shift+Insert 粘贴 -> Enter 发送
```

如果粘贴前发现剪贴板内容不是本次语音识别文本，程序会重新写入并再次校验；仍然失败时会中止本次粘贴和回车，避免把旧剪贴板内容发出去。

Web 实时听写模式：

```text
浏览器 SpeechRecognition -> /api/run -> WebAppState 后台任务 -> Agent CLI -> 页面轮询任务结果
```

## 配置

主要配置在 `config.yaml`：

- `input`：F7/F8、耳机中键、停止播报等输入配置。
- `stt`：语音识别 provider、模型、缓存目录、超时、热词和 fallback。
- `agents`：Claude/Codex CLI 命令、参数、工作目录和超时时间。
- `routing`：显式 Agent 路由、本地命令、自动路由。
- `safety`：删除、提交、推送等高风险关键词的二次确认。
- `output`：TTS、提示音、F7 粘贴前等待、F7 发送延迟、播报摘要长度。

关闭语音播报：

```yaml
output:
  tts_enabled: false
```

调整 F7 粘贴节奏：

```yaml
output:
  f7_paste_delay_ms: 800
  f7_send_delay_ms: 1000
```

`f7_paste_delay_ms` 是写入剪贴板后、发送 `Shift+Insert` 前的等待时间；`f7_send_delay_ms` 是发送 `Shift+Insert` 后、发送 `Enter` 前的等待时间。

## 模型

检查模型缓存：

```powershell
python tools/check_model_cache.py
```

下载模型到项目目录：

```powershell
python tools/download_project_models.py
```

更多说明见 [MODELS.md](MODELS.md)。

## 日志与运行数据

运行时会自动生成这些目录：

- `data/logs`：后台服务、调试和启动日志。
- `data/recordings`：录音 wav。
- `data/transcripts`：识别文本。
- `data/tts`：TTS 播报音频。
- `data/sounds`：F7/F8 开始和结束录音提示音。

打开实时日志窗口：

```text
open_live_log.vbs
```

打开悬浮日志面板：

```text
open_log_overlay.vbs
```

## 文本调试

不录音，直接测试路由：

```powershell
python app.py --text "Claude 解释当前项目" --agent codex
python app.py --text "Codex 修复这个错误" --agent claude
python app.py --text "停止朗读"
```

旧版本地 GUI：

```powershell
python app.py --local-gui
```

旧版控制台热键模式：

```powershell
python app.py --console
```

## 开机自启动

安装：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_startup.ps1
```

卸载：

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall_startup.ps1
```

## 清理说明

`__pycache__`、`*.pyc`、`data/recordings`、`data/transcripts`、`data/tts`、`data/logs`、`data/sounds`、`.DS_Store` 和下载中断产生的 `*.incomplete` 都是可再生成文件，已在 `.gitignore` 中忽略。
