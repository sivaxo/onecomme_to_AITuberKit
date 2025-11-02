"""Application configuration loading utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List
import os

from dotenv import load_dotenv


BOOL_TRUE = {"1", "true", "yes", "on", "y"}
BOOL_FALSE = {"0", "false", "no", "off", "n"}


class ConfigError(RuntimeError):
    """Raised when configuration loading fails."""


@dataclass(slots=True)
class Config:
    """Strongly-typed configuration values for the integration service."""

    onecomme_ws_urls: List[str]
    onecomme_stream_ids: List[str]
    aituberkit_base_url: str
    aituberkit_client_id: str
    aituberkit_timeout: int
    use_aituberkit_system_prompt: bool

    max_queue_size: int
    allow_concurrent_response: bool

    trigger_words: List[str] = field(default_factory=list)

    greeting_first: str = "{username}さん、はじめまして！"
    greeting_return: str = "{username}さん、また来てくれてありがとう！"
    use_greeting: bool = True

    min_comment_length: int = 2
    ignore_patterns: List[str] = field(default_factory=list)
    positive_keywords: List[str] = field(default_factory=list)

    enable_llm_judge: bool = True
    llm_judge_cpu_threshold: int = 60

    max_cpu_usage: int = 80
    cpu_check_interval: int = 5

    log_level: str = "INFO"
    log_file: Path = Path("logs/system.log")
    stats_file: Path = Path("logs/stats.json")
    debug_mode: bool = False
    show_all_comments: bool = False

    @property
    def aituberkit_messages_url(self) -> str:
        return f"{self.aituberkit_base_url.rstrip('/')}/api/messages/"


def _str_to_bool(raw: str, *, var_name: str) -> bool:
    value = raw.strip().lower()
    if value in BOOL_TRUE:
        return True
    if value in BOOL_FALSE:
        return False
    raise ConfigError(f"Invalid boolean value '{raw}' for {var_name}")


def _split_csv(raw: str) -> List[str]:
    return [item.strip() for item in raw.split(',') if item.strip()]


def _get_required(env: dict[str, str | None], key: str) -> str:
    value = env.get(key)
    if not value:
        raise ConfigError(f"Missing required configuration value: {key}")
    return value


def load_config(env_file: str | None = None) -> Config:
    """Load configuration from environment and optional .env file."""

    if env_file is not None:
        load_dotenv(env_file, override=False)
    else:
        load_dotenv(override=False)

    env = os.environ

    def _split_any(raw: str) -> List[str]:
        raw = raw.replace("\n", ",")
        return _split_csv(raw)

    raw_onecomme_ws_url = (env.get("ONECOMME_WS_URL", "") or "").strip()
    stream_ids = _split_any(env.get("ONECOMME_STREAM_IDS", ""))
    additional_urls = _split_any(env.get("ONECOMME_WS_URLS", ""))

    onecomme_urls: List[str] = []

    if raw_onecomme_ws_url:
        if "{STREAM_ID}" in raw_onecomme_ws_url:
            if not stream_ids:
                raise ConfigError(
                    "ONECOMME_WS_URL に {STREAM_ID} プレースホルダが含まれていますが、"
                    "ONECOMME_STREAM_IDS が設定されていません"
                )
            for stream_id in stream_ids:
                onecomme_urls.append(raw_onecomme_ws_url.replace("{STREAM_ID}", stream_id))
        elif stream_ids:
            base = raw_onecomme_ws_url.rstrip('/')
            for stream_id in stream_ids:
                onecomme_urls.append(f"{base}/{stream_id}")
        else:
            onecomme_urls.append(raw_onecomme_ws_url)
    elif stream_ids and not additional_urls:
        raise ConfigError("ONECOMME_STREAM_IDS を使用する場合は ONECOMME_WS_URL も設定してください")

    onecomme_urls.extend(additional_urls)

    dedup_urls: List[str] = []
    seen = set()
    for url in onecomme_urls:
        if not url:
            continue
        if url not in seen:
            seen.add(url)
            dedup_urls.append(url)

    if not dedup_urls:
        raise ConfigError(
            "OneComme WebSocket URL が設定されていません。"
            "ONECOMME_WS_URL または ONECOMME_WS_URLS を指定してください。"
        )

    aituberkit_base_url = _get_required(env, "AITUBERKIT_BASE_URL")
    aituberkit_client_id = _get_required(env, "AITUBERKIT_CLIENT_ID")

    aituberkit_timeout = int(env.get("AITUBERKIT_TIMEOUT", 30))
    use_aituberkit_system_prompt = _str_to_bool(
        env.get("USE_AITUBERKIT_SYSTEM_PROMPT", "true"),
        var_name="USE_AITUBERKIT_SYSTEM_PROMPT",
    )

    max_queue_size = int(env.get("MAX_QUEUE_SIZE", 20))
    allow_concurrent_response = _str_to_bool(
        env.get("ALLOW_CONCURRENT_RESPONSE", "false"),
        var_name="ALLOW_CONCURRENT_RESPONSE",
    )

    trigger_words = _split_csv(env.get("TRIGGER_WORDS", ""))

    greeting_first = env.get("GREETING_FIRST", "{username}さん、はじめまして！")
    greeting_return = env.get("GREETING_RETURN", "{username}さん、また来てくれてありがとう！")
    use_greeting = _str_to_bool(
        env.get("USE_GREETING", "true"),
        var_name="USE_GREETING",
    )

    min_comment_length = int(env.get("MIN_COMMENT_LENGTH", 2))
    ignore_patterns = _split_csv(env.get("IGNORE_PATTERNS", ""))
    positive_keywords = _split_csv(env.get("POSITIVE_KEYWORDS", ""))

    enable_llm_judge = _str_to_bool(
        env.get("ENABLE_LLM_JUDGE", "true"),
        var_name="ENABLE_LLM_JUDGE",
    )
    llm_judge_cpu_threshold = int(env.get("LLM_JUDGE_CPU_THRESHOLD", 60))

    max_cpu_usage = int(env.get("MAX_CPU_USAGE", 80))
    cpu_check_interval = int(env.get("CPU_CHECK_INTERVAL", 5))

    log_level = env.get("LOG_LEVEL", "INFO").upper()
    log_file = Path(env.get("LOG_FILE", "logs/system.log"))
    stats_file = Path(env.get("STATS_FILE", "logs/stats.json"))
    debug_mode = _str_to_bool(
        env.get("DEBUG_MODE", "false"),
        var_name="DEBUG_MODE",
    )
    show_all_comments = _str_to_bool(
        env.get("SHOW_ALL_COMMENTS", "false"),
        var_name="SHOW_ALL_COMMENTS",
    )

    # Ensure directories exist
    log_file.parent.mkdir(parents=True, exist_ok=True)
    stats_file.parent.mkdir(parents=True, exist_ok=True)

    return Config(
        onecomme_ws_urls=dedup_urls,
        onecomme_stream_ids=stream_ids,
        aituberkit_base_url=aituberkit_base_url,
        aituberkit_client_id=aituberkit_client_id,
        aituberkit_timeout=aituberkit_timeout,
        use_aituberkit_system_prompt=use_aituberkit_system_prompt,
        max_queue_size=max_queue_size,
        allow_concurrent_response=allow_concurrent_response,
        trigger_words=trigger_words,
        greeting_first=greeting_first,
        greeting_return=greeting_return,
        use_greeting=use_greeting,
        min_comment_length=min_comment_length,
        ignore_patterns=ignore_patterns,
        positive_keywords=positive_keywords,
        enable_llm_judge=enable_llm_judge,
        llm_judge_cpu_threshold=llm_judge_cpu_threshold,
        max_cpu_usage=max_cpu_usage,
        cpu_check_interval=cpu_check_interval,
        log_level=log_level,
        log_file=log_file,
        stats_file=stats_file,
        debug_mode=debug_mode,
        show_all_comments=show_all_comments,
    )
