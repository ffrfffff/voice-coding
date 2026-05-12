from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import threading
import time
import traceback
import winsound

from agents.claude_agent import ClaudeAgent
from agents.codex_agent import CodexAgent
from core.config import load_config
from core.recorder import Recorder
from core.risk_checker import RiskChecker
from core.router import Router
from core.summarizer import Summarizer
from providers.stt_whisper import FasterWhisperSTT
from providers.stt_funasr import FunASRSTT
from providers.tts_edge import EdgeTTS


class BackgroundUI:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def status(self, message: str) -> None:
        self._write("STATUS", message)

    def warning(self, message: str) -> None:
        self._write("WARN", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)

    def transcript(self, text: str) -> None:
        self._write("TRANSCRIPT", text)

    def agent_start(self, target: str, prompt: str) -> None:
        self._write("AGENT", f"{target}: {prompt}")

    def agent_result(self, result) -> None:
        state = "ok" if result.success else "failed"
        self._write("RESULT", f"{result.agent_name} {state}: {result.summary}")

    def _write(self, level: str, message: str) -> None:
        if self._is_noisy(level, message):
            return
        line = f"{datetime.now().isoformat(timespec='seconds')} [{level}] {message}\n"
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as file:
                file.write(line)

    def _is_noisy(self, level: str, message: str) -> bool:
        noisy_fragments = [
            "\u6b63\u5728\u52a0\u8f7d Whisper",
            "正在加载 Whisper",
            "TTS:",
            "\u6587\u672c\u5df2\u4fdd\u5b58",
            "文本已保存",
        ]
        return level == "STATUS" and any(fragment in message for fragment in noisy_fragments)


class BackgroundVoiceAgent:
    def __init__(self, config: dict, project_dir: Path):
        self.config = config
        self.project_dir = project_dir
        self.ui = BackgroundUI(project_dir / "data" / "logs" / "background.log")
        self.recorder = Recorder(project_dir / "data" / "recordings")
        self.stt = self._build_stt(config.get("stt", {}))
        self.router = Router(config.get("routing", {}), config.get("agents", {}).get("default", "codex"))
        self.risk_checker = RiskChecker(config.get("safety", {}), config.get("routing", {}))
        self.summarizer = Summarizer(config.get("output", {}))
        self.tts = EdgeTTS(config.get("output", {}), project_dir / "data" / "tts", self.ui)
        output_config = config.get("output", {})
        self.beep_enabled = bool(output_config.get("beep_enabled", False))
        self.f7_send_delay_ms = int(output_config.get("f7_send_delay_ms", 600))

        agents_config = config.get("agents", {})
        self.agents = {
            "claude": ClaudeAgent(agents_config.get("claude", {}), agents_config, project_dir),
            "codex": CodexAgent(agents_config.get("codex", {}), agents_config, project_dir),
        }

        self.recording = False
        self.recording_mode: str | None = None
        self.busy = False
        self.cursor_ready_to_send = False
        self.task_id = 0
        self._lock = threading.Lock()

    def _build_stt(self, stt_config: dict):
        provider = stt_config.get("provider", "faster_whisper")
        if provider == "funasr":
            return FunASRSTT(stt_config, self.ui)
        return FasterWhisperSTT(stt_config, self.ui)

    def toggle_recording(self) -> None:
        with self._lock:
            if self.busy:
                self._cancel_current_task_locked()
            if self.recording:
                if self.recording_mode != "agent":
                    self.ui.status("\u5f53\u524d\u662f F7 \u5149\u6807\u542c\u5199\u6a21\u5f0f\uff0c\u8bf7\u6309 F7 \u505c\u6b62\u3002")
                    return
                self.recording = False
                self.recording_mode = None
                self.busy = True
                task_id = self.task_id
                self._beep(520, 90)
                threading.Thread(target=self._stop_and_process, args=(task_id,), daemon=True).start()
                return
            self._new_task_locked()
            self.recording = True
            self.recording_mode = "agent"
            self.cursor_ready_to_send = False
            self.tts.stop()
            self.recorder.start()
            self._beep(880, 90)
            self.ui.status("\u5f00\u59cb\u5f55\u97f3\u3002")

    def toggle_cursor_dictation(self) -> None:
        with self._lock:
            if self.busy:
                self._cancel_current_task_locked()
            if self.recording:
                if self.recording_mode != "cursor":
                    self.ui.status("\u5f53\u524d\u662f F8 Agent \u6a21\u5f0f\uff0c\u8bf7\u6309 F8 \u505c\u6b62\u3002")
                    return
                self.recording = False
                self.recording_mode = None
                self.busy = True
                task_id = self.task_id
                self._beep(520, 90)
                threading.Thread(target=self._stop_paste_and_send_at_cursor, args=(task_id,), daemon=True).start()
                return

            self._new_task_locked()
            self.recording = True
            self.recording_mode = "cursor"
            self.tts.stop()
            self.recorder.start()
            self._beep(880, 90)
            self.ui.status("F7 \u5149\u6807\u542c\u5199\u5f00\u59cb\u3002")

    def stop_tts(self) -> None:
        self.tts.stop()
        self.ui.status("\u5df2\u505c\u6b62\u64ad\u62a5\u3002")

    def _stop_and_process(self, task_id: int) -> None:
        try:
            wav_path = self.recorder.stop_and_save()
            if wav_path is None:
                self._say("\u6ca1\u6709\u5f55\u5230\u6709\u6548\u97f3\u9891\u3002")
                return
            if self._is_cancelled(task_id):
                return

            self.ui.status("\u5f55\u97f3\u7ed3\u675f\uff0c\u6b63\u5728\u8bc6\u522b\u3002")
            text = self.stt.transcribe(wav_path).strip()
            if self._is_cancelled(task_id):
                return
            if not text:
                self._say("\u6ca1\u6709\u8bc6\u522b\u5230\u6587\u672c\u3002")
                return

            self.ui.transcript(text)
            self._handle_text(text, task_id)
        except Exception as exc:
            self.ui.error(f"{exc}\n{traceback.format_exc()}")
            self._say("\u5904\u7406\u8bed\u97f3\u65f6\u51fa\u9519\u4e86\u3002")
        finally:
            with self._lock:
                if self.task_id == task_id:
                    self.busy = False

    def _stop_and_paste_at_cursor(self) -> None:
        try:
            wav_path = self.recorder.stop_and_save()
            if wav_path is None:
                self.ui.warning("F7 \u6ca1\u6709\u5f55\u5230\u6709\u6548\u97f3\u9891\u3002")
                return

            self.ui.status("F7 \u5f55\u97f3\u7ed3\u675f\uff0c\u6b63\u5728\u8bc6\u522b\u5e76\u7c98\u8d34\u3002")
            text = self.stt.transcribe(wav_path).strip()
            if not text:
                self.ui.warning("F7 \u6ca1\u6709\u8bc6\u522b\u5230\u6587\u672c\u3002")
                return

            self.ui.transcript(f"F7: {text}")
            self._paste_text_at_cursor(text)
            with self._lock:
                self.cursor_ready_to_send = True
            self.ui.status("F7 \u5df2\u7c98\u8d34\u5230\u5149\u6807\u4f4d\u7f6e\u3002\u518d\u6309 F7 \u53d1\u9001 Enter\u3002")
        except Exception as exc:
            self.ui.error(f"{exc}\n{traceback.format_exc()}")
        finally:
            with self._lock:
                self.busy = False

    def _stop_paste_and_send_at_cursor(self, task_id: int) -> None:
        try:
            wav_path = self.recorder.stop_and_save()
            if wav_path is None:
                self.ui.warning("F7 \u6ca1\u6709\u5f55\u5230\u6709\u6548\u97f3\u9891\u3002")
                return
            if self._is_cancelled(task_id):
                return

            self.ui.status("F7 \u5f55\u97f3\u7ed3\u675f\uff0c\u6b63\u5728\u8bc6\u522b\u3001\u7c98\u8d34\u5e76\u53d1\u9001\u3002")
            text = self.stt.transcribe(wav_path).strip()
            if self._is_cancelled(task_id):
                return
            if not text:
                self.ui.warning("F7 \u6ca1\u6709\u8bc6\u522b\u5230\u6587\u672c\u3002")
                return

            self.ui.transcript(f"F7: {text}")
            self._paste_clipboard_with_shift_insert(text, task_id)
            self.ui.status("F7 \u5df2\u7c98\u8d34\u5230\u5149\u6807\u4f4d\u7f6e\u5e76\u53d1\u9001 Enter\u3002")
        except Exception as exc:
            self.ui.error(f"{exc}\n{traceback.format_exc()}")
        finally:
            with self._lock:
                if self.task_id == task_id:
                    self.busy = False

    def _handle_text(self, text: str, task_id: int) -> None:
        confirmation_state, pending = self.risk_checker.consume_confirmation(text)
        if confirmation_state == "confirmed" and pending:
            self._run_agent(pending["target"], pending["prompt"], task_id)
            return
        if confirmation_state == "rejected":
            self.risk_checker.pending = None
            self._say("\u5df2\u53d6\u6d88\u3002")
            return
        if confirmation_state == "waiting":
            self._say("\u8bf7\u8bf4\u786e\u8ba4\u7ee7\u7eed\uff0c\u6216\u8bf4\u53d6\u6d88\u653e\u5f03\u3002")
            return

        decision = self.router.route(text, None)
        if decision.kind == "local":
            self._handle_local_command(decision.target)
            return

        if self.risk_checker.needs_confirmation(decision.prompt):
            self.risk_checker.hold(decision.target, decision.prompt)
            self._say(f"\u8bc6\u522b\u5230\u9ad8\u98ce\u9669\u64cd\u4f5c\uff0c\u76ee\u6807\u662f {decision.target}\u3002\u8bf7\u518d\u6b21\u6309 F8 \u8bf4\u786e\u8ba4\u6216\u53d6\u6d88\u3002")
            return

        self._run_agent(decision.target, decision.prompt, task_id)

    def _handle_local_command(self, command: str | None) -> None:
        if command == "stop":
            self.stop_tts()
        elif command == "cancel":
            self.risk_checker.pending = None
            self._say("\u5df2\u53d6\u6d88\u3002")
        elif command == "retry":
            self._say("\u8bf7\u91cd\u65b0\u6309 F8 \u5f55\u97f3\u3002")
        else:
            self._say("\u672c\u5730\u547d\u4ee4\u5df2\u5904\u7406\u3002")

    def _run_agent(self, target: str, prompt: str, task_id: int) -> None:
        agent = self.agents.get(target)
        if not agent:
            self._say(f"\u672a\u77e5 Agent: {target}")
            return

        self.ui.agent_start(target, prompt)
        result = agent.run(prompt, context={})
        if self._is_cancelled(task_id):
            return
        result.summary = self.summarizer.summarize(result)
        self.ui.agent_result(result)
        spoken = self.summarizer.spoken_summary(result, target)
        self._say(spoken)

    def _new_task_locked(self) -> int:
        self.task_id += 1
        self.busy = False
        self.cursor_ready_to_send = False
        return self.task_id

    def _cancel_current_task_locked(self) -> None:
        self.task_id += 1
        self.busy = False
        self.cursor_ready_to_send = False
        self.ui.status("\u5df2\u653e\u5f03\u4e0a\u4e00\u6b21\u8bed\u97f3\u5904\u7406\u3002")

    def _is_cancelled(self, task_id: int) -> bool:
        return self.task_id != task_id

    def _say(self, text: str) -> None:
        self.ui.status(f"TTS: {text}")
        self.tts.speak(text)

    def _beep(self, frequency: int, duration_ms: int) -> None:
        if not self.beep_enabled:
            return
        try:
            winsound.Beep(frequency, duration_ms)
        except RuntimeError:
            pass

    def _paste_clipboard_with_shift_insert(self, text: str, task_id: int) -> None:
        self._copy_to_clipboard(text)
        time.sleep(0.25)
        self.ui.status(f"F7 粘贴目标窗口: {self._foreground_window_title()}")
        if self._is_cancelled(task_id):
            return

        try:
            from core.sendkeys import send_enter, send_shift_insert

            send_shift_insert()
            self.ui.status("F7 已执行粘贴热键: shift+insert")
            time.sleep(max(self.f7_send_delay_ms, 0) / 1000)
            if self._is_cancelled(task_id):
                return
            self.ui.status(f"F7 回车目标窗口: {self._foreground_window_title()}")
            send_enter()
            self.ui.status("F7 已执行 Enter。")
        except Exception as exc:
            self.ui.warning(f"Shift+Insert/Enter 发送失败，改用 pyautogui: {exc}")
            import pyautogui

            pyautogui.hotkey("shift", "insert")
            time.sleep(max(self.f7_send_delay_ms, 0) / 1000)
            if not self._is_cancelled(task_id):
                pyautogui.press("enter")
            self.ui.status("F7 已执行 pyautogui Shift+Insert 和 Enter。")

    def _paste_clipboard_with_configured_hotkey(self, text: str, task_id: int) -> None:
        self._copy_to_clipboard(text)
        time.sleep(0.25)
        self.ui.status(f"F7 粘贴目标窗口: {self._foreground_window_title()}")
        if self._is_cancelled(task_id):
            return

        try:
            self._send_paste_hotkey()
            self.ui.status(f"F7 已执行粘贴热键: {self.paste_mode}")
            time.sleep(max(self.f7_send_delay_ms, 0) / 1000)
            if self._is_cancelled(task_id):
                return
            self.ui.status(f"F7 回车目标窗口: {self._foreground_window_title()}")
            self._send_enter_key()
            self.ui.status("F7 已执行 Enter。")
        except Exception as exc:
            self.ui.warning(f"pynput 粘贴/发送失败，改用原生 SendInput: {exc}")
            from core.sendkeys import send_ctrl_v, send_enter, send_shift_insert

            if self.paste_mode == "shift_insert":
                send_shift_insert()
            else:
                send_ctrl_v()
            time.sleep(max(self.f7_send_delay_ms, 0) / 1000)
            if not self._is_cancelled(task_id):
                send_enter()
            self.ui.status(f"F7 已执行原生粘贴热键和 Enter: {self.paste_mode}")

    def _send_paste_hotkey(self) -> None:
        from pynput.keyboard import Controller, Key

        keyboard = Controller()
        if self.paste_mode == "shift_insert":
            keyboard.press(Key.shift)
            time.sleep(0.05)
            keyboard.press(Key.insert)
            time.sleep(0.05)
            keyboard.release(Key.insert)
            time.sleep(0.05)
            keyboard.release(Key.shift)
            return

        keyboard.press(Key.ctrl)
        time.sleep(0.05)
        keyboard.press("v")
        time.sleep(0.05)
        keyboard.release("v")
        time.sleep(0.05)
        keyboard.release(Key.ctrl)

    def _send_enter_key(self) -> None:
        from pynput.keyboard import Controller, Key

        keyboard = Controller()
        keyboard.press(Key.enter)
        time.sleep(0.05)
        keyboard.release(Key.enter)

    def _paste_clipboard_hotkey_and_enter(self, text: str, task_id: int) -> None:
        self._copy_to_clipboard(text)
        time.sleep(0.25)
        self.ui.status(f"F7 粘贴目标窗口: {self._foreground_window_title()}")
        if self._is_cancelled(task_id):
            return

        try:
            import pyautogui

            if self.paste_mode == "shift_insert":
                from core.sendkeys import send_shift_insert

                send_shift_insert()
            else:
                pyautogui.hotkey("ctrl", "v")
            self.ui.status(f"F7 已执行粘贴热键: {self.paste_mode}")

            time.sleep(max(self.f7_send_delay_ms, 0) / 1000)
            if self._is_cancelled(task_id):
                return

            self.ui.status(f"F7 回车目标窗口: {self._foreground_window_title()}")
            pyautogui.press("enter")
            self.ui.status("F7 已执行 Enter。")
        except Exception as exc:
            self.ui.warning(f"pyautogui 粘贴/发送失败，改用原生 SendInput: {exc}")
            from core.sendkeys import send_ctrl_v, send_enter, send_shift_insert

            if self.paste_mode == "shift_insert":
                send_shift_insert()
            else:
                send_ctrl_v()
            time.sleep(max(self.f7_send_delay_ms, 0) / 1000)
            if not self._is_cancelled(task_id):
                send_enter()
            self.ui.status(f"F7 已执行原生粘贴热键和 Enter: {self.paste_mode}")

    def _paste_and_send_text_at_cursor(self, text: str, task_id: int) -> None:
        self._copy_to_clipboard(text)
        time.sleep(0.5)
        self.ui.status(f"F7 粘贴目标窗口: {self._foreground_window_title()}")
        if self._is_cancelled(task_id):
            return

        try:
            import pyautogui

            pyautogui.PAUSE = 0.05
            self._release_modifier_keys(pyautogui)
            if self.paste_mode == "shift_insert":
                pyautogui.keyDown("shift")
                time.sleep(0.05)
                pyautogui.press("insert")
                time.sleep(0.05)
                pyautogui.keyUp("shift")
            else:
                pyautogui.keyDown("ctrl")
                time.sleep(0.05)
                pyautogui.press("v")
                time.sleep(0.05)
                pyautogui.keyUp("ctrl")
            self._release_modifier_keys(pyautogui)
            self.ui.status(f"F7 已执行粘贴按键: {self.paste_mode}")

            time.sleep(max(self.f7_send_delay_ms, 0) / 1000)
            if self._is_cancelled(task_id):
                return

            self.ui.status(f"F7 Enter 目标窗口: {self._foreground_window_title()}")
            self._release_modifier_keys(pyautogui)
            pyautogui.press("enter")
            self._release_modifier_keys(pyautogui)
            self.ui.status("F7 已执行 Enter。")
        except Exception as exc:
            self.ui.warning(f"pyautogui 粘贴/发送失败，改用原生 SendInput: {exc}")
            from core.sendkeys import send_ctrl_v, send_enter, send_shift_insert

            if self.paste_mode == "shift_insert":
                send_shift_insert()
            else:
                send_ctrl_v()
            time.sleep(max(self.f7_send_delay_ms, 0) / 1000)
            if not self._is_cancelled(task_id):
                send_enter()
            self.ui.status(f"F7 已执行原生粘贴和 Enter: {self.paste_mode}")

    def _release_modifier_keys(self, pyautogui_module) -> None:
        for key in ("ctrl", "shift", "alt", "win"):
            try:
                pyautogui_module.keyUp(key)
            except Exception:
                pass

    def _foreground_window_title(self) -> str:
        try:
            import ctypes

            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            return buffer.value or "<无标题窗口>"
        except Exception as exc:
            return f"<读取失败: {exc}>"

    def _paste_text_at_cursor(self, text: str) -> None:
        from core.sendkeys import send_ctrl_v, send_shift_insert

        self._copy_to_clipboard(text)
        time.sleep(0.35)
        try:
            if self.paste_mode == "shift_insert":
                send_shift_insert()
            else:
                send_ctrl_v()
            self.ui.status(f"F7 已执行粘贴按键: {self.paste_mode}")
        except Exception as exc:
            self.ui.warning(f"原生粘贴按键失败，改用 pyautogui: {exc}")
            import pyautogui

            if self.paste_mode == "shift_insert":
                pyautogui.hotkey("shift", "insert")
            else:
                pyautogui.hotkey("ctrl", "v")
            self.ui.status(f"F7 已执行 pyautogui 粘贴按键: {self.paste_mode}")
        time.sleep(0.35)

    def _copy_to_clipboard(self, text: str) -> None:
        import pyperclip

        last_error = None
        for _ in range(5):
            try:
                pyperclip.copy(text)
                if pyperclip.paste() == text:
                    return
            except Exception as exc:
                last_error = exc
            time.sleep(0.1)
        if last_error:
            raise RuntimeError(f"写入剪贴板失败: {last_error}") from last_error
        raise RuntimeError("写入剪贴板失败: 剪贴板内容校验未通过")

    def _press_enter(self) -> None:
        try:
            import pyautogui

            pyautogui.press("enter")
        except Exception:
            from core.sendkeys import send_enter

            send_enter()


def run_hotkey_loop(agent: BackgroundVoiceAgent) -> None:
    from pynput import keyboard

    f8_down = False
    f7_down = False

    def on_press(key):
        nonlocal f8_down, f7_down
        if key == keyboard.Key.f8:
            if f8_down:
                return
            f8_down = True
            agent.toggle_recording()
        elif key == keyboard.Key.f7:
            if f7_down:
                return
            f7_down = True
            agent.toggle_cursor_dictation()
        elif key == keyboard.Key.esc:
            agent.stop_tts()

    def on_release(key):
        nonlocal f8_down, f7_down
        if key == keyboard.Key.f8:
            f8_down = False
        elif key == keyboard.Key.f7:
            f7_down = False

    agent.ui.status("\u540e\u53f0\u8bed\u97f3 Agent \u5df2\u542f\u52a8\u3002F8 \u53d1\u7ed9 Agent\uff1bF7 \u5f55\u97f3/\u7c98\u8d34/\u53d1\u9001\uff1bEsc \u505c\u6b62\u64ad\u62a5\u3002")
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


def main() -> int:
    parser = argparse.ArgumentParser(description="Background F8 voice agent.")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parent
    config = load_config(project_dir / args.config)
    agent = BackgroundVoiceAgent(config, project_dir)
    run_hotkey_loop(agent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
