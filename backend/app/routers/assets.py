"""素材库路由：列表 / 详情 / 评分 / 批量入选淘汰 / 二次优化重绘。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app import serializers
from app.crud import add_rating, add_revision, asset_stats, get_asset, list_assets, revisions_of
from app.crud.common import page_result, paginate
from app.deps import CurrentUser, DbSession
from app.errors import NotFoundError, ok
from app.schemas import AssetBatchRequest, AssetRateRequest, AssetReviseRequest, AssetUpdate, TaskCreate
from app.services import generation, prompt_builder

router = APIRouter(prefix="/assets", tags=["素材库"])


def _revision(obj) -> dict:
    return {
        "id": obj.id,
        "asset_id": obj.asset_id,
        "new_asset_id": obj.new_asset_id,
        "issues": obj.issues_json or [],
        "issues_labels": [prompt_builder.REVISION_LABELS.get(code, code) for code in (obj.issues_json or [])],
        "fix_prompt": obj.fix_prompt,
        "task_id": obj.task_id,
        "note": obj.note,
        "created_by": obj.created_by,
        "created_at": serializers.iso(obj.created_at),
    }


@router.get("", summary="素材列表（按项目 / 分集 / 分镜 / 角色 / 状态过滤）")
def list_assets_api(
    db: DbSession,
    page: int = Query(1, ge=1),
    size: int = Query(24, ge=1, le=100),
    series_id: int | None = None,
    episode_id: int | None = None,
    shot_id: int | None = None,
    character_id: int | None = None,
    status: str = "",
    kind: str = "",
    keyword: str = "",
) -> dict:
    stmt = list_assets(
        db,
        series_id=series_id,
        episode_id=episode_id,
        shot_id=shot_id,
        character_id=character_id,
        status=status,
        kind=kind,
        keyword=keyword,
    )
    rows, total = paginate(db, stmt, page, size)
    return ok(page_result([serializers.asset(db, row) for row in rows], total, page, size))


@router.get("/stats", summary="素材统计：入选 / 淘汰 / 平均评分 / 体积")
def stats(db: DbSession) -> dict:
    return ok(asset_stats(db))


@router.get("/{asset_id}", summary="素材详情（含二次优化历史）")
def asset_detail(asset_id: int, db: DbSession) -> dict:
    asset = get_asset(db, asset_id)
    history = revisions_of(db, asset.id)
    return ok({**serializers.asset(db, asset), "revisions": [_revision(item) for item in history]})


@router.patch("/{asset_id}", summary="重命名 / 标记入选淘汰 / 审核备注")
def update_asset(asset_id: int, payload: AssetUpdate, db: DbSession) -> dict:
    asset = get_asset(db, asset_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return ok(serializers.asset(db, asset), "已保存")


@router.post("/{asset_id}/rate", summary="给素材打分（1-5 星 + 评语）")
def rate_asset(asset_id: int, payload: AssetRateRequest, db: DbSession, user: CurrentUser) -> dict:
    asset = get_asset(db, asset_id)
    add_rating(db, asset, user_id=user.id, score=payload.score, comment=payload.comment)
    db.commit()
    db.refresh(asset)
    return ok(serializers.asset(db, asset), "评分已记录")


@router.get("/{asset_id}/revisions", summary="二次优化记录")
def list_revisions(asset_id: int, db: DbSession) -> dict:
    asset = get_asset(db, asset_id)
    items = revisions_of(db, asset.id)
    return ok({"items": [_revision(item) for item in items], "total": len(items)})


@router.post("/{asset_id}/revise", summary="二次优化：标注问题 → 追加修正词 → 重绘 → 与原图关联")
def revise_asset(asset_id: int, payload: AssetReviseRequest, db: DbSession, user: CurrentUser) -> dict:
    asset = get_asset(db, asset_id)
    fix_prompt = prompt_builder.fix_prompt(asset.prompt, payload.issues)
    kind = "img2video" if asset.kind == "animation" else "text2image"
    task = generation.create_task(
        db,
        TaskCreate(
            prompt=fix_prompt,
            negative_prompt=asset.negative_prompt,
            kind=kind,
            provider=asset.provider,
            series_id=asset.series_id,
            episode_id=asset.episode_id,
            shot_id=asset.shot_id,
            character_id=asset.character_id,
            scene_card_id=asset.scene_card_id,
            params={"revision_of": asset.id, "steps": 28, "cfg_scale": 7.0},
        ),
        user,
    )
    revision = add_revision(
        db,
        asset,
        issues=payload.issues,
        fix_prompt=fix_prompt,
        note=payload.note,
        created_by=user.username,
        new_asset_id=task.asset_id,
        task_id=task.id,
    )
    db.commit()
    db.refresh(revision)
    new_asset = get_asset(db, revision.new_asset_id) if revision.new_asset_id else None
    return ok(
        {
            "original": serializers.asset(db, asset),
            "revision": _revision(revision),
            "task": serializers.task(db, task),
            "new_asset": serializers.asset(db, new_asset) if new_asset is not None else None,
        },
        "已按修正词重绘",
    )


@router.post("/batch", summary="批量操作：入选 / 淘汰 / 归档 / 按原提示词重绘")
def batch_action(payload: AssetBatchRequest, db: DbSession, user: CurrentUser) -> dict:
    mapping = {"select": "selected", "reject": "rejected", "archive": "archived"}
    updated: list[dict] = []
    created_tasks: list[dict] = []
    for asset_id in payload.ids:
        asset = get_asset(db, asset_id)
        if payload.action == "regenerate":
            task = generation.create_task(
                db,
                TaskCreate(
                    prompt=asset.prompt,
                    negative_prompt=asset.negative_prompt,
                    kind="img2video" if asset.kind == "animation" else "text2image",
                    provider=asset.provider,
                    series_id=asset.series_id,
                    episode_id=asset.episode_id,
                    shot_id=asset.shot_id,
                    character_id=asset.character_id,
                    scene_card_id=asset.scene_card_id,
                    params={**(asset.meta_json or {}), "regenerate_of": asset.id},
                ),
                user,
            )
            created_tasks.append(serializers.task(db, task))
        else:
            asset.status = mapping[payload.action]
            updated.append(serializers.asset(db, asset))
    db.commit()
    return ok(
        {"updated": updated, "tasks": created_tasks, "count": len(payload.ids)},
        "批量操作完成",
    )
