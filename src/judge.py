"""Comment prioritisation and AI judgement logic."""
from __future__ import annotations

from typing import Optional, Tuple

from .config import Config


def detect_trigger(comment_text: str, config: Config) -> bool:
    lowered = comment_text.lower()
    return any(trigger.lower() in lowered for trigger in config.trigger_words)


def calculate_priority(comment_data: dict, config: Config) -> Tuple[int, bool]:
    """Determine priority value and whether trigger matched."""

    comment_text = comment_data.get("comment", "") or ""
    is_first_time = bool(comment_data.get("isFirstTime", False))
    has_trigger = detect_trigger(comment_text, config)

    if has_trigger or is_first_time:
        return 0, has_trigger
    return 3, has_trigger


def stage_b_judge(comment_text: str, config: Config) -> Tuple[Optional[bool], str]:
    """Cheap heuristics to filter comments before LLM usage."""

    normalized = comment_text.strip()

    if len(normalized) < config.min_comment_length:
        return False, "too_short"

    for pattern in config.ignore_patterns:
        if pattern and pattern in normalized:
            return False, "ignore_pattern"

    for keyword in config.positive_keywords:
        if keyword and keyword in normalized:
            return True, "positive_keyword"

    if len(normalized) < 5:
        first_char = normalized[0]
        if normalized.count(first_char) >= int(len(normalized) * 0.7):
            return False, "repetitive"

    return None, "need_llm_judge"


async def stage_a_judge(
    comment_text: str,
    *,
    config: Config,
    cpu_usage: int,
    aituberkit_client,
) -> Tuple[bool, str]:
    """High-cost LLM judgement stage."""

    if not config.enable_llm_judge:
        return False, "llm_disabled"

    if cpu_usage > config.llm_judge_cpu_threshold:
        return False, "skip_high_cpu_load"

    prompt = (
        "以下のコメントに返答すべきか判断してください。\n"
        f"コメント: {comment_text}\n"
        "判断基準:\n"
        "- 質問、感想、呼びかけ → YES\n"
        "- 意味のない文字列、スパム → NO\n"
        "- 短い相槌（「草」「www」など） → NO\n"
        "YESまたはNOのみで答えてください。"
    )

    try:
        response_text = await aituberkit_client.classify(prompt)
    except Exception as exc:  # pragma: no cover
        return False, f"llm_error:{exc}"

    decision = "YES" in response_text.upper()
    return decision, "llm_judged"


async def should_respond(
    comment_data: dict,
    *,
    config: Config,
    cpu_usage: int,
    aituberkit_client,
) -> Tuple[bool, str]:
    """Combined Stage B + Stage A pipeline."""

    comment_text = comment_data.get("comment", "") or ""
    primary_result, reason = stage_b_judge(comment_text, config)
    if primary_result is not None:
        return primary_result, reason

    return await stage_a_judge(
        comment_text,
        config=config,
        cpu_usage=cpu_usage,
        aituberkit_client=aituberkit_client,
    )
