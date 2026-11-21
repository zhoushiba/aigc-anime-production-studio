"""认证路由：注册 / 登录 / 当前用户。"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app import serializers
from app.config import settings
from app.deps import CurrentUser, DbSession
from app.errors import ConflictError, UnauthorizedError, ok
from app.models import User
from app.schemas import LoginRequest, RegisterRequest
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["认证"])


def _issue_token(user: User) -> dict:
    token, expires_in = create_access_token(user.id, user.username, user.role)
    return {
        "token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": serializers.user(user),
    }


@router.post("/register", summary="注册（可选角色：导演/分镜师/美术/审核/学员）")
def register(payload: RegisterRequest, db: DbSession) -> dict:
    exists = db.scalar(select(User).where(User.username == payload.username))
    if exists is not None:
        raise ConflictError("用户名已被占用", code=40901)
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name or payload.username,
        role=payload.role or "student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return ok(_issue_token(user), "注册成功")


@router.post("/login", summary="登录，返回 JWT")
def login(payload: LoginRequest, db: DbSession) -> dict:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("用户名或密码错误", code=40101)
    return ok(_issue_token(user), "登录成功")


@router.get("/me", summary="当前登录用户")
def me(user: CurrentUser) -> dict:
    return ok({**serializers.user(user), "app_name": settings.app_name})
