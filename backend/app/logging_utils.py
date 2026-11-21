"""结构化日志与请求链路 ID。

每个请求生成 / 透传 ``X-Request-Id``，写入日志字段与响应头，便于前后端联查问题。
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Awaitable, Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """当前上下文的请求 ID（无则返回 ``-``）。"""
    return request_id_var.get()


class JsonFormatter(logging.Formatter):
    """把日志记录序列化为单行 JSON，便于采集（ELK / Loki）。"""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", None) or get_request_id(),
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # 清空 uvicorn 默认 handler，统一格式
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    logging.getLogger("uvicorn.access").disabled = True


class RequestContextMiddleware:
    """纯 ASGI 中间件：注入 request_id、记录访问日志与耗时响应头。

    采用纯 ASGI 实现而非 ``BaseHTTPMiddleware``，可以保证未捕获异常（500）
    的响应头与日志里同样带有 request_id。
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = logging.getLogger("app.access")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        request_id = headers.get("x-request-id") or uuid.uuid4().hex[:16]
        scope["request_id"] = request_id
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_holder = {"status": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                elapsed = int((time.perf_counter() - started) * 1000)
                raw_headers: list[tuple[bytes, bytes]] = list(message.get("headers") or [])
                raw_headers.append((b"x-request-id", request_id.encode("latin-1")))
                raw_headers.append((b"x-response-time-ms", str(elapsed).encode("latin-1")))
                message = {**message, "headers": raw_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            self.logger.info(
                "%s %s -> %s",
                scope.get("method", "-"),
                scope.get("path", "-"),
                status_holder["status"],
                extra={"extra_fields": {"status": status_holder["status"], "duration_ms": elapsed_ms}},
            )
            request_id_var.reset(token)


AccessLogMiddleware = RequestContextMiddleware  # 兼容旧命名

__all__ = [
    "AccessLogMiddleware",
    "JsonFormatter",
    "RequestContextMiddleware",
    "configure_logging",
    "get_request_id",
    "request_id_var",
    "Awaitable",
    "Callable",
]
