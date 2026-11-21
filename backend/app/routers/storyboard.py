"""分镜 / 角色卡 / 场景卡 / 提示词 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import delete, func, select

from app import serializers
from app.crud import (
    get_character,
    get_episode,
    get_prompt_template,
    get_scene_card as get_scene_card_crud,
    get_shot,
    list_characters,
    list_prompt_history,
    list_prompt_templates,
    list_scene_cards,
    next_shot_seq,
    shots_of,
)
from app.deps import CurrentUser, DbSession
from app.errors import ConflictError, NotFoundError, ok
from app.models import Character, PromptHistory, PromptTemplate, SceneCard, StoryboardShot
from app.schemas import (
    CharacterCreate,
    CharacterUpdate,
    MoveRequest,
    PromptBuildRequest,
    PromptFromShotRequest,
    PromptTemplateCreate,
    SceneCardCreate,
    SceneCardUpdate,
    ShotCreate,
    ShotReorder,
    ShotUpdate,
)
from app.services import prompt_builder

router = APIRouter(tags=["分镜与提示词"])


# ---------------- 分镜 ----------------
@router.get("/episodes/{episode_id}/shots", summary="分镜表（按镜号顺序）")
def list_shots(episode_id: int, db: DbSession) -> dict:
    episode = get_episode(db, episode_id)
    items = shots_of(db, episode.id)
    total_duration = round(sum(float(item.duration_seconds or 0) for item in items), 2)
    return ok(
        {
            "items": [serializers.shot(db, item) for item in items],
            "total": len(items),
            "total_duration": total_duration,
            "episode": serializers.episode(episode),
        }
    )


@router.post("/episodes/{episode_id}/shots", summary="新增分镜")
def create_shot(episode_id: int, payload: ShotCreate, db: DbSession) -> dict:
    episode = get_episode(db, episode_id)
    seq = next_shot_seq(db, episode.id)
    shot = StoryboardShot(
        episode_id=episode.id,
        seq=seq,
        shot_no=payload.shot_no or f"{seq:02d}",
        **payload.model_dump(exclude={"shot_no"}),
    )
    db.add(shot)
    if episode.status in ("draft", "scripting"):
        episode.status = "storyboard"
    db.commit()
    db.refresh(shot)
    return ok(serializers.shot(db, shot), "分镜已添加")


@router.get("/shots/{shot_id}", summary="分镜详情")
def shot_detail(shot_id: int, db: DbSession) -> dict:
    shot = get_shot(db, shot_id)
    return ok(serializers.shot(db, shot))


@router.patch("/shots/{shot_id}", summary="编辑分镜（景别/机位/运镜/画面描述/台词）")
def update_shot(shot_id: int, payload: ShotUpdate, db: DbSession) -> dict:
    shot = get_shot(db, shot_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(shot, field, value)
    db.commit()
    db.refresh(shot)
    return ok(serializers.shot(db, shot), "已保存")


@router.delete("/shots/{shot_id}", summary="删除分镜")
def delete_shot(shot_id: int, db: DbSession) -> dict:
    shot = get_shot(db, shot_id)
    db.delete(shot)
    db.commit()
    return ok({"deleted": shot_id}, "已删除")


@router.post("/shots/{shot_id}/move", summary="分镜上移 / 下移")
def move_shot(shot_id: int, payload: MoveRequest, db: DbSession) -> dict:
    shot = get_shot(db, shot_id)
    items = shots_of(db, shot.episode_id)
    index = next((i for i, item in enumerate(items) if item.id == shot.id), None)
    if index is None:
        raise NotFoundError("分镜不存在")
    target = index - 1 if payload.direction == "up" else index + 1
    if target < 0 or target >= len(items):
        return ok({"items": [serializers.shot(db, item) for item in items]}, "已到边界")
    items[index], items[target] = items[target], items[index]
    for position, item in enumerate(items, start=1):
        item.seq = position
    db.commit()
    return ok({"items": [serializers.shot(db, item) for item in items]}, "顺序已更新")


@router.post("/episodes/{episode_id}/shots/reorder", summary="按 id 顺序重排分镜")
def reorder_shots(episode_id: int, payload: ShotReorder, db: DbSession) -> dict:
    episode = get_episode(db, episode_id)
    items = {item.id: item for item in shots_of(db, episode.id)}
    unknown = [shot_id for shot_id in payload.ordered_ids if shot_id not in items]
    if unknown:
        raise NotFoundError(f"分镜不属于该分集：{unknown}")
    for position, shot_id in enumerate(payload.ordered_ids, start=1):
        items[shot_id].seq = position
        items[shot_id].shot_no = f"{position:02d}"
    db.commit()
    return ok({"items": [serializers.shot(db, item) for item in shots_of(db, episode.id)]}, "已重排")


@router.post("/shots/{shot_id}/prompt", summary="为分镜生成提示词（带角色/场景一致性）")
def build_shot_prompt(shot_id: int, payload: PromptFromShotRequest, db: DbSession, user: CurrentUser) -> dict:
    from app.models import Series

    shot = get_shot(db, shot_id)
    episode = get_episode(db, shot.episode_id)
    series = db.get(Series, episode.series_id)
    style = payload.style or (series.style if series is not None else "日系赛璐璐")
    character = db.get(Character, shot.character_id) if shot.character_id else None
    scene_card = db.get(SceneCard, shot.scene_card_id) if shot.scene_card_id else None
    built = prompt_builder.build_from_shot(
        shot, style=style, character=character, scene_card=scene_card, consistency=payload.consistency
    )
    if payload.save:
        shot.prompt = built["prompt"]
        shot.negative_prompt = built["negative_prompt"]
        if shot.status == "draft":
            shot.status = "prompted"
        db.add(
            PromptHistory(
                series_id=series.id if series is not None else None,
                shot_id=shot.id,
                kind="from_shot",
                prompt=built["prompt"],
                negative_prompt=built["negative_prompt"],
                params_json={"style": style, "consistency": payload.consistency},
                created_by=user.username,
            )
        )
        db.commit()
        db.refresh(shot)
    return ok({**built, "shot": serializers.shot(db, shot)}, "提示词已生成")


# ---------------- 角色卡 ----------------
@router.get("/series/{series_id}/characters", summary="角色设定卡列表")
def list_series_characters(series_id: int, db: DbSession) -> dict:
    items = list_characters(db, series_id)
    return ok({"items": [serializers.character(item) for item in items], "total": len(items)})


@router.post("/series/{series_id}/characters", summary="新建角色设定卡")
def create_character(series_id: int, payload: CharacterCreate, db: DbSession) -> dict:
    character = Character(series_id=series_id, **payload.model_dump())
    db.add(character)
    db.commit()
    db.refresh(character)
    return ok(serializers.character(character), "角色已创建")


@router.patch("/characters/{character_id}", summary="编辑角色（外形 prompt / LoRA / seed）")
def update_character(character_id: int, payload: CharacterUpdate, db: DbSession) -> dict:
    character = get_character(db, character_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(character, field, value)
    db.commit()
    db.refresh(character)
    return ok(serializers.character(character), "已保存")


@router.delete("/characters/{character_id}", summary="删除角色")
def delete_character(character_id: int, db: DbSession) -> dict:
    character = get_character(db, character_id)
    db.delete(character)
    db.commit()
    return ok({"deleted": character_id}, "已删除")


# ---------------- 场景卡 ----------------
@router.get("/series/{series_id}/scene-cards", summary="场景卡列表")
def list_series_scene_cards(series_id: int, db: DbSession) -> dict:
    items = list_scene_cards(db, series_id)
    return ok({"items": [serializers.scene_card(item) for item in items], "total": len(items)})


@router.post("/series/{series_id}/scene-cards", summary="新建场景卡")
def create_scene_card(series_id: int, payload: SceneCardCreate, db: DbSession) -> dict:
    card = SceneCard(series_id=series_id, **payload.model_dump())
    db.add(card)
    db.commit()
    db.refresh(card)
    return ok(serializers.scene_card(card), "场景卡已创建")


@router.patch("/scene-cards/{scene_card_id}", summary="编辑场景卡")
def update_scene_card(scene_card_id: int, payload: SceneCardUpdate, db: DbSession) -> dict:
    card = get_scene_card_crud(db, scene_card_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(card, field, value)
    db.commit()
    db.refresh(card)
    return ok(serializers.scene_card(card), "已保存")


@router.delete("/scene-cards/{scene_card_id}", summary="删除场景卡")
def delete_scene_card(scene_card_id: int, db: DbSession) -> dict:
    card = get_scene_card_crud(db, scene_card_id)
    db.delete(card)
    db.commit()
    return ok({"deleted": scene_card_id}, "已删除")


# ---------------- 提示词 ----------------
@router.post("/prompts/build", summary="提示词构建器：主体+动作+镜头语言+画风+光影+画质词+负向词")
def build_prompt(payload: PromptBuildRequest, db: DbSession) -> dict:
    character = db.get(Character, payload.character_id) if payload.character_id else None
    scene_card = db.get(SceneCard, payload.scene_card_id) if payload.scene_card_id else None
    prefixes: list[str] = []
    tokens: list[str] = []
    if scene_card is not None:
        prefixes.extend([scene_card.prompt_prefix, scene_card.prompt])
        if payload.consistency and scene_card.seed:
            tokens.append(f"scene seed {scene_card.seed}")
    if character is not None:
        prefixes.extend([character.prompt_prefix, character.appearance_prompt])
        if payload.consistency:
            if character.lora_name:
                tokens.append(f"lora:{character.lora_name}:{character.lora_weight}")
            if character.seed:
                tokens.append(f"character seed {character.seed}")
    built = prompt_builder.build_prompt(
        subject=payload.subject,
        action=payload.action,
        shot_size=payload.shot_size,
        camera_angle=payload.camera_angle,
        camera_move=payload.camera_move,
        style=payload.style,
        lighting=payload.lighting,
        quality=payload.quality,
        negative=payload.negative,
        consistency_prefix=", ".join([item for item in prefixes if item]),
        consistency_tokens=tokens,
    )
    return ok(built)


@router.get("/prompts/templates", summary="提示词模板（12 套内置画风 + 自定义）")
def list_templates(db: DbSession, keyword: str = "") -> dict:
    items = list_prompt_templates(db, keyword=keyword)
    return ok({"items": [serializers.prompt_template(item) for item in items], "total": len(items)})


@router.post("/prompts/templates", summary="新建提示词模板")
def create_template(payload: PromptTemplateCreate, db: DbSession) -> dict:
    exists = db.scalar(select(PromptTemplate).where(PromptTemplate.name == payload.name))
    if exists is not None:
        raise ConflictError("模板名称已存在", code=40903)
    template = PromptTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return ok(serializers.prompt_template(template), "模板已创建")


@router.delete("/prompts/templates/{template_id}", summary="删除自定义模板")
def delete_template(template_id: int, db: DbSession) -> dict:
    template = get_prompt_template(db, template_id)
    if template.is_builtin:
        raise ConflictError("内置模板不可删除", code=40904)
    db.delete(template)
    db.commit()
    return ok({"deleted": template_id}, "已删除")


@router.get("/prompts/history", summary="提示词使用历史")
def prompt_history(db: DbSession, series_id: int | None = None, limit: int = Query(50, ge=1, le=200)) -> dict:
    items = list_prompt_history(db, series_id=series_id, limit=limit)
    return ok({"items": [serializers.prompt_history(item) for item in items], "total": len(items)})


@router.get("/prompts/issues", summary="二次优化可选问题清单")
def prompt_issues() -> dict:
    return ok({"items": prompt_builder.issue_choices()})
