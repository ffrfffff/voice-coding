from __future__ import annotations

import re


ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MOJIBAKE_RE = re.compile(r"[锟�]{2,}|鑾|鈥|濮|粰|炴|€|�")


def clean_output(text: str, max_chars: int = 1600) -> str:
    text = ANSI_RE.sub("", text or "")
    text = CONTROL_RE.sub("", text)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _looks_noisy(stripped):
            continue
        lines.append(stripped)
        if sum(len(item) + 1 for item in lines) >= max_chars:
            break
    cleaned = "\n".join(lines).strip()
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + "\n..."
    return cleaned


def brief_output(summary: str, raw_output: str, error: str = "") -> str:
    parts = []
    if summary:
        parts.append(summary.strip())
    if error:
        parts.append(f"Error: {clean_output(error, 500)}")

    cleaned = clean_output(raw_output, 900)
    if cleaned and cleaned not in "\n".join(parts):
        parts.append(cleaned)

    return "\n\n".join(part for part in parts if part).strip()


def _looks_noisy(line: str) -> bool:
    if MOJIBAKE_RE.search(line):
        return True
    if len(line) > 220:
        return True
    lowered = line.lower()
    noisy_prefixes = (
        "debug:",
        "trace:",
        "warning:",
        "npm ",
        "node:",
        "internal/",
        "at ",
    )
    if lowered.startswith(noisy_prefixes):
        return True
    return False
