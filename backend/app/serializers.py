"""ORM → dict 序列化：统一前端字段，并生成 /media 可访问的静态 URL。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import (
    ASSET_STATUS_LABELS,
    EPISODE_STATUS_LABELS,
    GENERATION_KINDS,
    SERIES_STATUS_LABELS,
    TASK_STATUS_LABELS,
)

ROLE_LABELS = {
    "director": "导演",
    "storyboard": "分镜师",
    "artist": "美术",
    "reviewer": "审核",
    "student": "学员",
    "admin": "管理员",
}

PLATFORM_LABELS = {"vertical": "竖屏短片", "horizontal": "横屏番剧"}


def media_url(path: str | None) -> str:
    """本地静态路径 → 可访问 URL（/media 挂载在 storage 目录）。"""
    if not path:
        return ""
    return path if path.startswith(("http://", "https://", "/")) else f"/media/{path}"


def iso(value: Any) -> str:
    return value.isoformat() + "Z" if hasattr(value, "isoformat") else ""


def user(obj: Any) -> dict[str, Any]:
    return {
        "id": obj.id,
        "username": obj.username,
        "display_name": obj.display_name or obj.username,
        "role": obj.role,
        "role_label": ROLE_LABELS.get(obj.role, obj.role),
        "created_at": iso(obj.created_at),
    }


def series(db: Session, obj: Any, *, with_stats: bool = True) -> dict[str, Any]:
    from app.models import Episode, StoryboardShot

    data = {
        "id": obj.id,
        "title": obj.title,
        "genre": obj.genre,
        "logline": obj.logline,
        "synopsis": obj.synopsis,
        "episodes_planned": obj.episodes_planned,
        "target_duration": obj.target_duration,
        "style": obj.style,
        "platform": obj.platform,
        "platform_label": PLATFORM_LABELS.get(obj.platform, obj.platform),
        "status": obj.status,
        "status_label": SERIES_STATUS_LABELS.get(obj.status, obj.status),
        "cover_prompt": obj.cover_prompt,
        "cover_asset_id": obj.cover_asset_id,
        "cover_url": "",
        "owner_id": obj.owner_id,
        "owner_name": "",
        "created_at": iso(obj.created_at),
        "updated_at": iso(obj.updated_at),
        "episode_count": 0,
        "shot_count": 0,
    }
    if obj.cover_asset_id:
        from app.models import Asset

        asset = db.get(Asset, obj.cover_asset_id)
        if asset is not None:
            data["cover_url"] = media_url(asset.thumb_path or asset.file_path)
    if obj.owner_id:
        from app.models import User

        owner = db.get(User, obj.owner_id)
        if owner is not None:
            data["owner_name"] = owner.display_name or owner.username
    if with_stats:
        data["episode_count"] = int(
            db.scalar(select(func.count()).select_from(Episode).where(Episode.series_id == obj.id)) or 0
        )
        data["shot_count"] = int(
            db.scalar(
                select(func.count())
                .select_from(StoryboardShot)
                .join(Episode, Episode.id == StoryboardShot.episode_id)
                .where(Episode.series_id == obj.id)
            )
            or 0
        )
    return data


def episode(obj: Any) -> dict[str, Any]:
    return {
        "id": obj.id,
        "series_id": obj.series_id,
        "number": obj.number,
        "title": obj.title,
        "summary": obj.summary,
        "status": obj.status,
        "status_label": EPISODE_STATUS_LABELS.get(obj.status, obj.status),
        "created_at": iso(obj.created_at),
        "updated_at": iso(obj.updated_at),
    }


def script(obj: Any | None) -> dict[str, Any] | None:
    if obj is None:
        return None
    return {
        "id": obj.id,
        "episode_id": obj.episode_id,
        "version": obj.version,
        "structure": obj.structure,
        "content": obj.content,
        "is_current": obj.is_current,
        "created_by": obj.created_by,
        "created_at": iso(obj.created_at),
    }


def scene(obj: Any) -> dict[str, Any]:
    return {
        "id": obj.id,
        "script_id": obj.script_id,
        "episode_id": obj.episode_id,
        "seq": obj.seq,
        "title": obj.title,
        "location": obj.location,
        "time_of_day": obj.time_of_day,
        "characters": obj.characters,
        "action_text": obj.action_text,
        "dialogue": obj.dialogue,
        "mood": obj.mood,
        "duration_seconds": obj.duration_seconds,
        "created_at": iso(obj.created_at),
    }


def shot(db: Session, obj: Any) -> dict[str, Any]:
    asset_url = ""
    if obj.asset_id:
        from app.models import Asset

        asset = db.get(Asset, obj.asset_id)
        if asset is not None:
            asset_url = media_url(asset.thumb_path or asset.file_path)
    return {
        "id": obj.id,
        "episode_id": obj.episode_id,
        "seq": obj.seq,
        "shot_no": obj.shot_no,
        "shot_size": obj.shot_size,
        "camera_angle": obj.camera_angle,
        "camera_move": obj.camera_move,
        "duration_seconds": obj.duration_seconds,
        "description": obj.description,
        "dialogue": obj.dialogue,
        "bgm": obj.bgm,
        "characters": obj.characters,
        "character_id": obj.character_id,
        "scene_card_id": obj.scene_card_id,
        "prompt": obj.prompt,
        "negative_prompt": obj.negative_prompt,
        "asset_id": obj.asset_id,
        "asset_url": asset_url,
        "status": obj.status,
        "created_at": iso(obj.created_at),
        "updated_at": iso(obj.updated_at),
    }


def character(obj: Any) -> dict[str, Any]:
    return {
        "id": obj.id,
        "series_id": obj.series_id,
        "name": obj.name,
        "role_type": obj.role_type,
        "personality": obj.personality,
        "appearance_prompt": obj.appearance_prompt,
        "prompt_prefix": obj.prompt_prefix,
        "ref_asset_id": obj.ref_asset_id,
        "lora_name": obj.lora_name,
        "lora_weight": obj.lora_weight,
        "seed": obj.seed,
        "voice": obj.voice,
        "created_at": iso(obj.created_at),
    }


def scene_card(obj: Any) -> dict[str, Any]:
    return {
        "id": obj.id,
        "series_id": obj.series_id,
        "name": obj.name,
        "description": obj.description,
        "atmosphere": obj.atmosphere,
        "prompt": obj.prompt,
        "prompt_prefix": obj.prompt_prefix,
        "ref_asset_id": obj.ref_asset_id,
        "seed": obj.seed,
        "created_at": iso(obj.created_at),
    }


def prompt_template(obj: Any) -> dict[str, Any]:
    return {
        "id": obj.id,
        "name": obj.name,
        "category": obj.category,
        "style_key": obj.style_key,
        "content": obj.content,
        "negative_prompt": obj.negative_prompt,
        "description": obj.description,
        "is_builtin": obj.is_builtin,
        "created_at": iso(obj.created_at),
    }


def prompt_history(obj: Any) -> dict[str, Any]:
    return {
        "id": obj.id,
        "series_id": obj.series_id,
        "shot_id": obj.shot_id,
        "task_id": obj.task_id,
        "kind": obj.kind,
        "prompt": obj.prompt,
        "negative_prompt": obj.negative_prompt,
        "params": obj.params_json or {},
        "created_by": obj.created_by,
        "created_at": iso(obj.created_at),
    }


def task(db: Session, obj: Any) -> dict[str, Any]:
    asset = None
    if obj.asset_id:
        from app.models import Asset

        asset = db.get(Asset, obj.asset_id)
    return {
        "id": obj.id,
        "series_id": obj.series_id,
        "episode_id": obj.episode_id,
        "shot_id": obj.shot_id,
        "kind": obj.kind,
        "kind_label": GENERATION_KINDS.get(obj.kind, obj.kind),
        "provider": obj.provider,
        "prompt": obj.prompt,
        "negative_prompt": obj.negative_prompt,
        "params": obj.params_json or {},
        "status": obj.status,
        "status_label": TASK_STATUS_LABELS.get(obj.status, obj.status),
        "progress": obj.progress,
        "error": obj.error,
        "seed": obj.seed,
        "asset_id": obj.asset_id,
        "asset_url": media_url(asset.thumb_path or asset.file_path) if asset is not None else "",
        "duration_ms": obj.duration_ms,
        "created_by": obj.created_by,
        "created_at": iso(obj.created_at),
        "started_at": iso(obj.started_at),
        "finished_at": iso(obj.finished_at),
    }


def asset(db: Session, obj: Any) -> dict[str, Any]:
    return {
        "id": obj.id,
        "series_id": obj.series_id,
        "episode_id": obj.episode_id,
        "shot_id": obj.shot_id,
        "character_id": obj.character_id,
        "scene_card_id": obj.scene_card_id,
        "task_id": obj.task_id,
        "kind": obj.kind,
        "title": obj.title,
        "file_path": obj.file_path,
        "url": media_url(obj.file_path),
        "thumb_url": media_url(obj.thumb_path or obj.file_path),
        "width": obj.width,
        "height": obj.height,
        "file_size": obj.file_size,
        "seed": obj.seed,
        "prompt": obj.prompt,
        "negative_prompt": obj.negative_prompt,
        "provider": obj.provider,
        "status": obj.status,
        "status_label": ASSET_STATUS_LABELS.get(obj.status, obj.status),
        "rating": obj.rating,
        "review_note": obj.review_note,
        "meta": obj.meta_json or {},
        "created_at": iso(obj.created_at),
        "updated_at": iso(obj.updated_at),
    }


def timeline_item(db: Session, obj: Any) -> dict[str, Any]:
    shot_obj = None
    asset_obj = None
    if obj.shot_id:
        from app.models import StoryboardShot

        shot_obj = db.get(StoryboardShot, obj.shot_id)
    if obj.asset_id:
        from app.models import Asset

        asset_obj = db.get(Asset, obj.asset_id)
    return {
        "id": obj.id,
        "timeline_id": obj.timeline_id,
        "shot_id": obj.shot_id,
        "asset_id": obj.asset_id,
        "seq": obj.seq,
        "duration_seconds": obj.duration_seconds,
        "subtitle": obj.subtitle,
        "transition": obj.transition,
        "audio_note": obj.audio_note,
        "shot_no": shot_obj.shot_no if shot_obj is not None else "",
        "description": shot_obj.description if shot_obj is not None else "",
        "asset_url": media_url(asset_obj.thumb_path or asset_obj.file_path) if asset_obj is not None else "",
    }


def review(obj: Any) -> dict[str, Any]:
    return {
        "id": obj.id,
        "series_id": obj.series_id,
        "target_type": obj.target_type,
        "target_id": obj.target_id,
        "title": obj.title,
        "status": obj.status,
        "comment": obj.comment,
        "submitted_by": obj.submitted_by,
        "reviewer_name": obj.reviewer_name,
        "created_at": iso(obj.created_at),
        "decided_at": iso(obj.decided_at),
    }


def checklist(obj: Any) -> dict[str, Any]:
    return {
        "id": obj.id,
        "episode_id": obj.episode_id,
        "item_key": obj.item_key,
        "label": obj.label,
        "checked": obj.checked,
        "note": obj.note,
        "checked_by": obj.checked_by,
        "updated_at": iso(obj.updated_at),
    }


def page(items: list[Any], total: int, page_no: int, size: int) -> dict[str, Any]:
    return {"items": items, "total": total, "page": page_no, "size": size}
