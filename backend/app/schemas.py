"""Pydantic v2 请求模型（统一参数校验）。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ShotSize = Literal["远景", "全景", "中景", "近景", "特写"]
CameraAngle = Literal["平视", "俯视", "仰视", "斜视", "主观"]
CameraMove = Literal["固定", "推", "拉", "摇", "移", "跟", "升降"]
Transition = Literal["cut", "dissolve", "fade", "wipe"]
Role = Literal["director", "storyboard", "artist", "reviewer", "student", "admin"]


class BaseSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


# ---------------- 认证 ----------------
class RegisterRequest(BaseSchema):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_\-]+$")
    password: str = Field(min_length=6, max_length=64)
    display_name: str = Field(default="", max_length=32)
    role: Role = "student"


class LoginRequest(BaseSchema):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=64)


# ---------------- 剧集 ----------------
class SeriesCreate(BaseSchema):
    title: str = Field(min_length=1, max_length=80)
    genre: str = Field(default="日常", max_length=20)
    logline: str = Field(default="", max_length=300)
    synopsis: str = Field(default="", max_length=4000)
    episodes_planned: int = Field(default=1, ge=1, le=200)
    target_duration: int = Field(default=90, ge=10, le=1800)
    style: str = Field(default="日系赛璐璐", max_length=60)
    platform: Literal["vertical", "horizontal"] = "vertical"
    cover_prompt: str = Field(default="", max_length=2000)


class SeriesUpdate(BaseSchema):
    title: str | None = Field(default=None, min_length=1, max_length=80)
    genre: str | None = Field(default=None, max_length=20)
    logline: str | None = Field(default=None, max_length=300)
    synopsis: str | None = Field(default=None, max_length=4000)
    episodes_planned: int | None = Field(default=None, ge=1, le=200)
    target_duration: int | None = Field(default=None, ge=10, le=1800)
    style: str | None = Field(default=None, max_length=60)
    platform: Literal["vertical", "horizontal"] | None = None
    status: Literal["draft", "in_production", "review", "completed", "archived"] | None = None
    cover_prompt: str | None = Field(default=None, max_length=2000)


# ---------------- 分集 ----------------
class EpisodeCreate(BaseSchema):
    title: str = Field(min_length=1, max_length=80)
    number: int | None = Field(default=None, ge=1, le=999)
    summary: str = Field(default="", max_length=2000)


class EpisodeUpdate(BaseSchema):
    title: str | None = Field(default=None, min_length=1, max_length=80)
    summary: str | None = Field(default=None, max_length=2000)
    status: Literal["draft", "scripting", "storyboard", "generating", "editing", "review", "approved"] | None = None


# ---------------- 剧本 ----------------
class ScriptSave(BaseSchema):
    content: str = Field(default="", max_length=100_000)
    structure: Literal["三幕式", "起承转合", "自由"] = "三幕式"


class SceneCreate(BaseSchema):
    title: str = Field(default="", max_length=80)
    location: str = Field(default="", max_length=80)
    time_of_day: str = Field(default="夜", max_length=20)
    characters: str = Field(default="", max_length=200)
    action_text: str = Field(default="", max_length=4000)
    dialogue: str = Field(default="", max_length=4000)
    mood: str = Field(default="", max_length=40)
    duration_seconds: float = Field(default=12.0, gt=0, le=600)


class SceneUpdate(BaseSchema):
    title: str | None = Field(default=None, max_length=80)
    location: str | None = Field(default=None, max_length=80)
    time_of_day: str | None = Field(default=None, max_length=20)
    characters: str | None = Field(default=None, max_length=200)
    action_text: str | None = Field(default=None, max_length=4000)
    dialogue: str | None = Field(default=None, max_length=4000)
    mood: str | None = Field(default=None, max_length=40)
    duration_seconds: float | None = Field(default=None, gt=0, le=600)


class MoveRequest(BaseSchema):
    direction: Literal["up", "down"] = "down"


# ---------------- 分镜 ----------------
class ShotCreate(BaseSchema):
    shot_no: str | None = Field(default=None, max_length=20)
    shot_size: ShotSize = "中景"
    camera_angle: CameraAngle = "平视"
    camera_move: CameraMove = "固定"
    duration_seconds: float = Field(default=5.0, gt=0, le=300)
    description: str = Field(default="", max_length=4000)
    dialogue: str = Field(default="", max_length=4000)
    bgm: str = Field(default="", max_length=120)
    characters: str = Field(default="", max_length=200)
    character_id: int | None = None
    scene_card_id: int | None = None
    prompt: str = Field(default="", max_length=8000)
    negative_prompt: str = Field(default="", max_length=4000)


class ShotUpdate(BaseSchema):
    shot_no: str | None = Field(default=None, max_length=20)
    shot_size: ShotSize | None = None
    camera_angle: CameraAngle | None = None
    camera_move: CameraMove | None = None
    duration_seconds: float | None = Field(default=None, gt=0, le=300)
    description: str | None = Field(default=None, max_length=4000)
    dialogue: str | None = Field(default=None, max_length=4000)
    bgm: str | None = Field(default=None, max_length=120)
    characters: str | None = Field(default=None, max_length=200)
    character_id: int | None = None
    scene_card_id: int | None = None
    prompt: str | None = Field(default=None, max_length=8000)
    negative_prompt: str | None = Field(default=None, max_length=4000)
    status: Literal["draft", "prompted", "generated", "approved"] | None = None


class ShotReorder(BaseSchema):
    ordered_ids: list[int] = Field(min_length=1, max_length=500)


# ---------------- 角色 / 场景卡 ----------------
class CharacterCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=40)
    role_type: Literal["主角", "配角", "反派", "群演"] = "配角"
    personality: str = Field(default="", max_length=2000)
    appearance_prompt: str = Field(default="", max_length=2000)
    prompt_prefix: str = Field(default="", max_length=2000)
    lora_name: str = Field(default="", max_length=80)
    lora_weight: float = Field(default=0.8, ge=0, le=2)
    seed: int = Field(default=0, ge=0, le=2**31 - 1)
    voice: str = Field(default="", max_length=60)


class CharacterUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    role_type: Literal["主角", "配角", "反派", "群演"] | None = None
    personality: str | None = Field(default=None, max_length=2000)
    appearance_prompt: str | None = Field(default=None, max_length=2000)
    prompt_prefix: str | None = Field(default=None, max_length=2000)
    lora_name: str | None = Field(default=None, max_length=80)
    lora_weight: float | None = Field(default=None, ge=0, le=2)
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)
    voice: str | None = Field(default=None, max_length=60)
    ref_asset_id: int | None = None


class SceneCardCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=40)
    description: str = Field(default="", max_length=2000)
    atmosphere: str = Field(default="", max_length=120)
    prompt: str = Field(default="", max_length=2000)
    prompt_prefix: str = Field(default="", max_length=2000)
    seed: int = Field(default=0, ge=0, le=2**31 - 1)


class SceneCardUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    description: str | None = Field(default=None, max_length=2000)
    atmosphere: str | None = Field(default=None, max_length=120)
    prompt: str | None = Field(default=None, max_length=2000)
    prompt_prefix: str | None = Field(default=None, max_length=2000)
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)
    ref_asset_id: int | None = None


# ---------------- 提示词 ----------------
class PromptBuildRequest(BaseSchema):
    subject: str = Field(default="", max_length=500)
    action: str = Field(default="", max_length=500)
    shot_size: ShotSize = "中景"
    camera_angle: CameraAngle = "平视"
    camera_move: CameraMove = "固定"
    style: str = Field(default="日系赛璐璐", max_length=60)
    lighting: str = Field(default="", max_length=120)
    quality: str = Field(default="", max_length=300)
    negative: str = Field(default="", max_length=2000)
    character_id: int | None = None
    scene_card_id: int | None = None
    consistency: bool = True


class PromptFromShotRequest(BaseSchema):
    # 分镜 id 以路径参数为准，body 里的 shot_id 仅用于兼容旧调用
    shot_id: int | None = None
    style: str | None = Field(default=None, max_length=60)
    consistency: bool = True
    save: bool = True


class PromptTemplateCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=60)
    category: Literal["style", "shot", "negative", "custom"] = "custom"
    style_key: str = Field(default="", max_length=40)
    content: str = Field(default="", max_length=2000)
    negative_prompt: str = Field(default="", max_length=2000)
    description: str = Field(default="", max_length=200)


# ---------------- 生成任务 ----------------
class TaskCreate(BaseSchema):
    prompt: str = Field(min_length=1, max_length=8000)
    negative_prompt: str = Field(default="", max_length=4000)
    kind: Literal["text2image", "img2video"] = "text2image"
    provider: str | None = Field(default=None, max_length=20)
    series_id: int | None = None
    episode_id: int | None = None
    shot_id: int | None = None
    character_id: int | None = None
    scene_card_id: int | None = None
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)
    params: dict[str, Any] = Field(default_factory=dict)


class TaskRetry(BaseSchema):
    prompt: str | None = Field(default=None, max_length=8000)
    negative_prompt: str | None = Field(default=None, max_length=4000)
    params: dict[str, Any] | None = None


# ---------------- 素材 ----------------
class AssetUpdate(BaseSchema):
    title: str | None = Field(default=None, max_length=120)
    status: Literal["candidate", "selected", "rejected", "archived"] | None = None
    review_note: str | None = Field(default=None, max_length=200)
    rating: int | None = Field(default=None, ge=0, le=5)


class AssetRateRequest(BaseSchema):
    score: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=200)


class AssetBatchRequest(BaseSchema):
    ids: list[int] = Field(min_length=1, max_length=100)
    action: Literal["select", "reject", "regenerate", "archive"] = "select"


class AssetReviseRequest(BaseSchema):
    issues: list[str] = Field(min_length=1, max_length=10)
    note: str = Field(default="", max_length=200)


# ---------------- 合成单 ----------------
class TimelineCreate(BaseSchema):
    name: str = Field(default="成片合成单", max_length=120)
    auto_fill: bool = True


class TimelineItemUpdate(BaseSchema):
    duration_seconds: float | None = Field(default=None, gt=0, le=300)
    subtitle: str | None = Field(default=None, max_length=2000)
    transition: Transition | None = None
    audio_note: str | None = Field(default=None, max_length=120)
    asset_id: int | None = None


class ExportRequest(BaseSchema):
    format: Literal["csv", "json", "srt", "zip"] = "csv"


# ---------------- 审核 ----------------
class ReviewCreate(BaseSchema):
    target_type: Literal["episode", "timeline", "asset"] = "episode"
    target_id: int
    title: str = Field(default="", max_length=160)
    comment: str = Field(default="", max_length=2000)


class ReviewDecision(BaseSchema):
    approve: bool
    comment: str = Field(default="", max_length=2000)


# ---------------- 质检 ----------------
class ChecklistUpdate(BaseSchema):
    checked: bool
    note: str = Field(default="", max_length=200)


# ---------------- 通用 ----------------
class PageQuery(BaseSchema):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
