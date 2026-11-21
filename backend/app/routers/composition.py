"""成片合成单 / 时间轴 / 导出 / 质检清单 路由。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy import delete, select

from app import serializers
from app.config import settings
from app.constants import QUALITY_ITEMS
from app.crud import get_episode, get_shot, shots_of
from app.deps import CurrentUser, DbSession
from app.errors import NotFoundError, ok
from app.models import Asset, ExportJob, QualityChecklist, StoryboardShot, Timeline, TimelineItem
from app.schemas import ChecklistUpdate, ExportRequest, MoveRequest, TimelineCreate, TimelineItemUpdate
from app.services import export_service

router = APIRouter(tags=["成片合成单"])

_MIME_EXT = {"csv": "csv", "json": "json", "srt": "srt", "zip": "zip"}


def _get_timeline(db: DbSession, episode_id: int) -> Timeline | None:
    return db.scalar(select(Timeline).where(Timeline.episode_id == episode_id))


def _ordered_items(db: DbSession, timeline: Timeline) -> list[TimelineItem]:
    return list(
        db.scalars(select(TimelineItem).where(TimelineItem.timeline_id == timeline.id).order_by(TimelineItem.seq)).all()
    )


def _rebuild(db: DbSession, timeline: Timeline) -> list[TimelineItem]:
    """按分镜顺序重建合成单（自动带入每个镜头的入选素材）。"""
    db.execute(delete(TimelineItem).where(TimelineItem.timeline_id == timeline.id))
    items: list[TimelineItem] = []
    for seq, shot in enumerate(shots_of(db, timeline.episode_id), start=1):
        item = TimelineItem(
            timeline_id=timeline.id,
            shot_id=shot.id,
            asset_id=shot.asset_id,
            seq=seq,
            duration_seconds=shot.duration_seconds,
            subtitle=shot.dialogue,
            transition="cut",
            audio_note=shot.bgm,
        )
        db.add(item)
        items.append(item)
    timeline.total_duration = round(sum(float(item.duration_seconds or 0) for item in items), 2)
    return items


def _export_items(db: DbSession, timeline: Timeline) -> list[dict]:
    payload: list[dict] = []
    for item in _ordered_items(db, timeline):
        shot = db.get(StoryboardShot, item.shot_id) if item.shot_id else None
        asset = db.get(Asset, item.asset_id) if item.asset_id else None
        payload.append(
            {
                "seq": item.seq,
                "shot_no": shot.shot_no if shot is not None else "",
                "shot_size": shot.shot_size if shot is not None else "",
                "camera_angle": shot.camera_angle if shot is not None else "",
                "camera_move": shot.camera_move if shot is not None else "",
                "duration_seconds": item.duration_seconds,
                "description": shot.description if shot is not None else "",
                "subtitle": item.subtitle,
                "transition": item.transition,
                "audio_note": item.audio_note,
                "file_path": asset.file_path if asset is not None else "",
            }
        )
    return payload


def _timeline_payload(db: DbSession, timeline: Timeline) -> dict:
    items = _ordered_items(db, timeline)
    serialized = [serializers.timeline_item(db, item) for item in items]
    return {
        "timeline": {
            "id": timeline.id,
            "episode_id": timeline.episode_id,
            "name": timeline.name,
            "total_duration": timeline.total_duration,
            "status": timeline.status,
            "created_at": serializers.iso(timeline.created_at),
            "updated_at": serializers.iso(timeline.updated_at),
        },
        "items": serialized,
        "summary": {
            "shot_count": len(items),
            "total_duration": round(sum(float(item.duration_seconds or 0) for item in items), 2),
            "with_asset": sum(1 for item in items if item.asset_id),
            "subtitle_count": sum(1 for item in items if (item.subtitle or "").strip()),
        },
    }


@router.get("/episodes/{episode_id}/timeline", summary="成片合成单（不存在则按分镜自动生成）")
def get_timeline(episode_id: int, db: DbSession) -> dict:
    episode = get_episode(db, episode_id)
    timeline = _get_timeline(db, episode.id)
    if timeline is None:
        timeline = Timeline(episode_id=episode.id, name=f"第 {episode.number} 集 · 成片合成单", status="draft")
        db.add(timeline)
        db.flush()
        _rebuild(db, timeline)
        db.commit()
        db.refresh(timeline)
    return ok(_timeline_payload(db, timeline))


@router.put("/episodes/{episode_id}/timeline", summary="创建 / 重命名合成单，可自动按分镜填充")
def save_timeline(episode_id: int, payload: TimelineCreate, db: DbSession) -> dict:
    episode = get_episode(db, episode_id)
    timeline = _get_timeline(db, episode.id)
    if timeline is None:
        timeline = Timeline(episode_id=episode.id, name=payload.name, status="draft")
        db.add(timeline)
        db.flush()
    else:
        timeline.name = payload.name or timeline.name
    if payload.auto_fill:
        _rebuild(db, timeline)
    db.commit()
    db.refresh(timeline)
    return ok(_timeline_payload(db, timeline), "合成单已保存")


@router.post("/episodes/{episode_id}/timeline/auto-fill", summary="按分镜顺序重新填充合成单")
def auto_fill(episode_id: int, db: DbSession) -> dict:
    episode = get_episode(db, episode_id)
    timeline = _get_timeline(db, episode.id)
    if timeline is None:
        timeline = Timeline(episode_id=episode.id, name=f"第 {episode.number} 集 · 成片合成单", status="draft")
        db.add(timeline)
        db.flush()
    _rebuild(db, timeline)
    db.commit()
    db.refresh(timeline)
    return ok(_timeline_payload(db, timeline), "已按分镜重新填充")


@router.patch("/timeline-items/{item_id}", summary="调整镜头时长 / 字幕 / 转场 / 音效 / 素材")
def update_item(item_id: int, payload: TimelineItemUpdate, db: DbSession) -> dict:
    item = db.get(TimelineItem, item_id)
    if item is None:
        raise NotFoundError("合成单条目不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(item, field, value)
    timeline = db.get(Timeline, item.timeline_id)
    if timeline is not None:
        timeline.total_duration = round(
            sum(float(row.duration_seconds or 0) for row in _ordered_items(db, timeline)), 2
        )
    db.commit()
    db.refresh(item)
    return ok(serializers.timeline_item(db, item), "已保存")


@router.post("/timeline-items/{item_id}/move", summary="合成单条目上移 / 下移")
def move_item(item_id: int, payload: MoveRequest, db: DbSession) -> dict:
    item = db.get(TimelineItem, item_id)
    if item is None:
        raise NotFoundError("合成单条目不存在")
    items = _ordered_items(db, db.get(Timeline, item.timeline_id))
    index = next((i for i, row in enumerate(items) if row.id == item.id), None)
    if index is None:
        raise NotFoundError("合成单条目不存在")
    target = index - 1 if payload.direction == "up" else index + 1
    if target < 0 or target >= len(items):
        return ok({"items": [serializers.timeline_item(db, row) for row in items]}, "已到边界")
    items[index], items[target] = items[target], items[index]
    for position, row in enumerate(items, start=1):
        row.seq = position
    db.commit()
    return ok({"items": [serializers.timeline_item(db, row) for row in items]}, "顺序已更新")


@router.delete("/timeline-items/{item_id}", summary="从合成单移除镜头")
def delete_item(item_id: int, db: DbSession) -> dict:
    item = db.get(TimelineItem, item_id)
    if item is None:
        raise NotFoundError("合成单条目不存在")
    db.delete(item)
    db.commit()
    return ok({"deleted": item_id}, "已移除")


# ---------------- 导出 ----------------
@router.get("/episodes/{episode_id}/export", summary="直接下载合成单（csv / json / srt / zip）")
def export_now(episode_id: int, db: DbSession, format: str = Query("csv", pattern="^(csv|json|srt|zip)$")) -> Response:
    episode = get_episode(db, episode_id)
    timeline = _get_timeline(db, episode.id)
    if timeline is None:
        raise NotFoundError("合成单不存在，请先生成合成单")
    meta = {
        "episode": episode.title,
        "number": episode.number,
        "timeline": timeline.name,
        "total_duration": timeline.total_duration,
        "shot_count": len(_ordered_items(db, timeline)),
        "exported_by": settings.app_name,
    }
    content, fmt, mime, _payload = export_service.build_export(_export_items(db, timeline), fmt=format, meta=meta)
    filename = f"episode-{episode.number}-timeline.{_MIME_EXT[fmt]}"
    return Response(
        content=content,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/episodes/{episode_id}/exports", summary="生成导出文件并登记导出记录")
def create_export(episode_id: int, payload: ExportRequest, db: DbSession, user: CurrentUser) -> dict:
    episode = get_episode(db, episode_id)
    timeline = _get_timeline(db, episode.id)
    if timeline is None:
        raise NotFoundError("合成单不存在，请先生成合成单")
    meta = {
        "episode": episode.title,
        "number": episode.number,
        "timeline": timeline.name,
        "total_duration": timeline.total_duration,
        "exported_by": user.username,
    }
    content, fmt, _mime, summary = export_service.build_export(_export_items(db, timeline), fmt=payload.format, meta=meta)
    settings.ensure_dirs()
    path = Path(settings.exports_dir) / f"episode-{episode.number}-timeline.{_MIME_EXT[fmt]}"
    path.write_bytes(content)
    job = ExportJob(
        episode_id=episode.id,
        timeline_id=timeline.id,
        format=fmt,
        file_path=f"exports/{path.name}",
        status="done",
        payload_json=summary,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return ok(
        {
            "id": job.id,
            "format": job.format,
            "file_path": job.file_path,
            "download_url": f"{settings.api_prefix}/exports/{job.id}/download",
            "payload": summary,
            "created_at": serializers.iso(job.created_at),
        },
        "导出完成",
    )


@router.get("/exports/{job_id}/download", summary="下载已生成的导出文件")
def download_export(job_id: int, db: DbSession) -> FileResponse:
    job = db.get(ExportJob, job_id)
    if job is None:
        raise NotFoundError("导出记录不存在")
    path = Path(settings.storage_dir) / job.file_path
    if not path.exists():
        raise NotFoundError("导出文件已被清理，请重新导出")
    return FileResponse(path, filename=path.name)


# ---------------- 质检清单 ----------------
def _ensure_checklist(db: DbSession, episode_id: int) -> list[QualityChecklist]:
    items = list(
        db.scalars(
            select(QualityChecklist).where(QualityChecklist.episode_id == episode_id).order_by(QualityChecklist.id)
        ).all()
    )
    if items:
        return items
    for entry in QUALITY_ITEMS:
        db.add(
            QualityChecklist(
                episode_id=episode_id, item_key=entry["key"], label=entry["label"], checked=False
            )
        )
    db.commit()
    return list(
        db.scalars(
            select(QualityChecklist).where(QualityChecklist.episode_id == episode_id).order_by(QualityChecklist.id)
        ).all()
    )


@router.get("/episodes/{episode_id}/checklist", summary="交付前质量检查清单")
def get_checklist(episode_id: int, db: DbSession) -> dict:
    episode = get_episode(db, episode_id)
    items = _ensure_checklist(db, episode.id)
    checked = sum(1 for item in items if item.checked)
    return ok(
        {
            "items": [serializers.checklist(item) for item in items],
            "total": len(items),
            "checked": checked,
            "progress": round(checked / len(items) * 100, 1) if items else 0.0,
        }
    )


@router.patch("/checklist/{item_id}", summary="勾选 / 取消质检项并填写备注")
def update_checklist(item_id: int, payload: ChecklistUpdate, db: DbSession, user: CurrentUser) -> dict:
    item = db.get(QualityChecklist, item_id)
    if item is None:
        raise NotFoundError("质检项不存在")
    item.checked = payload.checked
    item.note = payload.note
    item.checked_by = (user.display_name or user.username) if payload.checked else ""
    db.commit()
    db.refresh(item)
    return ok(serializers.checklist(item), "已更新")
