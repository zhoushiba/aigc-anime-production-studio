"""素材库数据访问与统计。"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.crud.common import get_or_404
from app.models import Asset, AssetRating, AssetRevision


def list_assets(
    db: Session,
    *,
    series_id: int | None = None,
    episode_id: int | None = None,
    shot_id: int | None = None,
    character_id: int | None = None,
    status: str = "",
    kind: str = "",
    keyword: str = "",
) -> object:
    stmt = select(Asset)
    if series_id:
        stmt = stmt.where(Asset.series_id == series_id)
    if episode_id:
        stmt = stmt.where(Asset.episode_id == episode_id)
    if shot_id:
        stmt = stmt.where(Asset.shot_id == shot_id)
    if character_id:
        stmt = stmt.where(Asset.character_id == character_id)
    if status:
        stmt = stmt.where(Asset.status == status)
    if kind:
        stmt = stmt.where(Asset.kind == kind)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Asset.title.like(like), Asset.prompt.like(like)))
    return stmt.order_by(Asset.id.desc())


def get_asset(db: Session, asset_id: int) -> Asset:
    return get_or_404(db, Asset, asset_id, "素材")


def add_rating(db: Session, asset: Asset, *, user_id: int | None, score: int, comment: str = "") -> AssetRating:
    rating = AssetRating(asset_id=asset.id, user_id=user_id, score=score, comment=comment)
    db.add(rating)
    asset.rating = score
    return rating


def add_revision(
    db: Session,
    asset: Asset,
    *,
    issues: list[str],
    fix_prompt: str,
    note: str = "",
    created_by: str = "",
    new_asset_id: int | None = None,
    task_id: int | None = None,
) -> AssetRevision:
    revision = AssetRevision(
        asset_id=asset.id,
        new_asset_id=new_asset_id,
        issues_json=list(issues),
        fix_prompt=fix_prompt,
        task_id=task_id,
        note=note,
        created_by=created_by,
    )
    db.add(revision)
    return revision


def revisions_of(db: Session, asset_id: int) -> list[AssetRevision]:
    return list(
        db.scalars(select(AssetRevision).where(AssetRevision.asset_id == asset_id).order_by(AssetRevision.id)).all()
    )


def asset_stats(db: Session) -> dict:
    total = int(db.scalar(select(func.count()).select_from(Asset)) or 0)
    by_status = {
        status: int(count)
        for status, count in db.execute(select(Asset.status, func.count()).group_by(Asset.status)).all()
    }
    by_kind = {
        kind: int(count)
        for kind, count in db.execute(select(Asset.kind, func.count()).group_by(Asset.kind)).all()
    }
    avg_rating = db.scalar(select(func.avg(Asset.rating)).where(Asset.rating > 0))
    total_size = int(db.scalar(select(func.sum(Asset.file_size))) or 0)
    return {
        "total": total,
        "by_status": by_status,
        "by_kind": by_kind,
        "selected": by_status.get("selected", 0),
        "candidate": by_status.get("candidate", 0),
        "rejected": by_status.get("rejected", 0),
        "avg_rating": round(float(avg_rating or 0), 2),
        "total_size_mb": round(total_size / 1024 / 1024, 2),
    }
