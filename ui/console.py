from __future__ import annotations

from agents.base import AgentResult


class ConsoleUI:
    def show_hotkey_help(self) -> None:
        print("\n本地语音 Agent 路由器已启动")
        print("按一下 F8 开始说话，再按一下 F8 停止并发送。")
        print("可以直接说“Claude ...”或“Codex ...”指定目标；不指定时走默认 Agent。")
        print("按 Esc 停止朗读。按 Ctrl+C 退出。\n")

    def status(self, message: str) -> None:
        print(f"[状态] {message}")

    def warning(self, message: str) -> None:
        print(f"[确认] {message}")

    def error(self, message: str) -> None:
        print(f"[错误] {message}")

    def transcript(self, text: str) -> None:
        print("\n[识别文本]")
        print(text)

    def agent_start(self, target: str, prompt: str) -> None:
        print(f"\n[路由] -> {target}")
        print("[发送内容]")
        print(prompt)
        print("\n[Agent 执行中]\n")

    def agent_result(self, result: AgentResult) -> None:
        title = f"[{result.agent_name} 结果] {'成功' if result.success else '失败'}"
        print(title)
        if result.error:
            print(f"错误: {result.error}")
        if result.raw_output:
            print(result.raw_output)
        print("\n[播报摘要]")
        print(result.summary)
