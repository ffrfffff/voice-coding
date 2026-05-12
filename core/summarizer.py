from __future__ import annotations

import re

from agents.base import AgentResult
from core.output_cleaner import clean_output


class Summarizer:
    def __init__(self, config: dict):
        self.max_sentences = int(config.get("max_spoken_sentences", 3))
        self.max_spoken_chars = int(config.get("max_spoken_chars", 140))

    def summarize(self, result: AgentResult) -> str:
        if not result.success:
            detail = result.error or "\u6267\u884c\u5931\u8d25"
            return f"{result.agent_name} \u6267\u884c\u5931\u8d25\u3002{detail}"

        cleaned = self._remove_noisy_blocks(result.raw_output)
        sentences = self._split_sentences(cleaned)
        if not sentences:
            return f"{result.agent_name} \u5df2\u5b8c\u6210\uff0c\u4f46\u6ca1\u6709\u8fd4\u56de\u53ef\u64ad\u62a5\u7684\u6458\u8981\u3002"

        summary = "\u3002".join(sentences[: self.max_sentences]).strip("\u3002")
        return f"{result.agent_name} \u5df2\u5b8c\u6210\u3002{summary}\u3002"

    def spoken_summary(self, result: AgentResult, target: str | None = None) -> str:
        name = target or result.agent_name
        if not result.success:
            detail = clean_output(result.error or result.raw_output, 80)
            if detail:
                return f"{name} \u6267\u884c\u5931\u8d25\u3002{detail}"
            return f"{name} \u6267\u884c\u5931\u8d25\u3002\u8bf7\u67e5\u770b\u65e5\u5fd7\u3002"

        cleaned = self._remove_noisy_blocks(result.raw_output)
        sentences = self._split_sentences(cleaned)
        useful = []
        for sentence in sentences:
            if self._skip_spoken_sentence(sentence):
                continue
            useful.append(sentence)
            if len(useful) >= 2:
                break

        if not useful:
            return f"{name} \u5df2\u5b8c\u6210\u3002"

        body = "\u3002".join(useful).strip("\u3002")
        if len(body) > self.max_spoken_chars:
            body = body[: self.max_spoken_chars].rstrip() + "\u3002\u8be6\u60c5\u770b\u65e5\u5fd7"
        return f"{name} \u5df2\u5b8c\u6210\u3002{body}\u3002"

    def _remove_noisy_blocks(self, text: str) -> str:
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        text = re.sub(r"(?m)^diff --git .*$.*?(?=^\S|\Z)", "", text)
        text = re.sub(r"(?m)^[+\-]{3} .*$", "", text)
        text = re.sub(r"(?m)^@@ .*$", "", text)
        text = clean_output(text, 1600)
        lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if len(stripped) > 180:
                continue
            if stripped.startswith(("+", "-", "Traceback", 'File "')):
                continue
            lines.append(stripped)
        return " ".join(lines)

    def _split_sentences(self, text: str) -> list[str]:
        parts = re.split(r"[\u3002\uff01\uff1f!?\n]+", text)
        return [part.strip() for part in parts if part.strip()]

    def _skip_spoken_sentence(self, sentence: str) -> bool:
        lowered = sentence.lower()
        noisy = [
            "warning",
            "debug",
            "traceback",
            "stdout",
            "stderr",
            "tokens",
            "token",
            "command",
            "npm",
            "python",
            "powershell",
            "http://",
            "https://",
            "model",
            "gpt",
            "claude",
            "codex",
            "whisper",
            "ms",
            "sec",
            "seconds",
            "elapsed",
            "duration",
            "latency",
            "cached",
            "input",
            "output",
            "thinking",
            "reasoning",
            "stream",
            "pid",
            "process",
            "\u6a21\u578b",
            "\u8017\u65f6",
            "\u79d2",
            "\u6beb\u79d2",
            "\u65f6\u95f4",
            "\u547d\u4ee4",
            "\u8fdb\u7a0b",
            "\u8f93\u5165",
            "\u8f93\u51fa",
            "\u7f13\u5b58",
            "\u63a8\u7406",
        ]
        if any(item in lowered for item in noisy):
            return True
        if re.search(r"\b\d{1,2}:\d{2}(:\d{2})?\b", sentence):
            return True
        if re.search(r"\b\d+(\.\d+)?\s*(ms|s|sec|seconds|tokens?)\b", lowered):
            return True
        if re.search(r"\b(gpt|claude|codex|whisper)[\w.\-]*\b", lowered):
            return True
        if "\\" in sentence or "/" in sentence:
            return True
        if len(sentence) < 3:
            return True
        return False
