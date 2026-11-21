"""CRUD 公共工具。"""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.errors import NotFoundError


def paginate(db: Session, stmt: Select, page: int, size: int) -> tuple[Sequence[Any], int]:
    """返回 (当前页数据, 总数)。"""
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(stmt.limit(size).offset((page - 1) * size)).all()
    return rows, int(total)


def count_of(db: Session, stmt: Select) -> int:
    return int(db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)


def get_or_404(db: Session, model: Any, pk: int, label: str = "资源") -> Any:
    obj = db.get(model, pk)
    if obj is None:
        raise NotFoundError(f"{label}不存在（id={pk}）")
    return obj


def page_result(rows: Sequence[Any], total: int, page: int, size: int) -> dict:
    return {"items": list(rows), "total": total, "page": page, "size": size}
