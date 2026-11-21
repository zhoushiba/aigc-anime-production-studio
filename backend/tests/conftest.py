"""pytest 夹具：在导入 app 之前注入临时数据库 / 存储目录 / 同步生成模式。

这样测试完全跑在临时目录里，不会污染 backend/data 与 backend/storage。
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

_TMP = Path(tempfile.mkdtemp(prefix="aigc-studio-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'app.db').as_posix()}"
os.environ["STORAGE_DIR"] = str(_TMP / "storage")
os.environ["GENERATION_INLINE"] = "1"      # 同步执行，测试不需要轮询等待
os.environ["GENERATION_WORKERS"] = "1"
os.environ["SEED_DEMO"] = "1"
os.environ["JWT_SECRET"] = "test-secret-for-pytest"
os.environ["APP_ENV"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """带 lifespan 的测试客户端（触发建表 + 示例数据种子）。"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def auth(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": "director", "password": "anime2025"})
    assert response.status_code == 200, response.text
    token = response.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def demo_series(client: TestClient, auth: dict[str, str]) -> dict:
    response = client.get("/api/series", headers=auth)
    assert response.status_code == 200, response.text
    items = response.json()["data"]["items"]
    assert items, "示例剧集应当由种子数据创建"
    return items[0]


@pytest.fixture(scope="session")
def demo_episode(client: TestClient, auth: dict[str, str], demo_series: dict) -> dict:
    response = client.get(f"/api/series/{demo_series['id']}/episodes", headers=auth)
    assert response.status_code == 200, response.text
    items = response.json()["data"]["items"]
    assert items, "示例剧集应当带有分集"
    return items[0]


@pytest.fixture(scope="session")
def demo_shots(client: TestClient, auth: dict[str, str], demo_episode: dict) -> list[dict]:
    response = client.get(f"/api/episodes/{demo_episode['id']}/shots", headers=auth)
    assert response.status_code == 200, response.text
    return response.json()["data"]["items"]
