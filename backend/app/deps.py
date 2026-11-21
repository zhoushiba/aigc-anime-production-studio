"""依赖注入：数据库会话、当前用户、角色权限、分页参数。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ForbiddenError, UnauthorizedError
from app.models import User
from app.security import decode_token

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> User:
    """解析 Bearer Token 并加载用户。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("缺少 Authorization 头或格式不是 Bearer Token")
    payload = decode_token(authorization.split(" ", 1)[1].strip())
    if not payload:
        raise UnauthorizedError("Token 无效或已过期")
    user = db.get(User, int(payload.get("sub", 0)))
    if user is None:
        raise UnauthorizedError("用户不存在")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str):
    """角色校验依赖工厂：管理员始终放行。"""

    def _checker(user: CurrentUser) -> User:
        if user.role != "admin" and user.role not in roles:
            raise ForbiddenError(f"需要角色之一：{', '.join(roles)}")
        return user

    return _checker


class PageParams:
    """分页参数：page 从 1 开始，size 上限 100。"""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="页码"),
        size: int = Query(20, ge=1, le=100, description="每页条数"),
    ) -> None:
        self.page = page
        self.size = size
        self.offset = (page - 1) * size


Pagination = Annotated[PageParams, Depends(PageParams)]
