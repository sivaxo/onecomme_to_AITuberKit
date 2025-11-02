"""OneComme WebSocket client implementation."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable

import websockets
from websockets import WebSocketClientProtocol

from .config import Config

CommentHandler = Callable[[dict], Awaitable[None]]


class OneCommeClient:
    """Manage subscription to OneComme WebSocket stream."""

    def __init__(self, config: Config) -> None:
        if not config.onecomme_ws_urls:
            raise ValueError("OneComme WebSocket URL is not configured")
        self._config = config
        self._urls = config.onecomme_ws_urls
        self._logger = logging.getLogger(__name__)
        self._stop_event = asyncio.Event()

    async def stop(self) -> None:
        self._stop_event.set()

    async def listen(self, handler: CommentHandler) -> None:
        tasks = [
            asyncio.create_task(
                self._connection_loop(url, handler),
                name=f"onecomme-{idx}"
            )
            for idx, url in enumerate(self._urls)
        ]
        try:
            await self._stop_event.wait()
        finally:
            self._stop_event.set()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _connection_loop(self, url: str, handler: CommentHandler) -> None:
        backoff = 1.0
        max_backoff = 30.0
        while not self._stop_event.is_set():
            try:
                # OneCommeへの接続と同時に購読メッセージを送信するよう修正
                async with websockets.connect(url) as websocket:
                    self._logger.info("OneComme connected: %s", url)

                    # 【重要】接続完了直後にわずかな遅延を追加し、サーバーが切断するのを防ぐ
                    await asyncio.sleep(0.1) 

                    # 接続直後に購読メッセージを即座に送信
                    subscribe_message = {
                        "type": "subscribe",
                        "targets": ["comment"]
                    }
                    await websocket.send(json.dumps(subscribe_message))
                    self._logger.debug("Sent subscribe message: %s", subscribe_message)
                    
                    backoff = 1.0
                    await self._consume(websocket, handler, url)
                
            except asyncio.CancelledError:
                break
            except Exception as exc:
                if self._stop_event.is_set():
                    break
                self._logger.warning("OneComme connection error (%s): %s", url, exc, exc_info=True)
                self._logger.info("Retrying %s in %.1f seconds", url, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
        self._logger.debug("Stopped OneComme listener for %s", url)

    async def _consume(self, websocket: WebSocketClientProtocol, handler: CommentHandler, url: str) -> None:
        async for raw_message in websocket:
            if self._stop_event.is_set():
                break
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                self._logger.debug("Ignoring non-JSON message from %s: %s", url, raw_message)
                continue

            if self._config.debug_mode:
                self._logger.debug("[%s] Received raw payload: %s", url, message)

            if message.get("type") != "comment":
                continue

            comment_data = message.get("data", {})
            if self._config.show_all_comments:
                self._logger.info("[COMMENT][%s] %s", url, comment_data)

            await handler(comment_data)