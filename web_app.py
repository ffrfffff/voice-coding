from __future__ import annotations

import argparse
import json
import threading
import time
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from core.config import load_config
from core.factory import build_agents, build_risk_checker, build_router, build_summarizer
from core.output_cleaner import brief_output, clean_output


class WebAppState:
    def __init__(self, config: dict, project_dir: Path, agents: dict | None = None):
        self.config = config
        self.project_dir = project_dir
        self.router = build_router(config)
        self.risk_checker = build_risk_checker(config)
        self.summarizer = build_summarizer(config)
        self.jobs: dict[str, dict[str, Any]] = {}
        self.jobs_lock = threading.Lock()
        self.agents = agents or build_agents(config, project_dir)

    def submit_prompt(self, text: str, fallback_agent: str) -> dict[str, Any]:
        job_id = uuid.uuid4().hex
        preview = self.preview_route(text, fallback_agent)
        with self.jobs_lock:
            self.jobs[job_id] = {
                "id": job_id,
                "status": "queued",
                "created_at": time.time(),
                "updated_at": time.time(),
                "target": preview.get("target", fallback_agent),
                "text": text,
                "result": None,
                "output": "",
            }

        thread = threading.Thread(target=self._run_job, args=(job_id, text, fallback_agent), daemon=True)
        thread.start()
        return {
            "ok": True,
            "kind": "job",
            "job_id": job_id,
            "status": "queued",
            "target": preview.get("target", fallback_agent),
            "route_reason": preview.get("reason", ""),
            "message": "已发送给后台 Agent。",
        }

    def preview_route(self, text: str, fallback_agent: str) -> dict[str, Any]:
        fallback = None if fallback_agent == "auto" else fallback_agent
        decision = self.router.route(text.strip(), fallback)
        return {"kind": decision.kind, "target": decision.target, "reason": decision.reason}

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self.jobs_lock:
            job = self.jobs.get(job_id)
            if not job:
                return {"ok": False, "kind": "missing", "message": "任务不存在或已过期。"}
            snapshot = dict(job)
            if snapshot.get("output"):
                snapshot["display_output"] = clean_output(snapshot["output"], 1600)
            return snapshot

    def _run_job(self, job_id: str, text: str, fallback_agent: str) -> None:
        self._update_job(job_id, status="running")
        result = self.handle_prompt(text, fallback_agent, job_id=job_id)
        self._update_job(job_id, status="done", result=result, target=result.get("target", fallback_agent))

    def _update_job(self, job_id: str, **updates: Any) -> None:
        with self.jobs_lock:
            job = self.jobs.get(job_id)
            if not job:
                return
            job.update(updates)
            job["updated_at"] = time.time()

    def _append_job_output(self, job_id: str, chunk: str) -> None:
        with self.jobs_lock:
            job = self.jobs.get(job_id)
            if not job:
                return
            job["output"] = (job.get("output") or "") + chunk
            job["updated_at"] = time.time()

    def handle_prompt(self, text: str, fallback_agent: str, job_id: str | None = None) -> dict[str, Any]:
        text = text.strip()
        if not text:
            return {"ok": False, "kind": "empty", "message": "没有可发送的文本。"}

        confirmation_state, pending = self.risk_checker.consume_confirmation(text)
        if confirmation_state == "confirmed" and pending:
            return self._run_agent(pending["target"], pending["prompt"], job_id=job_id)
        if confirmation_state == "rejected":
            return {"ok": True, "kind": "cancelled", "message": "已取消待确认任务。"}
        if confirmation_state == "waiting":
            return {"ok": False, "kind": "waiting", "message": "请说或输入“确认”继续，或“取消”放弃。"}

        fallback = None if fallback_agent == "auto" else fallback_agent
        decision = self.router.route(text, fallback)
        if decision.kind == "local":
            return {"ok": True, "kind": "local", "target": decision.target, "message": f"本地命令已处理: {decision.target}"}

        if self.risk_checker.needs_confirmation(decision.prompt):
            self.risk_checker.hold(decision.target, decision.prompt)
            return {
                "ok": False,
                "kind": "confirm_required",
                "target": decision.target,
                "message": f"识别到高风险操作，目标是 {decision.target}。请再次输入“确认”继续，或输入“取消”放弃。",
            }

        return self._run_agent(decision.target, decision.prompt, job_id=job_id)

    def _run_agent(self, target: str, prompt: str, job_id: str | None = None) -> dict[str, Any]:
        agent = self.agents.get(target)
        if not agent:
            return {"ok": False, "kind": "error", "message": f"未知 Agent: {target}"}

        if job_id and hasattr(agent, "run_stream"):
            result = agent.run_stream(prompt, lambda chunk: self._append_job_output(job_id, chunk), context={})
        else:
            result = agent.run(prompt, context={})
        result.summary = self.summarizer.summarize(result)
        return {
            "ok": result.success,
            "kind": "agent",
            "target": target,
            "prompt": prompt,
            "summary": result.summary,
            "display_output": brief_output(result.summary, result.raw_output, result.error),
            "raw_output": clean_output(result.raw_output, 3000),
            "error": clean_output(result.error, 800),
            "metadata": result.metadata,
        }


class VoiceWebHandler(SimpleHTTPRequestHandler):
    state: WebAppState
    web_dir: Path

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.web_dir), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/":
            self.path = "/index.html"
        if self.path == "/api/config":
            self._send_json(
                {
                    "default_agent": self.state.config.get("agents", {}).get("default", "codex"),
                    "agents": ["codex", "claude"],
                    "auto_route": bool(self.state.config.get("routing", {}).get("allow_auto_route", False)),
                }
            )
            return
        if self.path.startswith("/api/jobs/"):
            job_id = self.path.rsplit("/", 1)[-1]
            self._send_json(self.state.get_job(job_id))
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/run":
            self.send_error(404, "Not found")
            return

        try:
            data = self._read_json()
            text = str(data.get("text", ""))
            target = str(data.get("target", self.state.config.get("agents", {}).get("default", "codex")))
            self._send_json(self.state.submit_prompt(text, target))
        except Exception as exc:
            self._send_json({"ok": False, "kind": "error", "message": str(exc)}, status=500)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        return json.loads(payload or "{}")

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def make_handler(state: WebAppState, web_dir: Path):
    class Handler(VoiceWebHandler):
        pass

    Handler.state = state
    Handler.web_dir = web_dir
    return Handler


def build_server(config: dict, project_dir: Path, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    state = WebAppState(config, project_dir)
    handler = make_handler(state, project_dir / "web")
    return ThreadingHTTPServer((host, port), handler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Realtime browser dictation UI for the voice agent router.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    project_dir = Path.cwd()
    config = load_config(project_dir / args.config)
    server = build_server(config, project_dir, args.host, args.port)
    print(f"实时听写界面已启动: http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
