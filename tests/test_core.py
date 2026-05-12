from __future__ import annotations

import unittest
import time
from pathlib import Path

import yaml

from app import build_controller
from core.config import load_config
from core.output_cleaner import clean_output
from core.hotkeys import parse_hotkey
from core.risk_checker import RiskChecker
from core.router import Router
from ui.tk_app import VoiceRouterApp
from web_app import WebAppState
from desktop_app import find_free_port
from background_voice_agent import BackgroundUI


ROOT = Path(__file__).resolve().parents[1]


class ConfigTests(unittest.TestCase):
    def test_config_loads(self) -> None:
        config = load_config(ROOT / "config.yaml")
        self.assertEqual(config["input"]["mode"], "toggle")
        self.assertIn(config["agents"]["default"], {"claude", "codex"})
        self.assertEqual(config["stt"]["provider"], "funasr")
        self.assertTrue(config["stt"]["use_local_cache"])
        self.assertEqual(config["stt"]["local_cache_root"], "models/modelscope")
        self.assertEqual(config["stt"]["fallback_local_cache_root"], "models/huggingface")
        self.assertEqual(config["stt"]["model"], "paraformer-zh")
        self.assertEqual(config["stt"]["model_hub"], "ms")
        self.assertEqual(config["stt"]["fallback_provider"], "faster_whisper")
        self.assertIn("Claude", config["stt"]["hotwords"])
        self.assertTrue(config["output"]["beep_enabled"])
        self.assertGreaterEqual(config["output"]["f7_send_delay_ms"], 300)


class RoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
        self.router = Router(config["routing"], config["agents"]["default"])

    def test_explicit_claude_route(self) -> None:
        decision = self.router.route("Claude 解释当前项目", "codex")
        self.assertEqual(decision.kind, "agent")
        self.assertEqual(decision.target, "claude")
        self.assertEqual(decision.prompt, "解释当前项目")

    def test_explicit_codex_route(self) -> None:
        decision = self.router.route("Codex 修复这个错误", "claude")
        self.assertEqual(decision.kind, "agent")
        self.assertEqual(decision.target, "codex")
        self.assertEqual(decision.prompt, "修复这个错误")

    def test_local_stop_route(self) -> None:
        decision = self.router.route("停止朗读", "codex")
        self.assertEqual(decision.kind, "local")
        self.assertEqual(decision.target, "stop")

    def test_auto_route_claude_for_analysis(self) -> None:
        decision = self.router.route("帮我分析一下这个方案是否合理", None)
        self.assertEqual(decision.target, "claude")
        self.assertEqual(decision.reason, "auto route")

    def test_auto_route_codex_for_implementation(self) -> None:
        decision = self.router.route("帮我修复这个测试错误", None)
        self.assertEqual(decision.target, "codex")
        self.assertEqual(decision.reason, "auto route")


class RiskTests(unittest.TestCase):
    def test_risk_confirmation_lifecycle(self) -> None:
        routing = {"local_commands": {"confirm": ["确认"], "reject": ["取消"]}}
        checker = RiskChecker({"require_confirmation": True, "confirm_keywords": ["提交"]}, routing)
        self.assertTrue(checker.needs_confirmation("提交这些修改"))
        checker.hold("codex", "提交这些修改")
        state, pending = checker.consume_confirmation("确认")
        self.assertEqual(state, "confirmed")
        self.assertEqual(pending["target"], "codex")


class HotkeyTests(unittest.TestCase):
    def test_f8_hotkey_parses(self) -> None:
        self.assertEqual(parse_hotkey("f8"), [{"f8"}])


class OutputCleanerTests(unittest.TestCase):
    def test_removes_ansi_and_mojibake_lines(self) -> None:
        text = "\x1b[31mOK\x1b[0m\n鑾峰彇乱码\nnormal line"
        self.assertEqual(clean_output(text), "OK\nnormal line")

    def test_spoken_summary_is_short(self) -> None:
        from agents.base import AgentResult
        from core.summarizer import Summarizer

        summarizer = Summarizer({"max_spoken_chars": 40, "max_spoken_sentences": 2})
        result = AgentResult("codex", True, raw_output="已修改两个文件。测试通过。C:/very/long/path should not be read.")
        spoken = summarizer.spoken_summary(result, "codex")
        self.assertIn("codex 已完成", spoken)
        self.assertLessEqual(len(spoken), 80)

    def test_spoken_summary_skips_model_time_and_tokens(self) -> None:
        from agents.base import AgentResult
        from core.summarizer import Summarizer

        summarizer = Summarizer({"max_spoken_chars": 80, "max_spoken_sentences": 2})
        result = AgentResult(
            "codex",
            True,
            raw_output="模型 gpt-5.4，耗时 12 秒，token 3000。已经修复登录按钮问题。测试通过。",
        )
        spoken = summarizer.spoken_summary(result, "codex")
        self.assertNotIn("模型", spoken)
        self.assertNotIn("token", spoken)
        self.assertNotIn("耗时", spoken)
        self.assertIn("登录按钮", spoken)


class StartupTests(unittest.TestCase):
    def test_controller_builds(self) -> None:
        config = load_config(ROOT / "config.yaml")
        controller = build_controller(config, ROOT)
        self.assertIn("codex", controller.agents)
        self.assertIn("claude", controller.agents)

    def test_tk_app_builds_and_destroys(self) -> None:
        config = load_config(ROOT / "config.yaml")
        app = VoiceRouterApp(config, ROOT)
        try:
            self.assertEqual(app.root.title(), "语音 Agent 路由器")
            self.assertIsNotNone(app.controller)
        finally:
            app.root.destroy()

    def test_desktop_app_files_exist(self) -> None:
        self.assertTrue((ROOT / "desktop_app.py").exists())
        self.assertTrue((ROOT / "start_app.vbs").exists())
        self.assertTrue((ROOT / "start_background.vbs").exists())
        self.assertTrue((ROOT / "background_voice_agent.py").exists())
        self.assertTrue((ROOT / "start_f8_voice_agent.vbs").exists())
        self.assertTrue((ROOT / "open_live_log.vbs").exists())
        self.assertTrue((ROOT / "watch_background_log.ps1").exists())
        self.assertTrue((ROOT / "log_overlay.py").exists())
        self.assertTrue((ROOT / "open_log_overlay.vbs").exists())
        self.assertTrue((ROOT / "install_startup.ps1").exists())
        self.assertTrue((ROOT / "uninstall_startup.ps1").exists())
        self.assertTrue((ROOT / "tools" / "check_model_cache.py").exists())
        self.assertTrue((ROOT / "tools" / "download_models.py").exists())
        self.assertTrue((ROOT / "tools" / "download_project_models.py").exists())
        self.assertTrue((ROOT / "tools" / "copy_cached_models_to_project.ps1").exists())
        self.assertTrue((ROOT / "tools" / "test_funasr_model.py").exists())
        self.assertTrue((ROOT / "MODELS.md").exists())

    def test_funasr_resolves_local_cache_when_present(self) -> None:
        from providers.stt_funasr import FunASRSTT

        config = load_config(ROOT / "config.yaml")["stt"]
        stt = FunASRSTT(config, ui=None)
        resolved = stt._resolve_model("paraformer-zh")
        self.assertTrue(resolved == "paraformer-zh" or "speech_seaco_paraformer" in resolved)

    def test_log_overlay_has_tray_support(self) -> None:
        source = (ROOT / "log_overlay.py").read_text(encoding="utf-8")
        self.assertIn("pystray.Icon", source)
        self.assertIn("WM_DELETE_WINDOW", source)
        self.assertIn("withdraw", source)
        self.assertIn("模型与参数", source)
        self.assertIn("save_and_restart", source)
        self.assertIn("batch_size_s", source)

    def test_background_agent_has_f7_cursor_mode(self) -> None:
        source = (ROOT / "background_voice_agent.py").read_text(encoding="utf-8")
        self.assertIn("toggle_cursor_dictation", source)
        self.assertIn("keyboard.Key.f7", source)
        self.assertIn("_stop_paste_and_send_at_cursor", source)
        self.assertIn("pyautogui.hotkey", source)
        self.assertIn("pyautogui.press", source)
        self.assertIn("shift_insert", source)
        self.assertIn("_cancel_current_task_locked", source)
        self.assertIn("_is_cancelled", source)

    def test_find_free_port_returns_int(self) -> None:
        self.assertIsInstance(find_free_port(0), int)

    def test_background_ui_writes_log(self) -> None:
        log_path = ROOT / "data" / "logs" / "test-background.log"
        if log_path.exists():
            log_path.unlink()
        ui = BackgroundUI(log_path)
        ui.status("ok")
        self.assertIn("ok", log_path.read_text(encoding="utf-8"))
        log_path.unlink()

    def test_background_ui_filters_noisy_status(self) -> None:
        log_path = ROOT / "data" / "logs" / "test-background-noisy.log"
        if log_path.exists():
            log_path.unlink()
        ui = BackgroundUI(log_path)
        ui.status("正在加载 Whisper 模型: base")
        self.assertFalse(log_path.exists())


class FakeAgent:
    def run(self, prompt: str, context: dict | None = None):
        from agents.base import AgentResult

        return AgentResult("fake", True, raw_output=f"收到: {prompt}")

    def run_stream(self, prompt: str, on_chunk, context: dict | None = None):
        from agents.base import AgentResult

        on_chunk("开始处理\n")
        on_chunk(f"收到: {prompt}\n")
        return AgentResult("fake", True, raw_output=f"开始处理\n收到: {prompt}")


class WebAppTests(unittest.TestCase):
    def test_web_asset_exists(self) -> None:
        html = ROOT / "web" / "index.html"
        self.assertTrue(html.exists())
        content = html.read_text(encoding="utf-8")
        self.assertIn("SpeechRecognition", content)
        self.assertIn("/api/run", content)
        self.assertIn("id=\"autoSend\" type=\"checkbox\" checked", content)
        self.assertIn("submitToAgent();", content)
        self.assertIn("clearOutputForNewRun", content)
        self.assertIn("&#24320;&#22987;", content)
        self.assertIn("&#20572;&#27490;&#21518;&#33258;&#21160;&#21457;&#36865;", content)

    def test_web_state_runs_fake_agent(self) -> None:
        config = load_config(ROOT / "config.yaml")
        state = WebAppState(config, ROOT, agents={"codex": FakeAgent(), "claude": FakeAgent()})
        result = state.handle_prompt("Codex 解释当前项目", "codex")
        self.assertTrue(result["ok"])
        self.assertEqual(result["kind"], "agent")
        self.assertIn("收到: 解释当前项目", result["raw_output"])
        self.assertIn("display_output", result)

    def test_web_state_submits_async_job(self) -> None:
        config = load_config(ROOT / "config.yaml")
        state = WebAppState(config, ROOT, agents={"codex": FakeAgent(), "claude": FakeAgent()})
        submitted = state.submit_prompt("Codex 解释当前项目", "auto")
        self.assertTrue(submitted["ok"])
        self.assertEqual(submitted["kind"], "job")
        self.assertEqual(submitted["target"], "codex")
        job_id = submitted["job_id"]

        for _ in range(20):
            job = state.get_job(job_id)
            if job["status"] == "done":
                break
            time.sleep(0.05)

        self.assertEqual(job["status"], "done")
        self.assertTrue(job["result"]["ok"])
        self.assertIn("收到: 解释当前项目", job["result"]["raw_output"])
        self.assertIn("开始处理", job["output"])

    def test_web_state_auto_route_preview(self) -> None:
        config = load_config(ROOT / "config.yaml")
        state = WebAppState(config, ROOT, agents={"codex": FakeAgent(), "claude": FakeAgent()})
        self.assertEqual(state.preview_route("总结当前方案", "auto")["target"], "claude")
        self.assertEqual(state.preview_route("实现这个功能", "auto")["target"], "codex")


if __name__ == "__main__":
    unittest.main()
