"""数据看板：生成成功率 / 平均耗时 / 素材数 / 项目进度 / 近 7 日趋势。"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app import serializers
from app.deps import DbSession, DbSession as _DbSession  # noqa: F401  (兼容旧引用)
from app.errors import ok
from app.models import (
    Asset,
    Character,
    Episode,
    GenerationTask,
    Review,
    Series,
    StoryboardShot,
    Timeline,
    User,
)
from app.services import generation

router = APIRouter(prefix="/dashboard", tags=["数据看板"])


@router.get("/overview", summary="看板总览")
def overview(db: DbSession) -> dict:
    series_rows = list(db.scalars(select(Series)).all())
    episode_total = int(db.scalar(select(func.count()).select_from(Episode)) or 0)
    shot_total = int(db.scalar(select(func.count()).select_from(StoryboardShot)) or 0)
    character_total = int(db.scalar(select(func.count()).select_from(Character)) or 0)
    user_total = int(db.scalar(select(func.count()).select_from(User)) or 0)
    timeline_total = int(db.scalar(select(func.count()).select_from(Timeline)) or 0)
    pending_reviews = int(
        db.scalar(select(func.count()).select_from(Review).where(Review.status == "pending")) or 0
    )
    approved_reviews = int(
        db.scalar(select(func.count()).select_from(Review).where(Review.status == "approved")) or 0
    )

    tasks = generation.task_stats(db)
    assets = __import__("app.crud", fromlist=["asset_stats"]).asset_stats(db)

    recent_tasks = [
        serializers.task(db, item)
        for item in db.scalars(select(GenerationTask).order_by(GenerationTask.id.desc()).limit(6)).all()
    ]
    recent_assets = [
        serializers.asset(db, item)
        for item in db.scalars(select(Asset).order_by(Asset.id.desc()).limit(6)).all()
    ]

    series_progress = []
    for series in series_rows[:12]:
        episodes = list(db.scalars(select(Episode).where(Episode.series_id == series.id)).all())
        done = sum(1 for item in episodes if item.status in ("approved", "delivered"))
        planned = series.episodes_planned or 1
        series_progress.append(
            {
                "id": series.id,
                "title": series.title,
                "status": series.status,
                "status_label": serializers.series(db, series, with_stats=False)["status_label"],
                "episode_count": len(episodes),
                "episodes_done": done,
                "episodes_planned": planned,
                "progress": round(done / planned * 100, 1) if planned else 0.0,
                "cover_url": serializers.series(db, series, with_stats=False)["cover_url"],
            }
        )

    return ok(
        {
            "series_total": len(series_rows),
            "series_in_production": sum(1 for item in series_rows if item.status == "in_production"),
            "episode_total": episode_total,
            "shot_total": shot_total,
            "character_total": character_total,
            "user_total": user_total,
            "timeline_total": timeline_total,
            "pending_reviews": pending_reviews,
            "approved_reviews": approved_reviews,
            "tasks": tasks,
            "assets": assets,
            "series_progress": series_progress,
            "recent_tasks": recent_tasks,
            "recent_assets": recent_assets,
        }
    )


@router.get("/trend", summary="近 N 日生成任务趋势（按天聚合）")
def trend(db: DbSession, days: int = Query(7, ge=1, le=30)) -> dict:
    start = datetime.utcnow() - timedelta(days=days - 1)
    rows = list(
        db.execute(
            select(GenerationTask.created_at, GenerationTask.status, GenerationTask.duration_ms).where(
                GenerationTask.created_at >= start
            )
        ).all()
    )
    buckets: dict[str, dict[str, float]] = defaultdict(lambda: {"total": 0, "succeeded": 0, "failed": 0, "duration_ms": 0})
    for created_at, status, duration_ms in rows:
        key = created_at.strftime("%Y-%m-%d") if created_at else ""
        if not key:
            continue
        bucket = buckets[key]
        bucket["total"] += 1
        if status == "succeeded":
            bucket["succeeded"] += 1
        elif status in ("failed", "timeout"):
            bucket["failed"] += 1
        bucket["duration_ms"] += duration_ms or 0

    items = []
    for offset in range(days - 1, -1, -1):
        day = (datetime.utcnow() - timedelta(days=offset)).strftime("%Y-%m-%d")
        bucket = buckets.get(day, {"total": 0, "succeeded": 0, "failed": 0, "duration_ms": 0})
        total = int(bucket["total"])
        items.append(
            {
                "date": day,
                "total": total,
                "succeeded": int(bucket["succeeded"]),
                "failed": int(bucket["failed"]),
                "success_rate": round(bucket["succeeded"] / total * 100, 1) if total else 0.0,
                "avg_duration_ms": round(bucket["duration_ms"] / total) if total else 0,
            }
        )
    return ok({"items": items, "days": days})
