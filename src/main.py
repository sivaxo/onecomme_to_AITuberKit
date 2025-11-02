from __future__ import annotations

import asyncio
import logging
import signal
import sys
import uuid
from typing import List

from .aituberkit_client import AITuberKitClient
from .config import Config, ConfigError, load_config
from .judge import calculate_priority, should_respond
from .logger import StatsManager, setup_logging
from .monitor import CpuMonitor
from .onecomme_client import OneCommeClient
from .prompt_builder import build_prompt
from .queue_manager import QueueItem, QueueManager


logger = logging.getLogger(__name__)


async def process_queue(
    config: Config,
    queue: QueueManager,
    aituberkit: AITuberKitClient,
    cpu_monitor: CpuMonitor,
    stats: StatsManager,
) -> None:
    """Continuously process queued comments."""

    while True:
        item = await queue.dequeue()
        if item is None:
            await asyncio.sleep(0.1)
            continue

        await cpu_monitor.wait_for_relief()

        prompt = build_prompt(item.comment_data, config)
        logger.info(
            "Processing comment %s with priority %d", item.comment_id, item.priority
        )
        try:
            response_text, elapsed = await aituberkit.send_prompt(prompt)
            stats.record_response(elapsed)
            logger.info(
                "Response completed in %.2fs for %s", elapsed, item.comment_id
            )
            if config.debug_mode:
                logger.debug("AITuberKit response: %s", response_text)
        except Exception as exc:
            stats.record_skip("api_error")
            logger.error("AITuberKit API error for %s: %s", item.comment_id, exc, exc_info=True)
        finally:
            await queue.mark_idle()


async def handle_comment(
    comment_data: dict,
    *,
    config: Config,
    stats: StatsManager,
    queue: QueueManager,
    aituberkit: AITuberKitClient,
    cpu_monitor: CpuMonitor,
) -> None:
    """Pipeline for each incoming comment."""

    comment_id = comment_data.get("id") or str(uuid.uuid4())
    comment_text = comment_data.get("comment", "")

    priority, has_trigger = calculate_priority(comment_data, config)
    stats.record_received(
        comment_data.get("userid", ""),
        is_first_time=bool(comment_data.get("isFirstTime", False)),
        has_trigger=has_trigger,
    )

    logger.info(
        "Comment received (%s) priority=%d text=%s",
        comment_id,
        priority,
        comment_text,
    )

    should_process = priority == 0
    skip_reason = "priority_filter"

    if not should_process:
        cpu_usage = cpu_monitor.latest_usage()
        decision, reason = await should_respond(
            comment_data,
            config=config,
            cpu_usage=cpu_usage,
            aituberkit_client=aituberkit,
        )
        should_process = decision
        skip_reason = reason

    if not should_process:
        stats.record_skip(skip_reason)
        logger.info("Skipping comment %s (reason=%s)", comment_id, skip_reason)
        return

    queue_item = QueueItem(priority=priority, comment_id=comment_id, comment_data=comment_data)
    evicted = await queue.enqueue(queue_item)
    if evicted:
        stats.record_skip("queue_full")
        logger.warning("Queue full. Dropped comment %s (priority %d)", evicted.comment_id, evicted.priority)
    else:
        queue_size = await queue.size()
        logger.info("Queued comment %s (queue_size=%d)", comment_id, queue_size)


async def main_async() -> None:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"設定エラー: {exc}", file=sys.stderr)
        raise SystemExit(1)

    setup_logging(config)

    logger.info("Configured OneComme endpoints (%d): %s", len(config.onecomme_ws_urls), ", ".join(config.onecomme_ws_urls))

    stats = StatsManager(config.stats_file)
    queue = QueueManager(config.max_queue_size, config.allow_concurrent_response)
    aituberkit = AITuberKitClient(config)
    cpu_monitor = CpuMonitor(config, stats)
    onecomme = OneCommeClient(config)

    if not await aituberkit.health_check():
        logger.warning("AITuberKit health check was not successful. Continuing anyway.")

    async def comment_handler(comment: dict) -> None:
        await handle_comment(
            comment,
            config=config,
            stats=stats,
            queue=queue,
            aituberkit=aituberkit,
            cpu_monitor=cpu_monitor,
        )

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Shutdown signal received")
        stop_event.set()

    signal_supported = True
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except (NotImplementedError, RuntimeError):
            signal_supported = False
            break

    if not signal_supported:
        logger.debug("Signal handlers are not supported on this platform. Use Ctrl+C or close the window to stop.")

    tasks: List[asyncio.Task] = [
        asyncio.create_task(cpu_monitor.run(), name="cpu-monitor"),
        asyncio.create_task(process_queue(config, queue, aituberkit, cpu_monitor, stats), name="queue-processor"),
        asyncio.create_task(onecomme.listen(comment_handler), name="onecomme-listener"),
    ]

    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user interrupt")
        stop_event.set()
    finally:
        logger.info("Shutting down tasks...")
        cpu_monitor.stop()
        await onecomme.stop()

        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
