"""元数据路由：把常量字典暴露给前端，避免前后端枚举漂移。"""

from __future__ import annotations

from fastapi import APIRouter

from app.constants import (
    ASSET_STATUS_LABELS,
    CAMERA_MOVES,
    EPISODE_STATUS_LABELS,
    GENRES,
    GENERATION_KINDS,
    QUALITY_ITEMS,
    SERIES_STATUS_LABELS,
    SHOT_SIZES,
    STRUCTURE_TEMPLATES,
    TASK_STATUS_LABELS,
    TRANSITIONS,
)
from app.errors import ok
from app.serializers import PLATFORM_LABELS, ROLE_LABELS
from app.services.prompt_builder import issue_choices, style_choices
from app.services.providers import list_providers

router = APIRouter(prefix="/meta", tags=["元数据"])

CAMERA_ANGLES = ["平视", "俯视", "仰视", "斜视", "主观"]


@router.get("/options", summary="全站下拉选项：题材/画风/镜头语言/状态标签/生成服务商")
def options() -> dict:
    return ok(
        {
            "genres": list(GENRES),
            "styles": style_choices(),
            "shot_sizes": list(SHOT_SIZES),
            "camera_angles": CAMERA_ANGLES,
            "camera_moves": list(CAMERA_MOVES),
            "transitions": [{"key": key, "label": label} for key, label in TRANSITIONS.items()],
            "platforms": [{"key": key, "label": label} for key, label in PLATFORM_LABELS.items()],
            "roles": [{"key": key, "label": label} for key, label in ROLE_LABELS.items()],
            "series_status": SERIES_STATUS_LABELS,
            "episode_status": EPISODE_STATUS_LABELS,
            "task_status": TASK_STATUS_LABELS,
            "asset_status": ASSET_STATUS_LABELS,
            "generation_kinds": [{"key": key, "label": label} for key, label in GENERATION_KINDS.items()],
            "structures": [
                {"key": key, "name": value.get("name", key), "description": value.get("description", ""),
                 "acts": value.get("acts", [])}
                for key, value in STRUCTURE_TEMPLATES.items()
            ],
            "quality_items": QUALITY_ITEMS,
            "revision_issues": issue_choices(),
            "providers": list_providers(),
        }
    )
