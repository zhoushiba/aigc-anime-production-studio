"""角色 / 场景卡 / 提示词模板 / 生成任务的数据访问。"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.crud.common import get_or_404
from app.models import (
    Character,
    GenerationTask,
    PromptHistory,
    PromptTemplate,
    SceneCard,
    StoryboardShot,
)


# ---------- 角色 ----------
def list_characters(db: Session, series_id: int | None = None) -> list[Character]:
    stmt = select(Character)
    if series_id:
        stmt = stmt.where(Character.series_id == series_id)
    return list(db.scalars(stmt.order_by(Character.id)).all())


def get_character(db: Session, character_id: int) -> Character:
    return get_or_404(db, Character, character_id, "角色")


# ---------- 场景卡 ----------
def list_scene_cards(db: Session, series_id: int | None = None) -> list[SceneCard]:
    stmt = select(SceneCard)
    if series_id:
        stmt = stmt.where(SceneCard.series_id == series_id)
    return list(db.scalars(stmt.order_by(SceneCard.id)).all())


def get_scene_card(db: Session, scene_card_id: int) -> SceneCard:
    return get_or_404(db, SceneCard, scene_card_id, "场景卡")


# ---------- 提示词模板 ----------
def list_prompt_templates(db: Session, *, keyword: str = "") -> list[PromptTemplate]:
    stmt = select(PromptTemplate)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(PromptTemplate.name.like(like), PromptTemplate.description.like(like)))
    return list(db.scalars(stmt.order_by(PromptTemplate.is_builtin.desc(), PromptTemplate.id)).all())


def get_prompt_template(db: Session, template_id: int) -> PromptTemplate:
    return get_or_404(db, PromptTemplate, template_id, "提示词模板")


def list_prompt_history(db: Session, *, series_id: int | None = None, limit: int = 50) -> list[PromptHistory]:
    stmt = select(PromptHistory)
    if series_id:
        stmt = stmt.where(PromptHistory.series_id == series_id)
    return list(db.scalars(stmt.order_by(PromptHistory.id.desc()).limit(limit)).all())


# ---------- 生成任务 ----------
def list_tasks(
    db: Session,
    *,
    status: str = "",
    series_id: int | None = None,
    episode_id: int | None = None,
    shot_id: int | None = None,
    kind: str = "",
) -> object:
    stmt = select(GenerationTask)
    if status:
        stmt = stmt.where(GenerationTask.status == status)
    if series_id:
        stmt = stmt.where(GenerationTask.series_id == series_id)
    if episode_id:
        stmt = stmt.where(GenerationTask.episode_id == episode_id)
    if shot_id:
        stmt = stmt.where(GenerationTask.shot_id == shot_id)
    if kind:
        stmt = stmt.where(GenerationTask.kind == kind)
    return stmt.order_by(GenerationTask.id.desc())


def get_task(db: Session, task_id: int) -> GenerationTask:
    return get_or_404(db, GenerationTask, task_id, "生成任务")


def recent_tasks(db: Session, limit: int = 8) -> list[GenerationTask]:
    return list(db.scalars(select(GenerationTask).order_by(GenerationTask.id.desc()).limit(limit)).all())


def count_tasks(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(GenerationTask)) or 0)


def shot_of_task(db: Session, task: GenerationTask) -> StoryboardShot | None:
    if not task.shot_id:
        return None
    return db.get(StoryboardShot, task.shot_id)
