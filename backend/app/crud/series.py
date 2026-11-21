"""剧集 / 分集 / 剧本 / 场次的数据访问。"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.crud.common import get_or_404
from app.models import Episode, SceneCard, Script, ScriptScene, Series, StoryboardShot


def get_series(db: Session, series_id: int) -> Series:
    return get_or_404(db, Series, series_id, "剧集")


def list_series(db: Session, *, search: str = "", status: str = "") -> object:
    stmt = select(Series)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Series.title.like(like), Series.logline.like(like), Series.genre.like(like)))
    if status:
        stmt = stmt.where(Series.status == status)
    return stmt.order_by(Series.updated_at.desc(), Series.id.desc())


def episodes_of(db: Session, series_id: int) -> list[Episode]:
    return list(db.scalars(select(Episode).where(Episode.series_id == series_id).order_by(Episode.number)).all())


def get_episode(db: Session, episode_id: int) -> Episode:
    return get_or_404(db, Episode, episode_id, "分集")


def next_episode_number(db: Session, series_id: int) -> int:
    current = db.scalar(select(func.max(Episode.number)).where(Episode.series_id == series_id)) or 0
    return int(current) + 1


def current_script(db: Session, episode_id: int) -> Script | None:
    return db.scalar(
        select(Script).where(Script.episode_id == episode_id).order_by(Script.version.desc()).limit(1)
    )


def list_scripts(db: Session, episode_id: int) -> list[Script]:
    return list(db.scalars(select(Script).where(Script.episode_id == episode_id).order_by(Script.version.desc())).all())


def scenes_of(db: Session, episode_id: int) -> list[ScriptScene]:
    return list(
        db.scalars(select(ScriptScene).where(ScriptScene.episode_id == episode_id).order_by(ScriptScene.seq)).all()
    )


def next_scene_seq(db: Session, episode_id: int) -> int:
    current = db.scalar(select(func.max(ScriptScene.seq)).where(ScriptScene.episode_id == episode_id)) or 0
    return int(current) + 1


def shots_of(db: Session, episode_id: int) -> list[StoryboardShot]:
    return list(
        db.scalars(
            select(StoryboardShot).where(StoryboardShot.episode_id == episode_id).order_by(StoryboardShot.seq)
        ).all()
    )


def get_shot(db: Session, shot_id: int) -> StoryboardShot:
    return get_or_404(db, StoryboardShot, shot_id, "分镜")


def next_shot_seq(db: Session, episode_id: int) -> int:
    current = db.scalar(select(func.max(StoryboardShot.seq)).where(StoryboardShot.episode_id == episode_id)) or 0
    return int(current) + 1


def get_scene_card(db: Session, scene_card_id: int | None) -> SceneCard | None:
    if not scene_card_id:
        return None
    return db.get(SceneCard, scene_card_id)
