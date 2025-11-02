"""Prompt generation helpers."""
from __future__ import annotations

from .config import Config


def build_prompt(comment_data: dict, config: Config) -> str:
    """Construct prompt string for AITuberKit."""

    username = comment_data.get("name") or comment_data.get("userid") or "視聴者"
    comment_text = comment_data.get("comment", "")
    is_first_time = bool(comment_data.get("isFirstTime", False))

    lines: list[str] = ["[conversation_history]", ""]

    if config.use_greeting:
        if is_first_time:
            lines.append(config.greeting_first.format(username=username))
        else:
            lines.append(config.greeting_return.format(username=username))
        lines.append("")

    lines.append(f"{username}さんのコメント: {comment_text}")
    return "\n".join(lines)
