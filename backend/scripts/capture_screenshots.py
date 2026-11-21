"""用 Edge 无头模式给运行中的应用截真实截图（登录页/看板/分镜/素材库）。

前置：后端已在 8000 端口运行，且 frontend/dist 已构建（后端会托管 dist）。

用法（在 backend 目录）：python scripts/capture_screenshots.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

PROJECT_DIR = Path(__file__).resolve().parents[2]
SHOT_DIR = PROJECT_DIR / "docs" / "screenshots"
EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
BASE_URL = "http://127.0.0.1:8000"


def find_edge() -> str:
    for path in EDGE_CANDIDATES:
        if Path(path).exists():
            return path
    found = shutil.which("msedge")
    if found:
        return found
    raise SystemExit("未找到 Edge，可用 --browser 指定 Chromium 内核浏览器路径")


def wait_health(timeout: float = 120.0) -> dict:
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        try:
            response = httpx.get(f"{BASE_URL}/health", timeout=3.0)
            if response.status_code == 200:
                return response.json()["data"]
            last_error = f"status={response.status_code}"
        except Exception as exc:  # noqa: BLE001 - 启动期连接失败属正常
            last_error = str(exc)
        time.sleep(1.0)
    raise SystemExit(f"后端未就绪：{last_error}")


def resolve_ids() -> tuple[int, int]:
    """登录后取第一个项目与它的第一集，用于分镜页面的 hash 路由。"""
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        login = client.post("/api/auth/login", json={"username": "director", "password": "anime2025"})
        login.raise_for_status()
        token = login.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}
        series_list = client.get("/api/series", headers=headers).json()["data"]["items"]
        if not series_list:
            raise SystemExit("没有可用项目，请检查种子数据")
        series_id = series_list[0]["id"]
        detail = client.get(f"/api/series/{series_id}", headers=headers).json()["data"]
        episodes = detail.get("episodes") or []
        if not episodes:
            raise SystemExit("项目下没有分集，请检查种子数据")
        return series_id, episodes[0]["id"]


def shot(edge: str, name: str | None, url: str, profile: str, width: int = 1440, height: int = 900) -> Path | None:
    """用指定的浏览器 profile 打开页面；name 为空时只预热（不截图，用于把 token 写进 profile）。"""
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    target = SHOT_DIR / name if name else None
    command = [
        edge,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--force-device-scale-factor=1",
        f"--window-size={width},{height}",
        f"--user-data-dir={profile}",
        "--virtual-time-budget=20000",
    ]
    if target is not None:
        command.append(f"--screenshot={target}")
    command.append(url)
    subprocess.run(command, capture_output=True, timeout=240, check=False)
    if target is None:
        return None
    if not target.exists() or target.stat().st_size < 2000:
        raise SystemExit(f"截图失败：{name}")
    print(f"已生成 {target.name}（{target.stat().st_size // 1024} KB）")
    return target


def main() -> None:
    edge = sys.argv[1] if len(sys.argv) > 1 else find_edge()
    health = wait_health()
    print(f"后端就绪：{health['app']} v{health['version']} · providers={health.get('providers')}")
    series_id, episode_id = resolve_ids()
    print(f"使用种子项目 #{series_id}、分集 #{episode_id}")

    # 登录页用干净的 profile（没有 token 才会停在登录表单）
    shot(edge, "01-login.png", f"{BASE_URL}/#/login", tempfile.mkdtemp(prefix="aigc-shot-login-"))

    # 其余页面共用一个 profile：先预热一次完成登录（token 落进 localStorage），
    # 之后每次打开都直接进入目标页，避免「登录请求未完成就截图」的竞态。
    profile = tempfile.mkdtemp(prefix="aigc-shot-app-")
    shot(edge, None, f"{BASE_URL}/#/login?demo=1&next=/dashboard", profile)

    pages = [
        ("02-dashboard.png", f"{BASE_URL}/#/dashboard"),
        ("03-storyboard.png", f"{BASE_URL}/#/episodes/{episode_id}/storyboard"),
        ("04-assets.png", f"{BASE_URL}/#/assets"),
        ("05-series-detail.png", f"{BASE_URL}/#/series/{series_id}"),
        ("06-tasks.png", f"{BASE_URL}/#/tasks"),
    ]
    for name, url in pages:
        shot(edge, name, url, profile)


if __name__ == "__main__":
    main()
