from __future__ import annotations

import argparse
import webbrowser
import sys
from pathlib import Path

from agents.claude_agent import ClaudeAgent
from agents.codex_agent import CodexAgent
from core.config import load_config
from core.hotkeys import PushToTalkHotkeys
from core.recorder import Recorder
from core.risk_checker import RiskChecker
from core.router import Router
from core.session import SessionController
from core.summarizer import Summarizer
from providers.stt_whisper import FasterWhisperSTT
from providers.stt_funasr import FunASRSTT
from providers.tts_edge import EdgeTTS
from ui.console import ConsoleUI


def build_controller(config: dict, project_dir: Path) -> SessionController:
    ui = ConsoleUI()
    recorder = Recorder(project_dir / "data" / "recordings")
    stt_config = config.get("stt", {})
    stt = FunASRSTT(stt_config, ui) if stt_config.get("provider") == "funasr" else FasterWhisperSTT(stt_config, ui)
    router = Router(config.get("routing", {}), config.get("agents", {}).get("default", "codex"))
    risk_checker = RiskChecker(config.get("safety", {}), config.get("routing", {}))
    summarizer = Summarizer(config.get("output", {}))
    tts = EdgeTTS(config.get("output", {}), project_dir / "data" / "tts", ui)

    agents_config = config.get("agents", {})
    agents = {
        "claude": ClaudeAgent(agents_config.get("claude", {}), agents_config, project_dir),
        "codex": CodexAgent(agents_config.get("codex", {}), agents_config, project_dir),
    }

    return SessionController(
        ui=ui,
        recorder=recorder,
        stt=stt,
        router=router,
        risk_checker=risk_checker,
        summarizer=summarizer,
        tts=tts,
        agents=agents,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Local voice router for Claude and Codex.")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--text", help="Skip recording and route this text directly.")
    parser.add_argument("--agent", choices=["claude", "codex"], default=None, help="Fallback target agent.")
    parser.add_argument("--host", default="127.0.0.1", help="Web dictation host.")
    parser.add_argument("--port", type=int, default=8765, help="Web dictation port.")
    parser.add_argument("--local-gui", action="store_true", help="Use the old local Whisper GUI.")
    parser.add_argument("--console", action="store_true", help="Use the old console hotkey mode.")
    args = parser.parse_args()

    project_dir = Path.cwd()
    config = load_config(project_dir / args.config)
    controller = build_controller(config, project_dir)

    if args.text:
        controller.handle_text(args.text, args.agent or config.get("agents", {}).get("default", "codex"))
        return 0

    if not args.console and not args.local_gui:
        from http.server import ThreadingHTTPServer

        from web_app import WebAppState, make_handler

        state = WebAppState(config, project_dir)
        handler = make_handler(state, project_dir / "web")
        server = ThreadingHTTPServer((args.host, args.port), handler)
        url = f"http://{args.host}:{args.port}"
        print(f"实时听写界面已启动: {url}")
        webbrowser.open(url)
        server.serve_forever()
        return 0

    if args.local_gui:
        from ui.tk_app import VoiceRouterApp

        app = VoiceRouterApp(config, project_dir)
        app.run()
        return 0

    hotkey_config = config.get("input", {})
    hotkeys = PushToTalkHotkeys(
        mode=hotkey_config.get("mode", "toggle"),
        toggle_hotkey=hotkey_config.get("toggle_hotkey", "f8"),
        default_agent=config.get("agents", {}).get("default", "codex"),
        claude_hotkey=hotkey_config.get("claude_hotkey", "ctrl+alt+c"),
        codex_hotkey=hotkey_config.get("codex_hotkey", "ctrl+alt+x"),
        stop_tts_hotkey=hotkey_config.get("stop_tts_hotkey", "esc"),
        on_start=controller.start_recording,
        on_stop=controller.stop_recording_and_handle,
        on_stop_tts=controller.stop_tts,
        ui=controller.ui,
    )
    hotkeys.run_forever()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n已退出。")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\n启动失败: {exc}", file=sys.stderr)
        raise SystemExit(1)
