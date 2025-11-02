"""System monitoring utilities."""
from __future__ import annotations

import asyncio
import logging

import psutil

from .config import Config
from .logger import StatsManager


class CpuMonitor:
    """Periodically sample CPU load for decision making."""

    def __init__(self, config: Config, stats_manager: StatsManager) -> None:
        self._config = config
        self._stats_manager = stats_manager
        self._logger = logging.getLogger(__name__)
        self._latest_usage: float = 0.0
        self._stop_event = asyncio.Event()
        psutil.cpu_percent(interval=None)  # Prime measurement baseline

    async def run(self) -> None:
        """Continuously sample CPU usage."""
        interval = max(1, self._config.cpu_check_interval)
        while not self._stop_event.is_set():
            usage = psutil.cpu_percent(interval=None)
            self._latest_usage = usage
            self._stats_manager.record_cpu(int(usage))
            if usage >= self._config.max_cpu_usage:
                self._logger.warning("High CPU usage detected: %.1f%%", usage)
            await asyncio.sleep(interval)

    def latest_usage(self) -> int:
        return int(self._latest_usage)

    async def wait_for_relief(self) -> None:
        """Wait until CPU usage drops below configured limit."""
        while self.latest_usage() >= self._config.max_cpu_usage:
            self._logger.info(
                "CPU usage %.1f%% >= threshold %d%%, waiting...",
                self._latest_usage,
                self._config.max_cpu_usage,
            )
            await asyncio.sleep(2)

    def stop(self) -> None:
        self._stop_event.set()
