"""统一响应体与统一异常处理。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("app.error")


class AppError(Exception):
    """业务异常基类：code 为业务错误码，status_code 为 HTTP 状态码。"""

    def __init__(self, message: str, code: int = 40000, status_code: int = 400, details: Any | None = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在", code: int = 40400):
        super().__init__(message, code, 404)


class ConflictError(AppError):
    def __init__(self, message: str = "资源冲突", code: int = 40900):
        super().__init__(message, code, 409)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "未登录或登录已过期", code: int = 40100):
        super().__init__(message, code, 401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "没有权限执行该操作", code: int = 40300):
        super().__init__(message, code, 403)


def envelope(data: Any = None, message: str = "ok", code: int = 0, request_id: str = "-") -> dict[str, Any]:
    """统一成功响应体。"""
    return {"code": code, "message": message, "data": data, "request_id": request_id}


def ok(data: Any = None, message: str = "ok") -> dict[str, Any]:
    """路由层快捷返回（request_id 由中间件补全到日志与响应头）。"""
    return envelope(data, message)


def error_body(message: str, code: int, request_id: str = "-", details: Any | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message, "data": None, "request_id": request_id}
    if details is not None:
        body["details"] = details
    return body


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:  # noqa: ANN202
        if exc.status_code >= 500:
            logger.error("业务异常 %s: %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.message, exc.code, _rid(request), exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:  # noqa: ANN202
        details = [
            {
                "field": ".".join(str(part) for part in item.get("loc", []) if part not in ("body", "query", "path")),
                "message": item.get("msg", "参数不合法"),
            }
            for item in exc.errors()
        ]
        return JSONResponse(status_code=422, content=error_body("请求参数校验失败", 42200, _rid(request), details))

    @app.exception_handler(SQLAlchemyError)
    async def _sqlalchemy_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:  # noqa: ANN202
        logger.exception("数据库异常: %s", exc)
        return JSONResponse(status_code=500, content=error_body("数据库操作失败", 50001, _rid(request)))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:  # noqa: ANN202
        logger.exception("未捕获异常: %s", exc)
        return JSONResponse(status_code=500, content=error_body("服务器内部错误", 50000, _rid(request)))
