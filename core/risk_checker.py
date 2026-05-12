from __future__ import annotations


class RiskChecker:
    def __init__(self, safety_config: dict, routing_config: dict):
        self.enabled = bool(safety_config.get("require_confirmation", True))
        self.keywords = [item for item in safety_config.get("confirm_keywords", []) if item]
        commands = routing_config.get("local_commands", {})
        self.confirm_phrases = commands.get("confirm", ["确认", "继续"])
        self.reject_phrases = commands.get("reject", ["取消", "放弃", "不要"])
        self.pending: dict | None = None

    def needs_confirmation(self, text: str) -> bool:
        return self.enabled and any(keyword in text for keyword in self.keywords)

    def hold(self, target: str, prompt: str) -> None:
        self.pending = {"target": target, "prompt": prompt}

    def consume_confirmation(self, text: str) -> tuple[str, dict | None]:
        if not self.pending:
            return "none", None
        if any(phrase in text for phrase in self.confirm_phrases):
            pending = self.pending
            self.pending = None
            return "confirmed", pending
        if any(phrase in text for phrase in self.reject_phrases):
            self.pending = None
            return "rejected", None
        return "waiting", None
