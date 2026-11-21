"""审核流路由：提交 → 通过 / 驳回（带意见）→ 状态回写目标对象。"""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app import serializers
from app.crud.common import page_result, paginate
from app.deps import CurrentUser, DbSession
from app.errors import ConflictError, NotFoundError, ok
from app.models import Asset, Episode, Review, Series, Timeline, utcnow
from app.schemas import ReviewCreate, ReviewDecision

router = APIRouter(prefix="/reviews", tags=["审核"])


@router.get("", summary="审核单列表")
def list_reviews(
    db: DbSession,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str = "",
    series_id: int | None = None,
    target_type: str = "",
) -> dict:
    stmt = select(Review)
    if status:
        stmt = stmt.where(Review.status == status)
    if series_id:
        stmt = stmt.where(Review.series_id == series_id)
    if target_type:
        stmt = stmt.where(Review.target_type == target_type)
    stmt = stmt.order_by(Review.id.desc())
    rows, total = paginate(db, stmt, page, size)
    return ok(page_result([serializers.review(row) for row in rows], total, page, size))


@router.get("/stats", summary="审核统计")
def review_stats(db: DbSession) -> dict:
    rows = db.execute(select(Review.status, func.count()).group_by(Review.status)).all()
    counts = {status: int(count) for status, count in rows}
    return ok({"total": sum(counts.values()), "by_status": counts, "pending": counts.get("pending", 0)})


@router.post("", summary="提交审核单")
def create_review(payload: ReviewCreate, db: DbSession, user: CurrentUser) -> dict:
    series_id: int | None = None
    title = payload.title
    if payload.target_type == "episode":
        episode = db.get(Episode, payload.target_id)
        if episode is None:
            raise NotFoundError("分集不存在")
        series_id = episode.series_id
        title = title or f"第 {episode.number} 集《{episode.title}》审核"
        episode.status = "review"
    elif payload.target_type == "asset":
        asset = db.get(Asset, payload.target_id)
        if asset is None:
            raise NotFoundError("素材不存在")
        series_id = asset.series_id
        title = title or f"素材 #{asset.id} 审核"
    elif payload.target_type == "timeline":
        timeline = db.get(Timeline, payload.target_id)
        if timeline is None:
            raise NotFoundError("合成单不存在")
        episode = db.get(Episode, timeline.episode_id)
        series_id = episode.series_id if episode is not None else None
        title = title or f"{timeline.name} 审核"
        timeline.status = "review"
    review = Review(
        series_id=series_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        title=title,
        status="pending",
        comment=payload.comment,
        submitted_by=user.display_name or user.username,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return ok(serializers.review(review), "已提交审核")


@router.get("/{review_id}", summary="审核单详情")
def review_detail(review_id: int, db: DbSession) -> dict:
    review = db.get(Review, review_id)
    if review is None:
        raise NotFoundError("审核单不存在")
    data = serializers.review(review)
    series = db.get(Series, review.series_id) if review.series_id else None
    data["series_title"] = series.title if series is not None else ""
    return ok(data)


@router.post("/{review_id}/decide", summary="通过 / 驳回并回写目标状态")
def decide(review_id: int, payload: ReviewDecision, db: DbSession, user: CurrentUser) -> dict:
    review = db.get(Review, review_id)
    if review is None:
        raise NotFoundError("审核单不存在")
    if review.status != "pending":
        raise ConflictError("该审核单已处理", code=40905)
    review.status = "approved" if payload.approve else "rejected"
    review.comment = payload.comment or review.comment
    review.reviewer_id = user.id
    review.reviewer_name = user.display_name or user.username
    review.decided_at = utcnow()

    if review.target_type == "episode":
        episode = db.get(Episode, review.target_id)
        if episode is not None:
            episode.status = "approved" if payload.approve else "storyboard"
    elif review.target_type == "timeline":
        timeline = db.get(Timeline, review.target_id)
        if timeline is not None:
            timeline.status = "approved" if payload.approve else "draft"
    elif review.target_type == "asset":
        asset = db.get(Asset, review.target_id)
        if asset is not None:
            asset.status = "selected" if payload.approve else "rejected"
            asset.review_note = payload.comment[:200]
    db.commit()
    db.refresh(review)
    return ok(serializers.review(review), "已通过" if payload.approve else "已驳回")
