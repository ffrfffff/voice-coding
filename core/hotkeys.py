from __future__ import annotations

import time
from typing import Callable


KEY_ALIASES = {
    "ctrl": {"ctrl_l", "ctrl_r"},
    "control": {"ctrl_l", "ctrl_r"},
    "alt": {"alt_l", "alt_r", "alt_gr"},
    "shift": {"shift_l", "shift_r"},
    "space": {"space"},
    "esc": {"esc"},
}


def normalize_key(key) -> str:
    name = getattr(key, "name", None)
    if name:
        return name.lower()
    char = getattr(key, "char", None)
    return (char or str(key)).lower()


def parse_hotkey(combo: str) -> list[set[str]]:
    parts = [part.strip().lower() for part in combo.split("+") if part.strip()]
    return [KEY_ALIASES.get(part, {part}) for part in parts]


def combo_pressed(required: list[set[str]], pressed: set[str]) -> bool:
    return all(options & pressed for options in required)


class PushToTalkHotkeys:
    def __init__(
        self,
        mode: str,
        toggle_hotkey: str,
        default_agent: str,
        claude_hotkey: str,
        codex_hotkey: str,
        stop_tts_hotkey: str,
        on_start: Callable[[str], None],
        on_stop: Callable[[str], None],
        on_stop_tts: Callable[[], None],
        ui,
    ):
        self.mode = mode
        self.default_agent = default_agent if default_agent in {"claude", "codex"} else "codex"
        self.toggle_hotkey = parse_hotkey(toggle_hotkey)
        self.bindings = {
            "claude": parse_hotkey(claude_hotkey),
            "codex": parse_hotkey(codex_hotkey),
        }
        self.stop_tts_key = parse_hotkey(stop_tts_hotkey)
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_stop_tts = on_stop_tts
        self.ui = ui
        self.pressed: set[str] = set()
        self.active_agent: str | None = None
        self._toggle_down = False

    def run_forever(self) -> None:
        try:
            from pynput import keyboard
        except ImportError as exc:
            raise RuntimeError("缺少 pynput，请先运行: pip install -r requirements.txt") from exc

        self.ui.show_hotkey_help()
        with keyboard.Listener(on_press=self._on_press, on_release=self._on_release) as listener:
            listener.join()

    def _on_press(self, key) -> None:
        key_name = normalize_key(key)
        self.pressed.add(key_name)

        if combo_pressed(self.stop_tts_key, self.pressed):
            self.on_stop_tts()
            return

        if self.mode == "toggle":
            if combo_pressed(self.toggle_hotkey, self.pressed) and not self._toggle_down:
                self._toggle_down = True
                if self.active_agent:
                    agent = self.active_agent
                    self.active_agent = None
                    self.on_stop(agent)
                else:
                    self.active_agent = self.default_agent
                    self.on_start(self.default_agent)
            return

        if self.active_agent:
            return

        for agent, combo in self.bindings.items():
            if combo_pressed(combo, self.pressed):
                self.active_agent = agent
                self.on_start(agent)
                break

    def _on_release(self, key) -> None:
        key_name = normalize_key(key)
        self.pressed.discard(key_name)

        if self.mode == "toggle":
            if not combo_pressed(self.toggle_hotkey, self.pressed):
                self._toggle_down = False
            return

        released_agent = self.active_agent
        if released_agent and not combo_pressed(self.bindings[released_agent], self.pressed):
            self.active_agent = None
            time.sleep(0.05)
            self.on_stop(released_agent)
