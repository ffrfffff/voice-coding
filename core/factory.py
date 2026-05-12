from __future__ import annotations

from pathlib import Path

from agents.claude_agent import ClaudeAgent
from agents.codex_agent import CodexAgent
from core.recorder import Recorder
from core.risk_checker import RiskChecker
from core.router import Router
from core.session import SessionController
from core.summarizer import Summarizer
from providers.stt_funasr import FunASRSTT
from providers.stt_whisper import FasterWhisperSTT
from providers.tts_edge import EdgeTTS


def build_agents(config: dict, project_dir: Path) -> dict:
    agents_config = config.get("agents", {})
    return {
        "claude": ClaudeAgent(agents_config.get("claude", {}), agents_config, project_dir),
        "codex": CodexAgent(agents_config.get("codex", {}), agents_config, project_dir),
    }


def build_router(config: dict) -> Router:
    agents_config = config.get("agents", {})
    return Router(config.get("routing", {}), agents_config.get("default", "codex"))


def build_risk_checker(config: dict) -> RiskChecker:
    return RiskChecker(config.get("safety", {}), config.get("routing", {}))


def build_summarizer(config: dict) -> Summarizer:
    return Summarizer(config.get("output", {}))


def build_stt(config: dict, ui):
    stt_config = config.get("stt", {})
    if stt_config.get("provider") == "funasr":
        return FunASRSTT(stt_config, ui)
    return FasterWhisperSTT(stt_config, ui)


def build_tts(config: dict, project_dir: Path, ui) -> EdgeTTS:
    return EdgeTTS(config.get("output", {}), project_dir / "data" / "tts", ui)


def build_session_controller(config: dict, project_dir: Path, ui) -> SessionController:
    return SessionController(
        ui=ui,
        recorder=Recorder(project_dir / "data" / "recordings"),
        stt=build_stt(config, ui),
        router=build_router(config),
        risk_checker=build_risk_checker(config),
        summarizer=build_summarizer(config),
        tts=build_tts(config, project_dir, ui),
        agents=build_agents(config, project_dir),
    )
