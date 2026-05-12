from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from agents.base import AgentResult
from core.factory import build_session_controller


class TkUI:
    def __init__(self, app: "VoiceRouterApp"):
        self.app = app

    def show_hotkey_help(self) -> None:
        pass

    def status(self, message: str) -> None:
        self.app.post("status", message)

    def warning(self, message: str) -> None:
        self.app.post("warning", message)

    def error(self, message: str) -> None:
        self.app.post("error", message)

    def transcript(self, text: str) -> None:
        self.app.post("transcript", text)

    def agent_start(self, target: str, prompt: str) -> None:
        self.app.post("agent_start", (target, prompt))

    def agent_result(self, result: AgentResult) -> None:
        self.app.post("agent_result", result)


class VoiceRouterApp:
    def __init__(self, config: dict, project_dir: Path):
        self.config = config
        self.project_dir = project_dir
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.recording = False

        self.root = tk.Tk()
        self.root.title("语音 Agent 路由器")
        self.root.geometry("1080x760")
        self.root.minsize(900, 640)
        self.root.configure(bg="#eef1f5")

        self.target = tk.StringVar(value=config.get("agents", {}).get("default", "codex"))
        self.status_text = tk.StringVar(value="准备就绪。点开始说话，或按 F8。")
        self.record_text = tk.StringVar(value="开始说话")

        self._build_styles()
        self._wire_controller()
        self._build_layout()

        self.root.bind("<F8>", lambda event: self.toggle_recording())
        self.root.bind("<Escape>", lambda event: self.controller.stop_tts())
        self.root.after(80, self._drain_events)

    def _wire_controller(self) -> None:
        tk_ui = TkUI(self)
        self.controller = build_session_controller(self.config, self.project_dir, tk_ui)

    def _build_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Root.TFrame", background="#eef1f5")
        style.configure("Header.TFrame", background="#1f2937")
        style.configure("Panel.TFrame", background="#ffffff", relief="flat")
        style.configure("Title.TLabel", background="#1f2937", foreground="#ffffff", font=("Microsoft YaHei UI", 20, "bold"))
        style.configure("Hint.TLabel", background="#1f2937", foreground="#cbd5e1", font=("Microsoft YaHei UI", 10))
        style.configure("Footer.TLabel", background="#eef1f5", foreground="#586174", font=("Microsoft YaHei UI", 10))
        style.configure("PanelTitle.TLabel", background="#ffffff", foreground="#111827", font=("Microsoft YaHei UI", 12, "bold"))
        style.configure("Small.TLabel", background="#ffffff", foreground="#64748b", font=("Microsoft YaHei UI", 9))
        style.configure("Status.TLabel", background="#ffffff", foreground="#1f2937", padding=(14, 10), font=("Microsoft YaHei UI", 10))
        style.configure("Target.TRadiobutton", background="#ffffff", foreground="#111827", font=("Microsoft YaHei UI", 10))
        style.configure("Accent.TButton", font=("Microsoft YaHei UI", 17, "bold"), padding=(28, 16), background="#2563eb", foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#1d4ed8"), ("pressed", "#1e40af")], foreground=[("disabled", "#e5e7eb")])
        style.configure("Danger.TButton", font=("Microsoft YaHei UI", 17, "bold"), padding=(28, 16), background="#dc2626", foreground="#ffffff")
        style.map("Danger.TButton", background=[("active", "#b91c1c"), ("pressed", "#991b1b")])
        style.configure("Tool.TButton", font=("Microsoft YaHei UI", 10), padding=(14, 9), background="#e5e7eb", foreground="#111827")
        style.map("Tool.TButton", background=[("active", "#d1d5db"), ("pressed", "#cbd5e1")])

    def _build_layout(self) -> None:
        root = ttk.Frame(self.root, style="Root.TFrame")
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        header = ttk.Frame(root, style="Header.TFrame", padding=(22, 18))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="语音 Agent 路由器", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="一次点击录音，再次点击发送。识别文本、路由目标和 Agent 输出都会留在窗口里。", style="Hint.TLabel").grid(row=1, column=0, sticky="w", pady=(6, 0))

        controls = ttk.Frame(root, style="Panel.TFrame", padding=18)
        controls.grid(row=1, column=0, sticky="ew", padx=18, pady=(18, 14))
        controls.columnconfigure(2, weight=1)

        self.record_button = ttk.Button(controls, textvariable=self.record_text, style="Accent.TButton", command=self.toggle_recording)
        self.record_button.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(0, 18))

        target_box = ttk.Frame(controls, style="Panel.TFrame", padding=(2, 0))
        target_box.grid(row=0, column=1, rowspan=2, sticky="w", padx=(0, 18))
        ttk.Label(target_box, text="默认目标", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Radiobutton(target_box, text="Codex", value="codex", variable=self.target, style="Target.TRadiobutton").pack(anchor="w", pady=(8, 2))
        ttk.Radiobutton(target_box, text="Claude", value="claude", variable=self.target, style="Target.TRadiobutton").pack(anchor="w")

        status_box = ttk.Frame(controls, style="Panel.TFrame")
        status_box.grid(row=0, column=2, rowspan=2, sticky="ew", padx=(0, 10))
        status_box.columnconfigure(0, weight=1)
        ttk.Label(status_box, text="当前状态", style="Small.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(status_box, textvariable=self.status_text, style="Status.TLabel").grid(row=1, column=0, sticky="ew", pady=(6, 0))

        ttk.Button(controls, text="停止朗读", style="Tool.TButton", command=self.controller.stop_tts).grid(row=0, column=3, sticky="e", padx=(8, 0))
        ttk.Button(controls, text="清空显示", style="Tool.TButton", command=self.clear_text).grid(row=1, column=3, sticky="e", padx=(8, 0), pady=(8, 0))

        body = ttk.Frame(root, style="Root.TFrame", padding=(18, 0, 18, 0))
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        self.transcript = self._make_text_panel(body, "识别文本", 0, 0)
        self.output = self._make_text_panel(body, "Agent 输出", 0, 1)

        footer = ttk.Label(root, text="快捷键：F8 开始/停止录音，Esc 停止朗读。说“Claude ...”或“Codex ...”可以临时覆盖默认目标。", style="Footer.TLabel")
        footer.grid(row=3, column=0, sticky="w", padx=18, pady=(12, 14))

    def _make_text_panel(self, parent, title: str, row: int, column: int) -> tk.Text:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=10)
        panel.grid(row=row, column=column, sticky="nsew", padx=(0, 8) if column == 0 else (8, 0))
        panel.rowconfigure(1, weight=1)
        panel.columnconfigure(0, weight=1)
        ttk.Label(panel, text=title, style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        text = tk.Text(
            panel,
            wrap="word",
            relief="flat",
            bg="#f8fafc",
            fg="#0f172a",
            insertbackground="#171b24",
            font=("Microsoft YaHei UI", 12),
            padx=14,
            pady=14,
        )
        text.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(panel, orient="vertical", command=text.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        text.configure(yscrollcommand=scroll.set)
        return text

    def run(self) -> None:
        self.root.mainloop()

    def post(self, kind: str, payload: object) -> None:
        self.events.put((kind, payload))

    def toggle_recording(self) -> None:
        if self.recording:
            self.recording = False
            self.record_text.set("开始说话")
            self.record_button.configure(style="Accent.TButton")
            self.status_text.set("录音结束，正在识别...")
            agent = self.target.get()
            threading.Thread(target=self.controller.stop_recording_and_handle, args=(agent,), daemon=True).start()
            return

        self.recording = True
        self.record_text.set("停止并发送")
        self.record_button.configure(style="Danger.TButton")
        self.status_text.set(f"正在录音，默认发送给 {self.target.get()}。")
        self._set_text(self.transcript, "")
        threading.Thread(target=self.controller.start_recording, args=(self.target.get(),), daemon=True).start()

    def clear_text(self) -> None:
        self._set_text(self.transcript, "")
        self._set_text(self.output, "")
        self.status_text.set("已清空显示。")

    def _drain_events(self) -> None:
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            self._handle_event(kind, payload)
        self.root.after(80, self._drain_events)

    def _handle_event(self, kind: str, payload: object) -> None:
        if kind in {"status", "warning", "error"}:
            self.status_text.set(str(payload))
        elif kind == "transcript":
            self._set_text(self.transcript, str(payload))
        elif kind == "agent_start":
            target, prompt = payload
            self.status_text.set(f"已路由给 {target}，正在执行...")
            self._append_text(self.output, f"[路由] {target}\n\n[发送内容]\n{prompt}\n\n[执行中]\n")
        elif kind == "agent_result":
            result = payload
            if isinstance(result, AgentResult):
                state = "成功" if result.success else "失败"
                text = f"\n[{result.agent_name} 结果] {state}\n"
                if result.error:
                    text += f"错误: {result.error}\n"
                if result.raw_output:
                    text += f"{result.raw_output}\n"
                text += f"\n[播报摘要]\n{result.summary}\n"
                self._append_text(self.output, text)
                self.status_text.set(result.summary)

    def _set_text(self, widget: tk.Text, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="normal")

    def _append_text(self, widget: tk.Text, value: str) -> None:
        widget.configure(state="normal")
        widget.insert("end", value)
        widget.see("end")
        widget.configure(state="normal")
