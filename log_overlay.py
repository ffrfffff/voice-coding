from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw
import pystray
import yaml


FUNASR_MODELS = ("paraformer-zh",)
WHISPER_MODELS = ("base", "small", "medium", "large-v3")
VAD_MODELS = ("fsmn-vad",)
PUNC_MODELS = ("ct-punc-c",)
DEVICES = ("cpu", "auto", "cuda")


class LogOverlay:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.log_path = project_dir / "data" / "logs" / "background.log"
        self.config_path = project_dir / "config.yaml"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.write_text("", encoding="utf-8")

        self.config = self._load_config()
        self.root = tk.Tk()
        self.root.title("语音 Agent 控制台")
        self.root.geometry("440x640+40+90")
        self.root.minsize(380, 500)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#f3f4f6")
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.root.bind("<Unmap>", self._on_unmap)

        self._last_content = ""
        self.tray_icon: pystray.Icon | None = None
        self._make_vars()
        self._build_ui()
        self._load_vars_from_config()
        self._start_tray()
        self._refresh()

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            return {}
        with self.config_path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}

    def _make_vars(self) -> None:
        self.provider_var = tk.StringVar()
        self.model_var = tk.StringVar()
        self.device_var = tk.StringVar()
        self.batch_size_var = tk.IntVar()
        self.timeout_var = tk.IntVar()
        self.fallback_model_var = tk.StringVar()
        self.fallback_beam_var = tk.IntVar()
        self.hotwords_var = tk.StringVar()
        self.tts_enabled_var = tk.BooleanVar()
        self.beep_enabled_var = tk.BooleanVar()
        self.restart_status_var = tk.StringVar(value="配置保存后，重启后台才会生效。")

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Header.TFrame", background="#1f2937")
        style.configure("Title.TLabel", background="#1f2937", foreground="#ffffff", font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("Hint.TLabel", background="#1f2937", foreground="#cbd5e1", font=("Microsoft YaHei UI", 9))
        style.configure("Tool.TButton", font=("Microsoft YaHei UI", 9), padding=(8, 4))
        style.configure("Muted.TLabel", background="#f3f4f6", foreground="#6b7280", font=("Microsoft YaHei UI", 9))

        header = ttk.Frame(self.root, style="Header.TFrame", padding=(10, 8))
        header.pack(fill="x")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="语音 Agent", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="F8 发给 Agent，F7 光标输入", style="Hint.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Button(header, text="隐藏", style="Tool.TButton", command=self.hide).grid(row=0, column=1, rowspan=2, sticky="e")

        settings = ttk.LabelFrame(self.root, text="模型与参数", padding=(10, 8))
        settings.pack(fill="x", padx=8, pady=(8, 4))
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="识别引擎").grid(row=0, column=0, sticky="w", pady=3)
        provider = ttk.Combobox(settings, textvariable=self.provider_var, values=("funasr", "faster_whisper"), state="readonly")
        provider.grid(row=0, column=1, sticky="ew", pady=3)
        provider.bind("<<ComboboxSelected>>", lambda _event: self._sync_model_choices())

        ttk.Label(settings, text="主模型").grid(row=1, column=0, sticky="w", pady=3)
        self.model_combo = ttk.Combobox(settings, textvariable=self.model_var)
        self.model_combo.grid(row=1, column=1, sticky="ew", pady=3)

        ttk.Label(settings, text="设备").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Combobox(settings, textvariable=self.device_var, values=DEVICES).grid(row=2, column=1, sticky="ew", pady=3)

        ttk.Label(settings, text="FunASR 批大小").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Spinbox(settings, textvariable=self.batch_size_var, from_=5, to=300, increment=5).grid(row=3, column=1, sticky="ew", pady=3)

        ttk.Label(settings, text="加载超时秒").grid(row=4, column=0, sticky="w", pady=3)
        ttk.Spinbox(settings, textvariable=self.timeout_var, from_=10, to=600, increment=10).grid(row=4, column=1, sticky="ew", pady=3)

        ttk.Label(settings, text="回退 Whisper").grid(row=5, column=0, sticky="w", pady=3)
        ttk.Combobox(settings, textvariable=self.fallback_model_var, values=WHISPER_MODELS).grid(row=5, column=1, sticky="ew", pady=3)

        ttk.Label(settings, text="回退 beam").grid(row=6, column=0, sticky="w", pady=3)
        ttk.Spinbox(settings, textvariable=self.fallback_beam_var, from_=1, to=8, increment=1).grid(row=6, column=1, sticky="ew", pady=3)

        ttk.Label(settings, text="热词").grid(row=7, column=0, sticky="w", pady=3)
        ttk.Entry(settings, textvariable=self.hotwords_var).grid(row=7, column=1, sticky="ew", pady=3)

        toggles = ttk.Frame(settings)
        toggles.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(5, 2))
        ttk.Checkbutton(toggles, text="语音播报", variable=self.tts_enabled_var).pack(side="left")
        ttk.Checkbutton(toggles, text="按键提示音", variable=self.beep_enabled_var).pack(side="left", padx=(12, 0))

        ttk.Label(settings, text="F7 固定使用 Shift+Insert 粘贴，再 Enter。", style="Muted.TLabel").grid(
            row=9, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )

        actions = ttk.Frame(settings)
        actions.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        actions.columnconfigure(1, weight=1)
        ttk.Button(actions, text="保存", command=self.save_config).grid(row=0, column=0, sticky="w")
        ttk.Button(actions, text="保存并重启后台", command=self.save_and_restart).grid(row=0, column=1, sticky="e")

        ttk.Label(settings, textvariable=self.restart_status_var, style="Muted.TLabel").grid(row=11, column=0, columnspan=2, sticky="w", pady=(6, 0))

        log_frame = ttk.LabelFrame(self.root, text="实时日志", padding=(8, 8))
        log_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        toolbar = ttk.Frame(log_frame)
        toolbar.pack(fill="x", pady=(0, 6))
        ttk.Button(toolbar, text="清空日志", style="Tool.TButton", command=self._clear).pack(side="right")

        self.text = tk.Text(log_frame, wrap="word", bg="#ffffff", fg="#111827", relief="flat", padx=10, pady=10, font=("Microsoft YaHei UI", 10), height=18)
        self.text.pack(fill="both", expand=True)
        self.text.configure(state="disabled")

    def _load_vars_from_config(self) -> None:
        stt = self.config.get("stt", {})
        output = self.config.get("output", {})
        provider = stt.get("provider", "funasr")
        self.provider_var.set(provider)
        self.model_var.set(stt.get("model", "paraformer-zh" if provider == "funasr" else "base"))
        self.device_var.set(stt.get("device", "cpu"))
        self.batch_size_var.set(int(stt.get("batch_size_s", 60)))
        self.timeout_var.set(int(stt.get("load_timeout_seconds", 90)))
        self.fallback_model_var.set(stt.get("fallback_model", "base"))
        self.fallback_beam_var.set(int(stt.get("fallback_beam_size", 2)))
        self.hotwords_var.set(stt.get("hotwords", ""))
        self.tts_enabled_var.set(bool(output.get("tts_enabled", True)))
        self.beep_enabled_var.set(bool(output.get("beep_enabled", True)))
        self._sync_model_choices(keep_current=True)

    def _sync_model_choices(self, keep_current: bool = False) -> None:
        values = FUNASR_MODELS if self.provider_var.get() == "funasr" else WHISPER_MODELS
        self.model_combo.configure(values=values)
        if not keep_current or not self.model_var.get():
            self.model_var.set(values[0])

    def save_config(self) -> None:
        try:
            self._write_config_from_vars()
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))
            return
        self.restart_status_var.set("配置已保存。点“保存并重启后台”后生效。")

    def save_and_restart(self) -> None:
        self.save_config()
        try:
            self._restart_background_agent()
        except Exception as exc:
            messagebox.showerror("重启失败", str(exc))
            return
        self.restart_status_var.set("后台已重启，新参数已生效。")

    def _write_config_from_vars(self) -> None:
        config = self._load_config()
        stt = config.setdefault("stt", {})
        output = config.setdefault("output", {})
        provider = self.provider_var.get().strip() or "funasr"
        stt["provider"] = provider
        stt["model"] = self.model_var.get().strip() or ("paraformer-zh" if provider == "funasr" else "base")
        stt["device"] = self.device_var.get().strip() or "cpu"
        stt["batch_size_s"] = int(self.batch_size_var.get())
        stt["load_timeout_seconds"] = int(self.timeout_var.get())
        stt["fallback_provider"] = "faster_whisper"
        stt["fallback_model"] = self.fallback_model_var.get().strip() or "base"
        stt["fallback_beam_size"] = int(self.fallback_beam_var.get())
        stt["hotwords"] = self.hotwords_var.get().strip()
        stt.setdefault("vad_model", VAD_MODELS[0])
        stt.setdefault("punc_model", PUNC_MODELS[0])
        stt.setdefault("sample_rate", 16000)
        output["tts_enabled"] = bool(self.tts_enabled_var.get())
        output["beep_enabled"] = bool(self.beep_enabled_var.get())
        output.pop("paste_mode", None)
        self._normalize_fixed_chinese_config(config)

        with self.config_path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(config, file, allow_unicode=True, sort_keys=False)
        self.config = config

    def _normalize_fixed_chinese_config(self, config: dict) -> None:
        config.setdefault("stt", {})["hotwords"] = "Claude Codex code x F7 F8 代码 项目 文件 测试 修复 修改 实现 解释 总结 提交 运行"
        config.setdefault("routing", {})["local_commands"] = {
            "stop": ["停止", "停止朗读", "别读了"],
            "retry": ["重新录音", "重来"],
            "cancel": ["取消", "放弃"],
            "confirm": ["确认", "继续"],
            "reject": ["不确认", "不要"],
        }
        config.setdefault("safety", {})["confirm_keywords"] = ["删除", "覆盖", "提交", "推送", "安装", "卸载", "重置", "迁移", "清空", "格式化", "发布", "部署"]

    def _restart_background_agent(self) -> None:
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(self.project_dir / "stop_voice_agent.ps1")], cwd=str(self.project_dir), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        executable = str(pythonw if pythonw.exists() else sys.executable)
        subprocess.Popen([executable, str(self.project_dir / "background_voice_agent.py")], cwd=str(self.project_dir), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _refresh(self) -> None:
        content = self._tail_lines(80)
        if content != self._last_content:
            self._last_content = content
            self.text.configure(state="normal")
            self.text.delete("1.0", "end")
            self.text.insert("1.0", content)
            self.text.see("end")
            self.text.configure(state="disabled")
        self.root.after(700, self._refresh)

    def _tail_lines(self, count: int) -> str:
        try:
            lines = self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return ""
        return "\n".join(line for line in (self._simplify(line) for line in lines[-count:]) if line)

    def _simplify(self, line: str) -> str:
        if "] " in line:
            line = line.split("] ", 1)[1]
        for old, new in {"TRANSCRIPT": "识别", "STATUS": "状态", "WARN": "提醒", "ERROR": "错误", "AGENT": "发送", "RESULT": "结果"}.items():
            line = line.replace(old, new)
        return line.strip()

    def _clear(self) -> None:
        self.log_path.write_text("", encoding="utf-8")
        self._last_content = ""
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def _on_unmap(self, event) -> None:
        if event.widget == self.root and self.root.state() == "iconic":
            self.root.after(0, self.hide)

    def hide(self) -> None:
        self.root.withdraw()

    def show(self) -> None:
        self.root.after(0, self._show_on_ui_thread)

    def _show_on_ui_thread(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def quit(self) -> None:
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)

    def _start_tray(self) -> None:
        image = self._make_tray_image()
        menu = pystray.Menu(
            pystray.MenuItem("显示控制台", lambda icon, item: self.show(), default=True),
            pystray.MenuItem("隐藏窗口", lambda icon, item: self.hide()),
            pystray.MenuItem("清空日志", lambda icon, item: self.root.after(0, self._clear)),
            pystray.MenuItem("退出控制台", lambda icon, item: self.quit()),
        )
        self.tray_icon = pystray.Icon("voice-agent-log", image, "语音 Agent", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _make_tray_image(self) -> Image.Image:
        image = Image.new("RGB", (64, 64), "#1f2937")
        draw = ImageDraw.Draw(image)
        draw.ellipse((10, 10, 54, 54), fill="#2563eb")
        draw.rectangle((29, 18, 35, 42), fill="white")
        draw.arc((20, 30, 44, 54), 0, 180, fill="white", width=4)
        return image

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    app = LogOverlay(Path(__file__).resolve().parent)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
