"""ORM 模型：覆盖「剧集 → 分集 → 剧本 → 分镜 → 生成任务 → 素材 → 合成单 → 审核」全链路。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    """统一使用 UTC 时间存储（前端按本地时区展示）。"""
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    display_name: Mapped[str] = mapped_column(String(50), default="")
    role: Mapped[str] = mapped_column(String(20), default="student", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Series(Base):
    """剧集 / 短片项目。"""

    __tablename__ = "series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120), index=True)
    genre: Mapped[str] = mapped_column(String(30), default="日常")
    logline: Mapped[str] = mapped_column(String(300), default="")
    synopsis: Mapped[str] = mapped_column(Text, default="")
    episodes_planned: Mapped[int] = mapped_column(Integer, default=1)
    target_duration: Mapped[int] = mapped_column(Integer, default=90)   # 单集目标时长（秒）
    style: Mapped[str] = mapped_column(String(60), default="日系赛璐璐")
    platform: Mapped[str] = mapped_column(String(20), default="vertical")  # vertical / horizontal
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    cover_prompt: Mapped[str] = mapped_column(Text, default="")
    cover_asset_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Episode(Base):
    """分集。"""

    __tablename__ = "episodes"
    __table_args__ = (UniqueConstraint("series_id", "number", name="uq_episode_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True)
    number: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(120), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Script(Base):
    """剧本正文的版本快照（每次保存生成一个新版本）。"""

    __tablename__ = "scripts"
    __table_args__ = (UniqueConstraint("episode_id", "version", name="uq_script_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    structure: Mapped[str] = mapped_column(String(20), default="三幕式")
    content: Mapped[str] = mapped_column(Text, default="")
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ScriptScene(Base):
    """剧本场次：地点 / 时间 / 人物 / 动作 / 对白。"""

    __tablename__ = "script_scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("scripts.id"), index=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(120), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    time_of_day: Mapped[str] = mapped_column(String(30), default="夜")
    characters: Mapped[str] = mapped_column(String(200), default="")
    action_text: Mapped[str] = mapped_column(Text, default="")
    dialogue: Mapped[str] = mapped_column(Text, default="")
    mood: Mapped[str] = mapped_column(String(60), default="")
    duration_seconds: Mapped[float] = mapped_column(Float, default=12.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Character(Base):
    """角色设定卡：外观 prompt + 一致性 seed + LoRA。"""

    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    role_type: Mapped[str] = mapped_column(String(20), default="配角")
    personality: Mapped[str] = mapped_column(Text, default="")
    appearance_prompt: Mapped[str] = mapped_column(Text, default="")
    prompt_prefix: Mapped[str] = mapped_column(Text, default="")
    ref_asset_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lora_name: Mapped[str] = mapped_column(String(80), default="")
    lora_weight: Mapped[float] = mapped_column(Float, default=0.8)
    seed: Mapped[int] = mapped_column(Integer, default=0)
    voice: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SceneCard(Base):
    """场景设定卡。"""

    __tablename__ = "scene_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(Text, default="")
    atmosphere: Mapped[str] = mapped_column(String(120), default="")
    prompt: Mapped[str] = mapped_column(Text, default="")
    prompt_prefix: Mapped[str] = mapped_column(Text, default="")
    ref_asset_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class StoryboardShot(Base):
    """分镜脚本一行。"""

    __tablename__ = "storyboard_shots"
    __table_args__ = (Index("ix_shots_episode_seq", "episode_id", "seq"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer, default=1)
    shot_no: Mapped[str] = mapped_column(String(20), default="01")
    shot_size: Mapped[str] = mapped_column(String(10), default="中景")
    camera_angle: Mapped[str] = mapped_column(String(10), default="平视")
    camera_move: Mapped[str] = mapped_column(String(10), default="固定")
    duration_seconds: Mapped[float] = mapped_column(Float, default=5.0)
    description: Mapped[str] = mapped_column(Text, default="")
    dialogue: Mapped[str] = mapped_column(Text, default="")
    bgm: Mapped[str] = mapped_column(String(120), default="")
    characters: Mapped[str] = mapped_column(String(200), default="")
    character_id: Mapped[int | None] = mapped_column(ForeignKey("characters.id"), nullable=True)
    scene_card_id: Mapped[int | None] = mapped_column(ForeignKey("scene_cards.id"), nullable=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    asset_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class PromptTemplate(Base):
    """提示词模板库（内置 12 套画风 + 自定义）。"""

    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    category: Mapped[str] = mapped_column(String(20), default="style")
    style_key: Mapped[str] = mapped_column(String(40), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(String(200), default="")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PromptHistory(Base):
    """提示词历史：谁在什么镜头用了什么提示词，可回溯复盘。"""

    __tablename__ = "prompt_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    shot_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kind: Mapped[str] = mapped_column(String(20), default="manual")
    prompt: Mapped[str] = mapped_column(Text, default="")
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    params_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class GenerationTask(Base):
    """AIGC 生成任务（文生图 / 图生视频）。"""

    __tablename__ = "generation_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    episode_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    shot_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(20), default="text2image")
    provider: Mapped[str] = mapped_column(String(20), default="mock")
    prompt: Mapped[str] = mapped_column(Text, default="")
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    params_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    asset_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seed: Mapped[int] = mapped_column(Integer, default=0)
    canceled: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Asset(Base):
    """素材库条目（图片 / 动图 / 参考图）。"""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    episode_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    shot_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    character_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    scene_card_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    task_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(20), default="image")
    title: Mapped[str] = mapped_column(String(120), default="")
    file_path: Mapped[str] = mapped_column(String(255), default="")
    thumb_path: Mapped[str] = mapped_column(String(255), default="")
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    seed: Mapped[int] = mapped_column(Integer, default=0)
    prompt: Mapped[str] = mapped_column(Text, default="")
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(20), default="mock")
    status: Mapped[str] = mapped_column(String(20), default="candidate", index=True)
    rating: Mapped[int] = mapped_column(Integer, default=0)
    review_note: Mapped[str] = mapped_column(String(200), default="")
    meta_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AssetRating(Base):
    """评分明细（支持多人打分，Asset.rating 存最新分）。"""

    __tablename__ = "asset_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=5)
    comment: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AssetRevision(Base):
    """二次优化记录：标注问题 → 追加修正词 → 重绘 → 与原图关联。"""

    __tablename__ = "asset_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    new_asset_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    issues_json: Mapped[list[Any]] = mapped_column(JSON, default=list)
    fix_prompt: Mapped[str] = mapped_column(Text, default="")
    task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Timeline(Base):
    """成片合成单：按分镜顺序排列镜头 + 转场 + 字幕。"""

    __tablename__ = "timelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="成片合成单")
    total_duration: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class TimelineItem(Base):
    __tablename__ = "timeline_items"
    __table_args__ = (Index("ix_timeline_items_seq", "timeline_id", "seq"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timeline_id: Mapped[int] = mapped_column(ForeignKey("timelines.id"), index=True)
    shot_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    asset_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seq: Mapped[int] = mapped_column(Integer, default=1)
    duration_seconds: Mapped[float] = mapped_column(Float, default=5.0)
    subtitle: Mapped[str] = mapped_column(Text, default="")
    transition: Mapped[str] = mapped_column(String(20), default="cut")
    audio_note: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class QualityChecklist(Base):
    """交付前质量检查清单。"""

    __tablename__ = "quality_checklists"
    __table_args__ = (UniqueConstraint("episode_id", "item_key", name="uq_checklist_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True)
    item_key: Mapped[str] = mapped_column(String(50))
    label: Mapped[str] = mapped_column(String(120), default="")
    checked: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(String(200), default="")
    checked_by: Mapped[str] = mapped_column(String(50), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ExportJob(Base):
    """导出任务：合成单 CSV / JSON / SRT。"""

    __tablename__ = "export_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True)
    timeline_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    format: Mapped[str] = mapped_column(String(10), default="csv")
    file_path: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(20), default="done")
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Review(Base):
    """审核流：提交 → 通过 / 驳回（带意见）。"""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    target_type: Mapped[str] = mapped_column(String(20), default="episode")  # episode / timeline / asset
    target_id: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    submitted_by: Mapped[str] = mapped_column(String(50), default="")
    reviewer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewer_name: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
