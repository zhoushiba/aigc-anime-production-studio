"""AIGC 生成任务执行器。

真实的异步执行：线程池消费任务 → 调用 Provider 生成图片 → 落盘 → 建素材 → 回写任务。
状态机：queued → running → succeeded / failed / timeout / canceled（终态不可回退）。
"""

from __future__ import annotations

import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import session_scope
from app.errors import ConflictError, NotFoundError
from app.models import (
    Asset,
    GenerationTask,
    PromptHistory,
    Series,
    StoryboardShot,
    utcnow,
)
from app.services.image_utils import save_asset_image
from app.services.providers import (
    GenerationRequest,
    GenerationResult,
    ProviderError,
    ProviderNotConfigured,
    ProviderTimeout,
    get_provider,
)

logger = logging.getLogger("app.generation")

TERMINAL_STATUSES = {"succeeded", "failed", "timeout", "canceled"}


def resolve_size(db: Session, task: GenerationTask) -> tuple[int, int]:
    """画布尺寸：优先任务参数，其次剧集横竖屏，最后默认竖屏。"""
    params = task.params_json or {}
    width, height = params.get("width"), params.get("height")
    if isinstance(width, int) and isinstance(height, int) and width >= 64 and height >= 64:
        return width, height
    if task.series_id:
        series = db.get(Series, task.series_id)
        if series is not None and series.platform == "horizontal":
            return settings.horizontal_size
    return settings.vertical_size


def _asset_kind(kind: str) -> str:
    return "image" if kind == "text2image" else "animation"


class GenerationRunner:
    """生成任务线程池。"""

    def __init__(self) -> None:
        self._pool: ThreadPoolExecutor | None = None
        self._lock = threading.Lock()
        self.inflight: set[int] = set()

    def start(self, workers: int | None = None) -> None:
        with self._lock:
            if self._pool is None:
                self._pool = ThreadPoolExecutor(
                    max_workers=max(1, workers or settings.generation_workers),
                    thread_name_prefix="aigc-gen",
                )

    def shutdown(self) -> None:
        with self._lock:
            pool, self._pool = self._pool, None
        if pool is not None:
            pool.shutdown(wait=False, cancel_futures=True)

    def submit(self, task_id: int) -> None:
        self.start()
        assert self._pool is not None
        self.inflight.add(task_id)
        self._pool.submit(self._run_guarded, task_id)

    def _run_guarded(self, task_id: int) -> None:
        try:
            self.run(task_id)
        except Exception:  # pragma: no cover - 兜底日志
            logger.exception("生成任务 %s 执行异常", task_id)
        finally:
            self.inflight.discard(task_id)

    # ---------- 单个任务的执行 ----------
    def run(self, task_id: int) -> None:
        payload = self._begin(task_id)
        if payload is None:
            return
        started = time.perf_counter()
        try:
            provider = get_provider(payload["provider"])
            request = GenerationRequest(
                prompt=payload["prompt"],
                negative_prompt=payload["negative_prompt"],
                seed=payload["seed"],
                size=payload["size"],
                params={**payload["params"], "kind": payload["kind"]},
                shot_label=payload["shot_label"],
                style_label=payload["style_label"],
            )
            result = provider.generate(request)
        except ProviderTimeout as exc:
            self._finish(task_id, "timeout", str(exc))
            return
        except (ProviderNotConfigured, ProviderError) as exc:
            self._finish(task_id, "failed", str(exc))
            return

        duration_ms = int((time.perf_counter() - started) * 1000)
        deadline_ms = settings.generation_deadline_seconds * 1000
        if duration_ms > deadline_ms:  # 真实耗时超限
            self._finish(task_id, "timeout", f"生成耗时 {duration_ms}ms，超过截止时间 {deadline_ms}ms")
            return

        saved = self._store(task_id, result)
        self._persist(task_id, payload, result, saved, duration_ms)

    def _begin(self, task_id: int) -> dict | None:
        with session_scope() as db:
            task = db.get(GenerationTask, task_id)
            if task is None:
                logger.warning("生成任务 %s 不存在", task_id)
                return None
            if task.status in TERMINAL_STATUSES:
                return None
            if task.canceled:
                task.status = "canceled"
                task.error = "任务在开始前被取消"
                task.finished_at = utcnow()
                return None
            task.status = "running"
            task.progress = 15
            task.started_at = utcnow()
            task.error = ""
            payload = {
                "prompt": task.prompt,
                "negative_prompt": task.negative_prompt,
                "seed": task.seed or task.id,
                "kind": task.kind,
                "provider": task.provider,
                "params": dict(task.params_json or {}),
                "series_id": task.series_id,
                "episode_id": task.episode_id,
                "shot_id": task.shot_id,
                "character_id": getattr(task, "character_id", None) or (task.params_json or {}).get("character_id"),
                "scene_card_id": getattr(task, "scene_card_id", None) or (task.params_json or {}).get("scene_card_id"),
                "size": resolve_size(db, task),
                "shot_label": "",
                "style_label": "",
            }
            if task.shot_id:
                shot = db.get(StoryboardShot, task.shot_id)
                if shot is not None:
                    payload["shot_label"] = f"{shot.shot_no} {shot.shot_size}/{shot.camera_angle}/{shot.camera_move}"
            if task.series_id:
                series = db.get(Series, task.series_id)
                if series is not None:
                    payload["style_label"] = series.style
            return payload

    def _store(self, task_id: int, result: GenerationResult) -> dict:
        directory = settings.assets_dir / datetime.utcnow().strftime("%Y%m%d")
        return save_asset_image(
            result.image,
            directory=directory,
            thumbs_dir=settings.thumbs_dir,
            stem=f"task{task_id}",
            thumb_width=settings.thumb_width,
        )

    def _relative(self, path) -> str:
        try:
            return path.relative_to(settings.storage_dir).as_posix()
        except ValueError:
            return path.name

    def _finish(self, task_id: int, status: str, error: str) -> None:
        with session_scope() as db:
            task = db.get(GenerationTask, task_id)
            if task is None:
                return
            task.status = status
            task.error = error[:1000]
            task.finished_at = utcnow()
            if task.started_at is not None:
                task.duration_ms = int((task.finished_at - task.started_at).total_seconds() * 1000)
            logger.info("生成任务 %s 结束：%s", task_id, status)

    def _persist(
        self,
        task_id: int,
        payload: dict,
        result: GenerationResult,
        saved: dict,
        duration_ms: int,
    ) -> None:
        with session_scope() as db:
            task = db.get(GenerationTask, task_id)
            if task is None:
                return
            title = f"{payload['shot_label'] or '素材'} · #{task.id}"
            asset = Asset(
                series_id=task.series_id,
                episode_id=task.episode_id,
                shot_id=task.shot_id,
                character_id=payload.get("character_id"),
                scene_card_id=payload.get("scene_card_id"),
                task_id=task.id,
                kind=_asset_kind(task.kind),
                title=title,
                file_path=self._relative(saved["path"]),
                thumb_path=self._relative(saved["thumb_path"]),
                width=int(saved["width"]),
                height=int(saved["height"]),
                file_size=int(saved["file_size"]),
                seed=payload["seed"],
                prompt=task.prompt,
                negative_prompt=task.negative_prompt,
                provider=task.provider,
                status="candidate",
                meta_json={**result.meta, "duration_ms": duration_ms, "task_no": task.id},
            )
            db.add(asset)
            db.flush()
            task.asset_id = asset.id
            task.status = "succeeded"
            task.progress = 100
            task.finished_at = utcnow()
            task.duration_ms = duration_ms
            task.error = ""
            if task.shot_id:
                shot = db.get(StoryboardShot, task.shot_id)
                if shot is not None:
                    shot.asset_id = asset.id
                    shot.status = "generated"
            if task.series_id:
                series = db.get(Series, task.series_id)
                if series is not None and not series.cover_asset_id:
                    series.cover_asset_id = asset.id
            logger.info("生成任务 %s 成功，素材 #%s，耗时 %sms", task_id, asset.id, duration_ms)

    def warmup(self) -> dict:
        """服务重启后把残留的 running 任务标记为失败（进程已丢）。"""
        with session_scope() as db:
            stuck = db.scalars(select(GenerationTask).where(GenerationTask.status.in_(["queued", "running"]))).all()
            for task in stuck:
                if task.status == "running":
                    task.status = "failed"
                    task.error = "服务重启，任务中断，请重试"
                    task.finished_at = utcnow()
            return {"interrupted": len(stuck)}


runner = GenerationRunner()


# ---------------- 业务服务函数 ----------------
def create_task(db: Session, payload, user) -> GenerationTask:
    """创建生成任务：入库 → 记提示词历史 → 提交线程池（或同步执行）。"""
    provider_name = (payload.provider or settings.default_provider or "mock").lower()
    if payload.series_id is not None and db.get(Series, payload.series_id) is None:
        raise NotFoundError("剧集不存在")
    if payload.shot_id is not None and db.get(StoryboardShot, payload.shot_id) is None:
        raise NotFoundError("分镜不存在")

    seed = payload.seed if payload.seed is not None else random.randint(1, 2**31 - 1)
    task = GenerationTask(
        series_id=payload.series_id,
        episode_id=payload.episode_id,
        shot_id=payload.shot_id,
        kind=payload.kind,
        provider=provider_name,
        prompt=payload.prompt,
        negative_prompt=payload.negative_prompt,
        params_json=dict(payload.params or {}),
        status="queued",
        progress=0,
        seed=seed,
        created_by=user.username,
    )
    db.add(task)
    db.flush()
    db.add(
        PromptHistory(
            series_id=payload.series_id,
            shot_id=payload.shot_id,
            task_id=task.id,
            kind=payload.kind,
            prompt=payload.prompt,
            negative_prompt=payload.negative_prompt,
            params_json=dict(payload.params or {}),
            created_by=user.username,
        )
    )
    db.commit()
    db.refresh(task)

    if settings.generation_inline:
        runner.run(task.id)
        db.expire_all()
        task = db.get(GenerationTask, task.id)
    else:
        runner.submit(task.id)
    return task


def retry_task(db: Session, task: GenerationTask, payload, user) -> GenerationTask:
    """重跑：复制参数生成新任务（保留原任务作为历史记录）。"""
    from app.schemas import TaskCreate

    new_payload = TaskCreate(
        prompt=payload.prompt or task.prompt if payload else task.prompt,
        negative_prompt=(payload.negative_prompt if payload and payload.negative_prompt is not None else task.negative_prompt),
        kind=task.kind,
        provider=task.provider,
        series_id=task.series_id,
        episode_id=task.episode_id,
        shot_id=task.shot_id,
        character_id=task.character_id if hasattr(task, "character_id") else (task.params_json or {}).get("character_id"),
        scene_card_id=task.scene_card_id if hasattr(task, "scene_card_id") else (task.params_json or {}).get("scene_card_id"),
        seed=None,
        params={**(task.params_json or {}), **((payload.params if payload else None) or {})},
    )
    return create_task(db, new_payload, user)


def cancel_task(db: Session, task: GenerationTask) -> GenerationTask:
    if task.status in TERMINAL_STATUSES:
        raise ConflictError("任务已结束，无法取消")
    if task.status == "running":
        raise ConflictError("任务正在生成中，无法取消")
    task.canceled = True
    task.status = "canceled"
    task.error = "已取消"
    task.finished_at = utcnow()
    db.commit()
    db.refresh(task)
    return task


def task_stats(db: Session) -> dict:
    rows = db.execute(select(GenerationTask.status, func.count()).group_by(GenerationTask.status)).all()
    counts = {status: count for status, count in rows}
    total = sum(counts.values())
    succeeded = counts.get("succeeded", 0)
    failed = counts.get("failed", 0)
    timeout = counts.get("timeout", 0)
    finished = succeeded + failed + timeout
    avg = db.scalar(
        select(func.avg(GenerationTask.duration_ms)).where(GenerationTask.status == "succeeded")
    )
    return {
        "total": total,
        "by_status": counts,
        "succeeded": succeeded,
        "failed": failed,
        "timeout": timeout,
        "running": counts.get("running", 0),
        "queued": counts.get("queued", 0),
        "success_rate": round(succeeded / finished * 100, 2) if finished else 0.0,
        "avg_duration_ms": int(avg or 0),
    }
