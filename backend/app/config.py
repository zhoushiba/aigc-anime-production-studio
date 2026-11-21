"""全局配置。

所有可变项都支持环境变量覆盖，默认值面向「本地一键跑通」：
数据库用 SQLite，素材落在 backend/storage 下，生成默认走离线 MockProvider。
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
PROJECT_DIR = BASE_DIR.parent                       # 仓库根目录


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "") or default)
    except ValueError:
        return default


class Settings:
    """运行期配置（读取一次环境变量，测试通过 conftest 提前注入）。"""

    app_name = "AIGC 动漫番剧制作工作台"
    app_version = "1.0.0"
    api_prefix = "/api"
    env = os.getenv("APP_ENV", "dev")

    database_url = os.getenv("DATABASE_URL") or f"sqlite:///{(BASE_DIR / 'data' / 'app.db').as_posix()}"
    db_echo = _env_bool("DB_ECHO", False)

    storage_dir = Path(os.getenv("STORAGE_DIR") or (BASE_DIR / "storage"))

    jwt_secret = os.getenv("JWT_SECRET", "dev-secret-change-me-in-production")
    jwt_algorithm = "HS256"
    token_expire_minutes = _env_int("TOKEN_EXPIRE_MINUTES", 60 * 12)

    # 生成任务：默认后台线程池执行；测试可切 inline 同步执行
    generation_inline = _env_bool("GENERATION_INLINE", False)
    generation_workers = _env_int("GENERATION_WORKERS", 2)
    generation_deadline_seconds = _env_int("GENERATION_DEADLINE_SECONDS", 60)
    default_provider = os.getenv("GENERATION_PROVIDER", "mock")

    # 真实服务接入（留空即视为不可用，降级提示见 docs/deployment.md）
    comfyui_base_url = os.getenv("COMFYUI_BASE_URL", "")
    comfyui_workflow_path = os.getenv("COMFYUI_WORKFLOW_PATH", "")
    openai_base_url = os.getenv("OPENAI_BASE_URL", "")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    openai_image_model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")

    # 演示账号（首次启动种子数据）
    demo_username = os.getenv("DEMO_USERNAME", "director")
    demo_password = os.getenv("DEMO_PASSWORD", "anime2025")
    seed_demo = _env_bool("SEED_DEMO", True)

    # 图像尺寸（竖屏短视频 / 横屏番剧）
    vertical_size = (720, 1280)
    horizontal_size = (1280, 720)
    thumb_width = 320

    @property
    def assets_dir(self) -> Path:
        return self.storage_dir / "assets"

    @property
    def thumbs_dir(self) -> Path:
        return self.storage_dir / "thumbs"

    @property
    def exports_dir(self) -> Path:
        return self.storage_dir / "exports"

    def ensure_dirs(self) -> None:
        for path in (self.assets_dir, self.thumbs_dir, self.exports_dir, BASE_DIR / "data"):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
