"""剧集 / 分集 / 剧本 / 场次 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import delete, func, select

from app import serializers
from app.crud import current_script, episodes_of, get_episode, get_series, list_scripts, list_series
from app.crud.common import page_result, paginate
from app.crud.series import next_episode_number, next_scene_seq, scenes_of
from app.deps import CurrentUser, DbSession
from app.errors import ConflictError, NotFoundError, ok
from app.models import (
    Asset,
    Character,
    Episode,
    QualityChecklist,
    SceneCard,
    Script,
    ScriptScene,
    Series,
    StoryboardShot,
    Timeline,
    TimelineItem,
)
from app.schemas import (
    EpisodeCreate,
    EpisodeUpdate,
    MoveRequest,
    SceneCreate,
    SceneUpdate,
    ScriptSave,
    SeriesCreate,
    SeriesUpdate,
)

router = APIRouter(tags=["剧集"])


# ---------------- 剧集 ----------------
@router.get("/series", summary="剧集列表（按更新时间倒序）")
def list_series_api(
    db: DbSession,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str = "",
    status: str = "",
) -> dict:
    rows, total = paginate(db, list_series(db, search=search, status=status), page, size)
    return ok(page_result([serializers.series(db, row) for row in rows], total, page, size))


@router.post("/series", summary="新建剧集 / 短片项目")
def create_series(payload: SeriesCreate, db: DbSession, user: CurrentUser) -> dict:
    series = Series(owner_id=user.id, **payload.model_dump())
    db.add(series)
    db.commit()
    db.refresh(series)
    return ok(serializers.series(db, series), "剧集创建成功")


@router.get("/series/{series_id}", summary="剧集详情（含分集列表）")
def series_detail(series_id: int, db: DbSession) -> dict:
    series = get_series(db, series_id)
    episodes = episodes_of(db, series.id)
    data = serializers.series(db, series)
    data["episodes"] = [serializers.episode(item) for item in episodes]
    data["character_count"] = int(
        db.scalar(select(func.count()).select_from(Character).where(Character.series_id == series.id)) or 0
    )
    data["scene_count"] = int(
        db.scalar(select(func.count()).select_from(SceneCard).where(SceneCard.series_id == series.id)) or 0
    )
    return ok(data)


@router.patch("/series/{series_id}", summary="编辑剧集信息 / 推进状态")
def update_series(series_id: int, payload: SeriesUpdate, db: DbSession) -> dict:
    series = get_series(db, series_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(series, field, value)
    db.commit()
    db.refresh(series)
    return ok(serializers.series(db, series), "已保存")


@router.delete("/series/{series_id}", summary="删除剧集（连同分集/分镜/合成单）")
def delete_series(series_id: int, db: DbSession) -> dict:
    series = get_series(db, series_id)
    for episode in episodes_of(db, series.id):
        _delete_episode(db, episode)
    db.execute(delete(Character).where(Character.series_id == series.id))
    db.execute(delete(SceneCard).where(SceneCard.series_id == series.id))
    db.delete(series)
    db.commit()
    return ok({"deleted": series_id}, "已删除")


def _delete_episode(db: DbSession, episode: Episode) -> None:
    timeline = db.scalar(select(Timeline).where(Timeline.episode_id == episode.id))
    if timeline is not None:
        db.execute(delete(TimelineItem).where(TimelineItem.timeline_id == timeline.id))
        db.delete(timeline)
    db.execute(delete(ScriptScene).where(ScriptScene.episode_id == episode.id))
    db.execute(delete(Script).where(Script.episode_id == episode.id))
    db.execute(delete(StoryboardShot).where(StoryboardShot.episode_id == episode.id))
    db.execute(delete(QualityChecklist).where(QualityChecklist.episode_id == episode.id))
    db.delete(episode)


# ---------------- 分集 ----------------
@router.get("/series/{series_id}/episodes", summary="分集列表")
def list_episodes(series_id: int, db: DbSession) -> dict:
    series = get_series(db, series_id)
    items = episodes_of(db, series.id)
    return ok({"items": [serializers.episode(item) for item in items], "total": len(items)})


@router.post("/series/{series_id}/episodes", summary="新增分集")
def create_episode(series_id: int, payload: EpisodeCreate, db: DbSession) -> dict:
    series = get_series(db, series_id)
    number = payload.number or next_episode_number(db, series.id)
    exists = db.scalar(
        select(Episode).where(Episode.series_id == series.id, Episode.number == number)
    )
    if exists is not None:
        raise ConflictError(f"第 {number} 集已存在", code=40902)
    episode = Episode(series_id=series.id, number=number, title=payload.title, summary=payload.summary)
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return ok(serializers.episode(episode), "分集已创建")


@router.get("/episodes/{episode_id}", summary="分集详情（剧本 + 场次 + 统计）")
def episode_detail(episode_id: int, db: DbSession) -> dict:
    episode = get_episode(db, episode_id)
    script = current_script(db, episode.id)
    scenes = scenes_of(db, episode.id)
    shot_count = int(
        db.scalar(
            select(func.count()).select_from(StoryboardShot).where(StoryboardShot.episode_id == episode.id)
        )
        or 0
    )
    total_duration = db.scalar(
        select(func.sum(StoryboardShot.duration_seconds)).where(StoryboardShot.episode_id == episode.id)
    )
    series = get_series(db, episode.series_id)
    return ok(
        {
            **serializers.episode(episode),
            "series": {"id": series.id, "title": series.title, "style": series.style, "platform": series.platform},
            "script": serializers.script(script),
            "scenes": [serializers.scene(item) for item in scenes],
            "shot_count": shot_count,
            "total_duration": round(float(total_duration or 0), 2),
        }
    )


@router.patch("/episodes/{episode_id}", summary="编辑分集 / 推进制作状态")
def update_episode(episode_id: int, payload: EpisodeUpdate, db: DbSession) -> dict:
    episode = get_episode(db, episode_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(episode, field, value)
    db.commit()
    db.refresh(episode)
    return ok(serializers.episode(episode), "已保存")


@router.delete("/episodes/{episode_id}", summary="删除分集")
def delete_episode(episode_id: int, db: DbSession) -> dict:
    episode = get_episode(db, episode_id)
    _delete_episode(db, episode)
    db.commit()
    return ok({"deleted": episode_id}, "已删除")


# ---------------- 剧本 ----------------
@router.get("/episodes/{episode_id}/script", summary="当前剧本 + 历史版本")
def get_script(episode_id: int, db: DbSession) -> dict:
    episode = get_episode(db, episode_id)
    script = current_script(db, episode.id)
    versions = list_scripts(db, episode.id)
    return ok(
        {
            "script": serializers.script(script),
            "versions": [serializers.script(item) for item in versions],
        }
    )


@router.put("/episodes/{episode_id}/script", summary="保存剧本（每次保存生成新版本）")
def save_script(episode_id: int, payload: ScriptSave, db: DbSession, user: CurrentUser) -> dict:
    episode = get_episode(db, episode_id)
    latest = current_script(db, episode.id)
    version = (latest.version + 1) if latest is not None else 1
    for item in list_scripts(db, episode.id):
        item.is_current = False
    script = Script(
        episode_id=episode.id,
        version=version,
        structure=payload.structure,
        content=payload.content,
        is_current=True,
        created_by=user.username,
    )
    db.add(script)
    if episode.status == "draft":
        episode.status = "scripting"
    db.commit()
    db.refresh(script)
    return ok(serializers.script(script), f"已保存为 v{version}")


# ---------------- 场次 ----------------
@router.get("/episodes/{episode_id}/scenes", summary="场次列表")
def list_scenes(episode_id: int, db: DbSession) -> dict:
    episode = get_episode(db, episode_id)
    items = scenes_of(db, episode.id)
    return ok({"items": [serializers.scene(item) for item in items], "total": len(items)})


@router.post("/episodes/{episode_id}/scenes", summary="新增场次")
def create_scene(episode_id: int, payload: SceneCreate, db: DbSession) -> dict:
    episode = get_episode(db, episode_id)
    script = current_script(db, episode.id)
    if script is None:
        script = Script(episode_id=episode.id, version=1, content="", is_current=True, created_by="system")
        db.add(script)
        db.flush()
    scene = ScriptScene(
        script_id=script.id,
        episode_id=episode.id,
        seq=next_scene_seq(db, episode.id),
        **payload.model_dump(),
    )
    db.add(scene)
    db.commit()
    db.refresh(scene)
    return ok(serializers.scene(scene), "场次已添加")


@router.patch("/scenes/{scene_id}", summary="编辑场次")
def update_scene(scene_id: int, payload: SceneUpdate, db: DbSession) -> dict:
    scene = db.get(ScriptScene, scene_id)
    if scene is None:
        raise NotFoundError("场次不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(scene, field, value)
    db.commit()
    db.refresh(scene)
    return ok(serializers.scene(scene), "已保存")


@router.delete("/scenes/{scene_id}", summary="删除场次")
def delete_scene(scene_id: int, db: DbSession) -> dict:
    scene = db.get(ScriptScene, scene_id)
    if scene is None:
        raise NotFoundError("场次不存在")
    db.delete(scene)
    db.commit()
    return ok({"deleted": scene_id}, "已删除")


@router.post("/scenes/{scene_id}/move", summary="场次上移 / 下移")
def move_scene(scene_id: int, payload: MoveRequest, db: DbSession) -> dict:
    scene = db.get(ScriptScene, scene_id)
    if scene is None:
        raise NotFoundError("场次不存在")
    stmt = (
        select(ScriptScene)
        .where(ScriptScene.episode_id == scene.episode_id)
        .order_by(ScriptScene.seq)
    )
    items = list(db.scalars(stmt).all())
    index = next((i for i, item in enumerate(items) if item.id == scene.id), None)
    if index is None:
        raise NotFoundError("场次不存在")
    target = index - 1 if payload.direction == "up" else index + 1
    if target < 0 or target >= len(items):
        return ok({"items": [serializers.scene(item) for item in items]}, "已到边界")
    items[index], items[target] = items[target], items[index]
    for position, item in enumerate(items, start=1):
        item.seq = position
    db.commit()
    return ok({"items": [serializers.scene(item) for item in items]}, "顺序已更新")
