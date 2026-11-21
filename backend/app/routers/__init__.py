"""路由聚合：所有业务模块统一从这里导出，main.py 逐个挂载。"""

from __future__ import annotations

from app.routers import (
    assets,
    auth,
    composition,
    dashboard,
    generation,
    meta,
    reviews,
    series,
    storyboard,
)

__all__ = [
    "assets",
    "auth",
    "composition",
    "dashboard",
    "generation",
    "meta",
    "reviews",
    "series",
    "storyboard",
]
