"""Logging and statistics utilities."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import coloredlogs

from .config import Config


LOG_FORMAT = "[%(asctime)s][%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class Stats:
    """In-memory statistics tracking structure."""

    session_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_received: int = 0
    total_responded: int = 0
    total_skipped: int = 0
    trigger_word_detections: int = 0
    first_time_users: int = 0
    unique_users: set[str] = field(default_factory=set)
    skip_reasons: Dict[str, int] = field(default_factory=dict)
    response_times: list[float] = field(default_factory=list)
    cpu_observations: list[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        duration = datetime.now(timezone.utc) - self.session_start
        response_rate = (
            self.total_responded / self.total_received
            if self.total_received
            else 0.0
        )
        return {
            "session_start": self.session_start.isoformat(),
            "session_duration_seconds": int(duration.total_seconds()),
            "total_received": self.total_received,
            "total_responded": self.total_responded,
            "total_skipped": self.total_skipped,
            "response_rate": round(response_rate, 4),
            "trigger_word_detections": self.trigger_word_detections,
            "first_time_users": self.first_time_users,
            "unique_users": len(self.unique_users),
            "skip_reasons": self.skip_reasons,
            "avg_response_time": round(sum(self.response_times) / len(self.response_times), 3)
            if self.response_times
            else 0.0,
            "min_response_time": round(min(self.response_times), 3)
            if self.response_times
            else 0.0,
            "max_response_time": round(max(self.response_times), 3)
            if self.response_times
            else 0.0,
            "cpu_stats": {
                "avg": int(sum(self.cpu_observations) / len(self.cpu_observations))
                if self.cpu_observations
                else 0,
                "max": max(self.cpu_observations) if self.cpu_observations else 0,
                "high_load_events": sum(1 for value in self.cpu_observations if value >= 80),
            },
        }


class StatsManager:
    """Manage statistics lifecycle and persistence."""

    def __init__(self, stats_path: Path) -> None:
        self._stats_path = stats_path
        self._stats_path.parent.mkdir(parents=True, exist_ok=True)
        self._stats = Stats()
        self._persist()

    @property
    def stats(self) -> Stats:
        return self._stats

    def record_received(self, user_id: str, *, is_first_time: bool, has_trigger: bool) -> None:
        self._stats.total_received += 1
        if user_id:
            self._stats.unique_users.add(user_id)
        if is_first_time:
            self._stats.first_time_users += 1
        if has_trigger:
            self._stats.trigger_word_detections += 1
        self._persist()

    def record_response(self, elapsed_seconds: float) -> None:
        self._stats.total_responded += 1
        self._stats.response_times.append(elapsed_seconds)
        self._persist()

    def record_skip(self, reason: str) -> None:
        self._stats.total_skipped += 1
        self._stats.skip_reasons[reason] = self._stats.skip_reasons.get(reason, 0) + 1
        self._persist()

    def record_cpu(self, usage_percent: int) -> None:
        self._stats.cpu_observations.append(int(usage_percent))
        self._persist()

    def _persist(self) -> None:
        try:
            self._stats_path.write_text(
                json.dumps(self._stats.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:  # pragma: no cover - we do not want to crash on IO issues
            logging.getLogger(__name__).exception("Failed to persist stats data")


def setup_logging(config: Config) -> logging.Logger:
    """Configure root logger according to config."""

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicate logs
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    config.log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(file_handler)

    coloredlogs.install(
        level=config.log_level,
        fmt=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        logger=logger,
    )

    return logger
