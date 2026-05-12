from __future__ import annotations

from pathlib import Path


class SessionController:
    def __init__(self, ui, recorder, stt, router, risk_checker, summarizer, tts, agents: dict):
        self.ui = ui
        self.recorder = recorder
        self.stt = stt
        self.router = router
        self.risk_checker = risk_checker
        self.summarizer = summarizer
        self.tts = tts
        self.agents = agents

    def start_recording(self, fallback_agent: str) -> None:
        self.ui.status(f"开始录音，松开快捷键后发送给 {fallback_agent}。")
        self.recorder.start()

    def stop_recording_and_handle(self, fallback_agent: str) -> None:
        self.ui.status("录音结束，正在识别...")
        wav_path = self.recorder.stop_and_save()
        if wav_path is None:
            self.ui.error("没有录到有效音频。")
            return

        text = self.stt.transcribe(wav_path)
        self.handle_text(text, fallback_agent)

    def handle_text(self, text: str, fallback_agent: str) -> None:
        text = (text or "").strip()
        if not text:
            self.ui.error("没有识别到文本。")
            return

        self.ui.transcript(text)

        confirmation_state, pending = self.risk_checker.consume_confirmation(text)
        if confirmation_state == "confirmed" and pending:
            self._run_agent(pending["target"], pending["prompt"])
            return
        if confirmation_state == "rejected":
            self.ui.status("已取消待确认任务。")
            self.tts.speak("已取消。")
            return
        if confirmation_state == "waiting":
            self.ui.status("仍在等待确认。请说“确认”继续，或说“取消”放弃。")
            return

        decision = self.router.route(text, fallback_agent)
        if decision.kind == "local":
            self._handle_local_command(decision.target)
            return

        if self.risk_checker.needs_confirmation(decision.prompt):
            self.risk_checker.hold(decision.target, decision.prompt)
            message = f"识别到高风险操作，目标是 {decision.target}。请再次说“确认”继续，或说“取消”放弃。"
            self.ui.warning(message)
            self.tts.speak(message)
            return

        self._run_agent(decision.target, decision.prompt)

    def stop_tts(self) -> None:
        self.tts.stop()
        self.ui.status("已停止朗读。")

    def _handle_local_command(self, command: str | None) -> None:
        if command == "stop":
            self.stop_tts()
        elif command == "cancel":
            self.risk_checker.pending = None
            self.ui.status("已取消。")
        elif command == "retry":
            self.ui.status("请重新按住快捷键录音。")
        else:
            self.ui.status(f"本地命令已处理: {command}")

    def _run_agent(self, target: str, prompt: str) -> None:
        agent = self.agents.get(target)
        if not agent:
            self.ui.error(f"未知 Agent: {target}")
            return

        self.ui.agent_start(target, prompt)
        result = agent.run(prompt, context={})
        result.summary = self.summarizer.summarize(result)
        self.ui.agent_result(result)
        self.tts.speak(result.summary)
