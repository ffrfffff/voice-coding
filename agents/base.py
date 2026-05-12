from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import subprocess
from typing import Any
from typing import Callable


@dataclass
class AgentResult:
    agent_name: str
    success: bool
    raw_output: str = ""
    summary: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent:
    name = "base"

    def __init__(self, config: dict, global_config: dict, project_dir: Path):
        self.config = config
        self.global_config = global_config
        self.project_dir = project_dir

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("enabled", True))

    def command(self) -> list[str]:
        command = self.config.get("command", self.name)
        args = self.config.get("args", [])
        return [command, *args]

    def run(self, prompt: str, context: dict | None = None) -> AgentResult:
        if not self.enabled:
            return AgentResult(self.name, False, error=f"{self.name} is disabled in config.yaml")

        timeout = int(self.global_config.get("timeout_seconds", 900))
        cmd = self.command()
        try:
            completed = subprocess.run(
                [*cmd, prompt],
                cwd=self.project_dir,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=timeout,
            )
        except FileNotFoundError:
            return AgentResult(self.name, False, error=f"Command not found: {cmd[0]}")
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or "") + ("\n" + exc.stderr if exc.stderr else "")
            return AgentResult(self.name, False, raw_output=output, error=f"Timed out after {timeout}s")

        raw_output = completed.stdout.strip()
        if completed.stderr.strip():
            raw_output = f"{raw_output}\n\n[stderr]\n{completed.stderr.strip()}".strip()

        return AgentResult(
            agent_name=self.name,
            success=completed.returncode == 0,
            raw_output=raw_output,
            error="" if completed.returncode == 0 else f"Exited with code {completed.returncode}",
            metadata={"command": " ".join(cmd), "returncode": completed.returncode},
        )

    def run_stream(self, prompt: str, on_chunk: Callable[[str], None], context: dict | None = None) -> AgentResult:
        if not self.enabled:
            return AgentResult(self.name, False, error=f"{self.name} is disabled in config.yaml")

        timeout = int(self.global_config.get("timeout_seconds", 900))
        cmd = self.command()
        try:
            process = subprocess.Popen(
                [*cmd, prompt],
                cwd=self.project_dir,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
            )
        except FileNotFoundError:
            return AgentResult(self.name, False, error=f"Command not found: {cmd[0]}")

        chunks: list[str] = []
        try:
            assert process.stdout is not None
            for line in process.stdout:
                chunks.append(line)
                on_chunk(line)
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            return AgentResult(self.name, False, raw_output="".join(chunks), error=f"Timed out after {timeout}s")

        raw_output = "".join(chunks).strip()
        return AgentResult(
            agent_name=self.name,
            success=returncode == 0,
            raw_output=raw_output,
            error="" if returncode == 0 else f"Exited with code {returncode}",
            metadata={"command": " ".join(cmd), "returncode": returncode},
        )
