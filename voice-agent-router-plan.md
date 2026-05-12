# 本地语音多 Agent 编程交互方案

## 1. 方案定位

本方案目标是构建一个运行在 Windows 本地的语音编程交互工具，用于通过语音与 Claude、Codex 等编程 Agent 交互。

它不是一个始终监听的语音助手，也不是一个全文朗读的聊天机器人，而是一个按键触发的本地语音 Agent 路由器。

核心定位：

```text
按键触发语音输入
→ 语音识别成文本
→ 选择或判断目标 Agent
→ 调用 Claude / Codex / 本地控制命令
→ 屏幕显示完整结果
→ 只语音播报摘要、状态和关键结论
```

## 2. 核心原则

### 2.1 不始终监听

系统默认不常开麦克风，不做后台持续监听，不做唤醒词。

推荐采用 Push-to-Talk 模式：

```text
按住快捷键开始录音
松开快捷键停止录音
停止后进行语音识别和任务分发
```

这样可以避免：

- 环境噪音误触发
- 隐私风险
- 长时间占用麦克风
- 播放声音被再次录入
- 唤醒词误识别
- 复杂的实时音频状态管理

### 2.2 不全文朗读

Claude 和 Codex 的输出可能包含代码、diff、日志、错误堆栈、测试输出等内容，不适合完整朗读。

输出策略：

```text
完整结果：显示在终端、窗口或日志中
语音输出：只播报摘要、状态和关键结论
```

默认不朗读：

- 代码块
- diff
- 长日志
- 错误堆栈
- 命令完整输出
- 文件路径列表

默认朗读：

- 是否完成
- 修改了什么
- 是否有错误
- 是否需要用户确认
- 下一步建议

### 2.3 支持 Claude 和 Codex

系统不绑定单一 Agent，而是提供统一语音入口，再路由到不同后端。

第一版至少支持：

```text
Claude Code
Codex CLI / Codex API
本地控制命令
```

后续可扩展：

```text
Gemini CLI
本地 LLM
自定义脚本
项目专用 Agent
```

## 3. 总体架构

```text
┌────────────────────────────┐
│        用户快捷键输入        │
│  Ctrl+Alt+Space / C / X     │
└──────────────┬─────────────┘
               ↓
┌────────────────────────────┐
│          录音模块            │
│    开始录音 / 停止录音        │
└──────────────┬─────────────┘
               ↓
┌────────────────────────────┐
│        语音识别模块          │
│     faster-whisper / STT    │
└──────────────┬─────────────┘
               ↓
┌────────────────────────────┐
│      指令解析与路由模块       │
│  本地命令 / Claude / Codex   │
└───────┬──────────┬─────────┘
        ↓          ↓
┌────────────┐ ┌────────────┐
│ Claude     │ │ Codex      │
│ Agent      │ │ Agent      │
└─────┬──────┘ └─────┬──────┘
      ↓              ↓
┌────────────────────────────┐
│       结果收集与摘要模块      │
│  过滤代码 / 日志 / diff       │
└──────────────┬─────────────┘
               ↓
┌────────────────────────────┐
│        输出模块              │
│  完整显示 + 摘要语音播报      │
└────────────────────────────┘
```

## 4. 用户交互设计

### 4.1 快捷键设计

推荐快捷键：

| 快捷键 | 行为 |
|---|---|
| Ctrl + Alt + Space | 默认语音输入，进入手动选择或自动路由 |
| Ctrl + Alt + C | 语音输入后发送给 Claude |
| Ctrl + Alt + X | 语音输入后发送给 Codex |
| Esc | 停止当前语音播报 |
| Ctrl + Alt + R | 重新录音 |

第一版建议优先实现：

```text
Ctrl + Alt + C → Claude
Ctrl + Alt + X → Codex
Esc → 停止播报
```

这样可以避免自动路由误判。

### 4.2 显式语音路由

用户可以直接指定目标 Agent：

```text
“Claude，解释当前文件”
“Codex，修复这个报错”
“让 Claude 总结 Codex 的输出”
“让 Codex 根据 Claude 的方案实现”
```

路由规则：

```text
以 Claude / 克劳德 开头 → Claude
以 Codex / code x / 代码助手 开头 → Codex
包含“让 Claude” → Claude
包含“让 Codex” → Codex
没有明确目标 → 使用当前快捷键指定的目标
```

### 4.3 本地控制命令

以下命令不发送给 Claude 或 Codex，而是在本地处理：

```text
停止
停止朗读
取消
重新录音
重来
确认
不确认
放弃
```

示例：

```text
用户：停止朗读
系统：立即停止 TTS，不调用 Agent
```

### 4.4 高风险操作确认

语音识别可能出错，因此高风险操作必须二次确认。

高风险关键词：

```text
删除
覆盖
提交
推送
安装
卸载
重置
迁移
清空
格式化
发布
部署
```

流程：

```text
用户语音：提交这些修改
系统识别：提交这些修改
系统判断：高风险操作
系统提示：识别到提交代码操作，是否确认？
用户语音：确认
系统执行：发送给目标 Agent 或执行本地流程
```

未确认前不执行高风险命令。

## 5. Agent 路由策略

### 5.1 MVP 路由策略

第一版不做复杂自动判断，采用两种稳定方式：

```text
方式一：快捷键指定 Agent
方式二：语音中显式指定 Agent
```

优先级：

```text
本地控制命令 > 显式 Agent 名称 > 快捷键指定 Agent > 默认 Agent
```

### 5.2 后续自动路由策略

后续可以加入轻量规则：

| 任务类型 | 默认目标 |
|---|---|
| 解释、总结、方案、评审 | Claude |
| 修复、生成代码、执行改动 | Codex 或 Claude |
| 对比、复核、安全性分析 | Claude |
| 批量机械修改 | Codex |
| 停止、取消、确认、重录 | 本地控制 |

自动路由只作为辅助，不应覆盖用户明确指定的 Agent。

## 6. 多 Agent 协作模式

### 6.1 单 Agent 模式

最基础模式：一次语音输入发送给一个 Agent。

示例：

```text
“Claude，解释当前项目结构”
“Codex，修复这个测试失败”
```

### 6.2 方案 + 实现模式

适合复杂任务：

```text
Claude 先给方案
用户确认
Codex 执行实现
Claude 复查结果
```

流程：

```text
语音输入：让 Claude 先设计方案，然后 Codex 实现
→ Claude 输出方案
→ 系统播报方案摘要
→ 用户确认
→ Codex 执行
→ 系统播报执行结果摘要
```

### 6.3 实现 + 复核模式

适合代码修改：

```text
Codex 修改代码
Claude 阅读 diff 进行复核
```

示例：

```text
“让 Codex 修复这个问题，然后让 Claude 复查”
```

### 6.4 双 Agent 对比模式

适合不确定方案：

```text
同一问题发给 Claude 和 Codex
收集两边结果
生成对比摘要
用户选择后执行
```

第一版不建议实现该模式，可作为第二阶段能力。

## 7. 输出与播报策略

### 7.1 完整显示

所有 Agent 的原始输出都应完整显示，便于用户检查。

显示内容包括：

```text
识别到的语音文本
目标 Agent
执行状态
Agent 完整输出
错误信息
日志路径
```

### 7.2 摘要播报

TTS 只播报摘要。

摘要模板：

```text
已发送给 {Agent}。
{任务状态}。
{关键结论}。
{是否需要你确认下一步}。
```

示例：

```text
“Codex 已完成修改，主要调整了录音快捷键逻辑。建议检查 diff 后运行测试。”
```

```text
“Claude 已完成分析，结论是当前方案可行，但需要先确认 Codex 的调用方式。”
```

### 7.3 摘要生成规则

优先从 Agent 输出中提取：

```text
完成状态
修改文件数量
测试是否通过
错误原因
下一步动作
```

过滤内容：

```text
代码块
Markdown 表格
diff
堆栈跟踪
长路径列表
命令原始输出
```

## 8. 技术选型

### 8.1 推荐 MVP 技术栈

```text
Python
sounddevice
pynput
faster-whisper
edge-tts
Claude Code CLI
Codex CLI / API
YAML 配置
```

### 8.2 模块选型说明

| 模块 | 推荐 | 说明 |
|---|---|---|
| 录音 | sounddevice | Windows 兼容性较好 |
| 快捷键 | pynput | 支持全局快捷键和按住触发 |
| STT | faster-whisper | 本地中文识别效果好 |
| Claude | Claude Code CLI | 适合本地项目编程任务 |
| Codex | Codex CLI / API | 作为第二编程 Agent |
| TTS | edge-tts | 中文声音自然，接入简单 |
| 配置 | YAML | 可读性好，便于修改 |

## 9. 推荐目录结构

```text
voice-agent-router/
  app.py
  config.yaml
  requirements.txt

  core/
    recorder.py
    hotkeys.py
    router.py
    risk_checker.py
    summarizer.py
    session.py

  agents/
    base.py
    claude_agent.py
    codex_agent.py

  providers/
    stt_whisper.py
    tts_edge.py

  ui/
    console.py

  data/
    recordings/
    transcripts/
    logs/
```

## 10. 模块职责

### 10.1 app.py

主入口，负责串联整体流程：

```text
初始化配置
注册快捷键
启动录音
调用 STT
调用路由器
执行 Agent
显示结果
播报摘要
```

### 10.2 core/recorder.py

负责录音：

```text
开始录音
停止录音
保存 wav
过滤空白音频
处理录音异常
```

### 10.3 core/hotkeys.py

负责快捷键：

```text
绑定 Push-to-Talk
识别目标 Agent 快捷键
绑定停止朗读
绑定重新录音
```

### 10.4 core/router.py

负责路由：

```text
识别本地控制命令
识别显式 Agent 名称
根据快捷键确定目标 Agent
处理默认 Agent
```

### 10.5 core/risk_checker.py

负责高风险判断：

```text
扫描高风险关键词
标记待确认任务
确认后继续执行
取消后丢弃任务
```

### 10.6 core/summarizer.py

负责摘要生成：

```text
过滤代码块
过滤 diff
过滤日志
提取结论
生成 TTS 文本
```

### 10.7 agents/base.py

定义统一 Agent 接口：

```text
run(prompt, context) -> AgentResult
```

AgentResult 包含：

```text
agent_name
success
raw_output
summary
error
metadata
```

### 10.8 agents/claude_agent.py

封装 Claude 调用：

```text
调用 Claude Code CLI
传入当前工作目录
收集输出
返回 AgentResult
```

### 10.9 agents/codex_agent.py

封装 Codex 调用：

```text
调用 Codex CLI 或 API
传入 prompt
收集输出
返回 AgentResult
```

### 10.10 providers/stt_whisper.py

负责语音识别：

```text
加载 faster-whisper 模型
识别中文语音
返回文本和置信度
过滤空识别结果
```

### 10.11 providers/tts_edge.py

负责语音播报：

```text
调用 edge-tts
播放摘要音频
支持停止播放
跳过空摘要
```

### 10.12 ui/console.py

负责命令行显示：

```text
显示识别文本
显示目标 Agent
显示完整输出
显示风险确认提示
显示错误信息
```

## 11. 配置文件示例

```yaml
input:
  mode: push_to_talk
  default_hotkey: ctrl+alt+space
  claude_hotkey: ctrl+alt+c
  codex_hotkey: ctrl+alt+x
  stop_tts_hotkey: esc
  retry_hotkey: ctrl+alt+r

stt:
  provider: faster_whisper
  language: zh
  model: small
  device: auto
  compute_type: int8

agents:
  default: manual
  claude:
    enabled: true
    type: cli
    command: claude
    working_directory: current
  codex:
    enabled: true
    type: cli
    command: codex
    working_directory: current

routing:
  prefer_explicit_agent_name: true
  allow_auto_route: false
  local_commands:
    stop:
      - 停止
      - 停止朗读
      - 别读了
    retry:
      - 重新录音
      - 重来
    cancel:
      - 取消
      - 放弃
    confirm:
      - 确认
      - 继续
    reject:
      - 不确认
      - 不要

output:
  display_full_text: true
  tts_mode: summary_only
  max_spoken_sentences: 3
  skip_code_blocks: true
  skip_diff: true
  skip_logs: true

safety:
  require_confirmation: true
  confirm_keywords:
    - 删除
    - 覆盖
    - 提交
    - 推送
    - 安装
    - 卸载
    - 重置
    - 迁移
    - 清空
    - 格式化
    - 发布
    - 部署
```

## 12. MVP 开发阶段

### 阶段 1：打通语音输入

目标：

```text
按住快捷键说话，松开后识别成中文文本。
```

实现内容：

```text
录音模块
快捷键模块
Whisper STT 模块
控制台显示识别结果
```

验收标准：

```text
按 Ctrl+Alt+C 说“Claude 解释当前文件”，控制台能显示正确文本。
按 Ctrl+Alt+X 说“Codex 修复这个错误”，控制台能显示正确文本。
```

### 阶段 2：打通 Claude / Codex 调用

目标：

```text
识别后的文本可以发送给指定 Agent。
```

实现内容：

```text
Claude Agent 封装
Codex Agent 封装
路由模块
完整输出显示
```

验收标准：

```text
Ctrl+Alt+C 的语音输入发送给 Claude。
Ctrl+Alt+X 的语音输入发送给 Codex。
显式说“Claude ...”时发送给 Claude。
显式说“Codex ...”时发送给 Codex。
```

### 阶段 3：加入摘要播报

目标：

```text
Agent 完整输出显示在屏幕上，语音只播报摘要。
```

实现内容：

```text
摘要模块
TTS 模块
停止播报快捷键
代码块 / diff / 日志过滤
```

验收标准：

```text
长输出不会被全文朗读。
代码块不会被朗读。
Esc 可以停止播报。
```

### 阶段 4：加入风险确认

目标：

```text
高风险语音命令不会直接执行。
```

实现内容：

```text
风险关键词识别
待确认任务缓存
确认 / 取消指令处理
```

验收标准：

```text
说“提交代码”时，系统先提示确认。
说“确认”后才继续执行。
说“取消”后丢弃任务。
```

### 阶段 5：加入多 Agent 协作

目标：

```text
支持 Claude 规划、Codex 实现、Claude 复核等组合流程。
```

实现内容：

```text
任务链编排
AgentResult 标准化
上下文传递
复核模式
```

验收标准：

```text
可以执行“Claude 先给方案，确认后 Codex 实现”的流程。
可以执行“Codex 修改后 Claude 复查”的流程。
```

## 13. 风险与应对

### 13.1 语音识别错误

风险：

```text
识别错误导致发送错误指令。
```

应对：

```text
显示识别文本
高风险操作二次确认
支持重新录音
第一版避免自动执行危险动作
```

### 13.2 Agent 输出过长

风险：

```text
全文朗读影响体验。
```

应对：

```text
完整输出只显示
TTS 只读摘要
过滤代码、diff、日志
限制播报句数
```

### 13.3 路由错误

风险：

```text
本该发给 Claude 的任务发给 Codex，或反之。
```

应对：

```text
MVP 使用快捷键和显式 Agent 名称
自动路由默认关闭
显示目标 Agent 后再执行高风险任务
```

### 13.4 CLI 调用不稳定

风险：

```text
Claude 或 Codex CLI 输出格式变化，进程阻塞或失败。
```

应对：

```text
统一 AgentResult
设置超时
捕获 stderr
记录日志
错误时只播报简短失败原因
```

### 13.5 隐私与权限

风险：

```text
语音输入可能包含敏感信息。
```

应对：

```text
不始终监听
录音只在按键期间进行
本地保存录音可配置关闭
敏感操作二次确认
```

## 14. 第一版验收清单

第一版完成时，应满足：

```text
[ ] 不会始终监听麦克风
[ ] 只在按键期间录音
[ ] 能识别中文语音
[ ] 能通过快捷键选择 Claude 或 Codex
[ ] 能通过语音显式指定 Claude 或 Codex
[ ] 能显示完整 Agent 输出
[ ] 不全文朗读 Agent 输出
[ ] 只播报摘要和状态
[ ] Esc 能停止播报
[ ] 高风险操作会二次确认
[ ] 本地控制命令不会发给 Agent
[ ] 关键日志可追踪
```

## 15. 推荐实施顺序

建议先做最小闭环：

```text
Push-to-Talk
→ STT
→ 快捷键选择 Claude / Codex
→ CLI 调用
→ 完整输出显示
→ 摘要 TTS
```

不要一开始做：

```text
始终监听
唤醒词
实时语音流
复杂 GUI
自动复杂路由
全文朗读
```

## 16. 最终目标

最终系统应成为一个轻量、可控、可扩展的本地语音编程入口：

```text
用户按键说话
→ 系统识别意图
→ 路由给 Claude 或 Codex
→ Agent 完成分析、编码或复核
→ 屏幕显示完整过程
→ 语音只播报关键摘要
→ 危险操作必须确认
```

一句话总结：

```text
这是一个不常开监听、不全文朗读、支持 Claude 与 Codex 的本地语音多 Agent 编程控制器。
```
