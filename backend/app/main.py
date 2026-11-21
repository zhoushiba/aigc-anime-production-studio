"""FastAPI 应用入口：中间件、异常处理、路由挂载、启动钩子。"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import PROJECT_DIR, settings
from app.database import init_db
from app.deps import get_current_user
from app.errors import ok, register_exception_handlers
from app.routers import assets, auth, composition, dashboard, generation, meta, reviews, series, storyboard
from app.services import generation as generation_service
from app.services.providers import list_providers
from app.services.seed import seed_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("app")

SEED_INFO: dict = {}


class RequestIdMiddleware(BaseHTTPMiddleware):
    """为每个请求生成 request_id，写进日志与响应头，便于问题排查。"""

    async def dispatch(self, request: Request, call_next):  # noqa: ANN001, ANN201
        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings.ensure_dirs()
    init_db()
    try:
        SEED_INFO.update(seed_all())
    except Exception as exc:  # 种子失败不能阻塞服务启动
        logger.warning("示例数据初始化失败（可忽略）：%s", exc)
    generation_service.runner.start(settings.generation_workers)
    interrupted = generation_service.runner.warmup()
    logger.info("AIGC 生成执行器已启动，workers=%s，残留任务回收=%s", settings.generation_workers, interrupted)
    yield
    generation_service.runner.shutdown()
    logger.info("AIGC 生成执行器已停止")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AIGC 动漫番剧制作工作台：项目策划 → 剧本 → 分镜 → 角色/场景一致性 → AIGC 生成 → "
        "素材二次优化 → 合成单导出 → 审核流 → 数据看板。"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id"],
)
register_exception_handlers(app)

for module in (series, storyboard, generation, assets, composition, reviews, dashboard):
    # 业务接口统一要求登录（JWT），元数据接口保持公开供登录页与下拉框使用
    app.include_router(module.router, prefix=settings.api_prefix, dependencies=[Depends(get_current_user)])
app.include_router(meta.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)

settings.ensure_dirs()
app.mount("/media", StaticFiles(directory=str(settings.storage_dir)), name="media")


@app.get("/health", tags=["系统"], summary="健康检查")
def health() -> dict:
    return ok(
        {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
            "database": settings.database_url.split("///")[-1],
            "seed": SEED_INFO,
            "providers": list_providers(),
        }
    )


def _index_payload() -> dict:
    return ok(
        {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "api_prefix": settings.api_prefix,
            "demo_account": {"username": settings.demo_username, "password": settings.demo_password},
        }
    )


# 构建过前端时，单端口即可演示（hash 路由无需回退配置）：
# 先把服务信息挂到 /api/info，再把 "/" 让给前端静态站点。
_DIST = Path(PROJECT_DIR) / "frontend" / "dist"
if _DIST.exists():
    app.get(f"{settings.api_prefix}/info", tags=["系统"], summary="服务信息")(_index_payload)
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="spa")
else:
    app.get("/", tags=["系统"], summary="服务信息")(_index_payload)
