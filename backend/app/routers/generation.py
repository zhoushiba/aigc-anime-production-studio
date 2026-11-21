"""AIGC 生成任务路由：提交 / 轮询 / 重试 / 取消 / 统计。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app import serializers
from app.crud import get_task, list_tasks
from app.crud.common import page_result, paginate
from app.deps import CurrentUser, DbSession
from app.errors import ok
from app.schemas import TaskCreate, TaskRetry
from app.services import generation
from app.services.providers import list_providers

router = APIRouter(prefix="/generation", tags=["AIGC 生成"])


@router.get("/providers", summary="可用生成服务商（mock / comfyui / openai）")
def providers() -> dict:
    return ok({"items": list_providers()})


@router.post("/tasks", summary="提交生成任务（文生图 / 图生视频）")
def create_task(payload: TaskCreate, db: DbSession, user: CurrentUser) -> dict:
    task = generation.create_task(db, payload, user)
    return ok(serializers.task(db, task), "任务已提交")


@router.get("/tasks", summary="生成任务列表（可按状态 / 项目 / 分镜过滤）")
def list_tasks_api(
    db: DbSession,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str = "",
    series_id: int | None = None,
    episode_id: int | None = None,
    shot_id: int | None = None,
    kind: str = "",
) -> dict:
    stmt = list_tasks(
        db, status=status, series_id=series_id, episode_id=episode_id, shot_id=shot_id, kind=kind
    )
    rows, total = paginate(db, stmt, page, size)
    return ok(page_result([serializers.task(db, row) for row in rows], total, page, size))


@router.get("/tasks/{task_id}", summary="任务详情（含结果素材，供轮询）")
def task_detail(task_id: int, db: DbSession) -> dict:
    task = get_task(db, task_id)
    data = serializers.task(db, task)
    data["finished"] = task.status in generation.TERMINAL_STATUSES
    return ok(data)


@router.post("/tasks/{task_id}/retry", summary="重跑任务（可覆盖 prompt / 参数）")
def retry_task(task_id: int, db: DbSession, user: CurrentUser, payload: TaskRetry | None = None) -> dict:
    task = get_task(db, task_id)
    new_task = generation.retry_task(db, task, payload, user)
    return ok(serializers.task(db, new_task), "已重新提交")


@router.post("/tasks/{task_id}/cancel", summary="取消排队中的任务")
def cancel_task(task_id: int, db: DbSession) -> dict:
    task = get_task(db, task_id)
    task = generation.cancel_task(db, task)
    return ok(serializers.task(db, task), "任务已取消")


@router.get("/stats", summary="生成统计：成功率 / 平均耗时 / 状态分布")
def stats(db: DbSession) -> dict:
    return ok(generation.task_stats(db))
