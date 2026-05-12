from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RouteDecision:
    kind: str
    target: str | None
    prompt: str
    reason: str


class Router:
    def __init__(self, config: dict, default_agent: str):
        self.config = config
        self.default_agent = default_agent if default_agent in {"claude", "codex"} else "codex"
        self.local_commands = config.get("local_commands", {})

    def route(self, text: str, fallback_agent: str | None) -> RouteDecision:
        normalized = text.strip()
        lowered = normalized.lower()

        for command_name, phrases in self.local_commands.items():
            if any(phrase and phrase in normalized for phrase in phrases):
                return RouteDecision("local", command_name, normalized, "local command")

        target = self._explicit_target(normalized, lowered)
        if target:
            prompt = self._strip_agent_prefix(normalized, target)
            return RouteDecision("agent", target, prompt, "explicit agent name")

        target = self._auto_target(normalized, lowered)
        if target:
            return RouteDecision("agent", target, normalized, "auto route")

        target = fallback_agent if fallback_agent in {"claude", "codex"} else self.default_agent
        return RouteDecision("agent", target, normalized, "fallback/default")

    def _explicit_target(self, text: str, lowered: str) -> str | None:
        if lowered.startswith(("claude", "\u514b\u52b3\u5fb7")) or "\u8ba9 claude" in lowered or "\u8ba9\u514b\u52b3\u5fb7" in text:
            return "claude"
        if lowered.startswith(("codex", "code x")) or text.startswith("\u4ee3\u7801\u52a9\u624b") or "\u8ba9 codex" in lowered:
            return "codex"
        return None

    def _strip_agent_prefix(self, text: str, target: str) -> str:
        prefixes = {
            "claude": ["Claude", "claude", "\u514b\u52b3\u5fb7"],
            "codex": ["Codex", "codex", "code x", "\u4ee3\u7801\u52a9\u624b"],
        }
        result = text
        for prefix in prefixes[target]:
            if result.startswith(prefix):
                result = result[len(prefix) :].lstrip(" \uff0c,\uff1a:")
                break
        return result or text

    def _auto_target(self, text: str, lowered: str) -> str | None:
        if not bool(self.config.get("allow_auto_route", False)):
            return None

        claude_keywords = [
            "\u89e3\u91ca",
            "\u5206\u6790",
            "\u603b\u7ed3",
            "\u65b9\u6848",
            "\u8bbe\u8ba1",
            "\u8bc4\u5ba1",
            "\u590d\u67e5",
            "\u6bd4\u8f83",
            "\u5224\u65ad",
            "\u5efa\u8bae",
            "\u4e3a\u4ec0\u4e48",
            "\u600e\u4e48\u7406\u89e3",
            "review",
            "explain",
            "summarize",
            "plan",
            "design",
        ]
        codex_keywords = [
            "\u5b9e\u73b0",
            "\u4fee\u590d",
            "\u4fee\u6539",
            "\u751f\u6210",
            "\u5199\u4ee3\u7801",
            "\u6539\u4ee3\u7801",
            "\u8fd0\u884c",
            "\u6d4b\u8bd5",
            "\u5b89\u88c5",
            "\u91cd\u6784",
            "\u521b\u5efa",
            "\u65b0\u589e",
            "\u5220\u9664",
            "\u63d0\u4ea4",
            "fix",
            "implement",
            "code",
            "test",
            "refactor",
        ]

        codex_score = sum(1 for keyword in codex_keywords if keyword in text or keyword in lowered)
        claude_score = sum(1 for keyword in claude_keywords if keyword in text or keyword in lowered)

        if codex_score > claude_score:
            return "codex"
        if claude_score > codex_score:
            return "claude"
        return None
