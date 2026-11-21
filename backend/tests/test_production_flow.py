"""AIGC 生成 / 素材库 / 合成单 / 审核 / 看板 相关用例（覆盖真实生成产物与导出文件）。"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings


def _create_task(client: TestClient, auth: dict[str, str], **overrides) -> dict:
    payload = {
        "prompt": "silver haired girl on a lighthouse, cel shading anime style, cinematic lighting",
        "negative_prompt": "lowres, bad anatomy",
        "kind": "text2image",
        "params": {"steps": 20, "cfg_scale": 6.5},
    }
    payload.update(overrides)
    response = client.post("/api/generation/tasks", headers=auth, json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_generation_providers(client: TestClient, auth: dict[str, str]) -> None:
    response = client.get("/api/generation/providers", headers=auth)
    assert response.status_code == 200
    providers = {item["name"]: item for item in response.json()["data"]["items"]}
    assert providers["mock"]["available"] is True
    assert providers["mock"]["requires_network"] is False


def test_generation_task_succeeds_and_writes_file(
    client: TestClient, auth: dict[str, str], demo_episode: dict, demo_shots: list[dict]
) -> None:
    shot = demo_shots[0]
    task = _create_task(
        client,
        auth,
        series_id=demo_episode["series_id"],
        episode_id=demo_episode["id"],
        shot_id=shot["id"],
        seed=20240501,
    )
    assert task["status"] == "succeeded", task
    assert task["progress"] == 100
    assert task["asset_id"]
    assert task["duration_ms"] >= 0

    asset = client.get(f"/api/assets/{task['asset_id']}", headers=auth).json()["data"]
    assert asset["status"] == "candidate"
    assert asset["width"] > 0 and asset["height"] > 0
    assert asset["file_size"] > 0
    assert asset["url"].startswith("/media/")

    stored = Path(settings.storage_dir) / asset["file_path"]
    assert stored.exists() and stored.stat().st_size > 1000
    thumb = Path(settings.storage_dir) / asset["thumb_url"].replace("/media/", "")
    assert thumb.exists()

    shot_after = client.get(f"/api/shots/{shot['id']}", headers=auth).json()["data"]
    assert shot_after["asset_id"] == asset["id"]
    assert shot_after["status"] == "generated"


def test_generation_task_detail_is_finished(client: TestClient, auth: dict[str, str]) -> None:
    task = _create_task(client, auth)
    detail = client.get(f"/api/generation/tasks/{task['id']}", headers=auth).json()["data"]
    assert detail["finished"] is True
    assert detail["status"] in ("succeeded", "failed", "timeout")


def test_generation_timeout_marker(client: TestClient, auth: dict[str, str]) -> None:
    task = _create_task(client, auth, params={"force_timeout": True})
    assert task["status"] == "timeout"
    assert "超时" in task["error"]


def test_generation_unknown_provider_fails(client: TestClient, auth: dict[str, str]) -> None:
    task = _create_task(client, auth, provider="no_such_provider")
    assert task["status"] == "failed"
    assert task["error"]


def test_cannot_cancel_finished_task(client: TestClient, auth: dict[str, str]) -> None:
    task = _create_task(client, auth)
    response = client.post(f"/api/generation/tasks/{task['id']}/cancel", headers=auth)
    assert response.status_code == 409
    assert response.json()["code"] == 40900


def test_task_retry(client: TestClient, auth: dict[str, str]) -> None:
    task = _create_task(client, auth)
    response = client.post(f"/api/generation/tasks/{task['id']}/retry", headers=auth, json={"params": {"steps": 12}})
    assert response.status_code == 200, response.text
    new_task = response.json()["data"]
    assert new_task["id"] != task["id"]
    assert new_task["params"]["steps"] == 12


def test_assets_list_stats_and_filters(client: TestClient, auth: dict[str, str], demo_episode: dict) -> None:
    listed = client.get("/api/assets", headers=auth, params={"episode_id": demo_episode["id"], "size": 50})
    assert listed.status_code == 200
    data = listed.json()["data"]
    assert data["total"] >= 2

    stats = client.get("/api/assets/stats", headers=auth).json()["data"]
    assert stats["total"] >= 2
    assert stats["selected"] >= 1
    assert stats["avg_rating"] >= 0


def test_asset_rate_and_rename(client: TestClient, auth: dict[str, str], demo_episode: dict) -> None:
    assets = client.get("/api/assets", headers=auth, params={"episode_id": demo_episode["id"]}).json()["data"]["items"]
    asset = assets[0]
    rated = client.post(f"/api/assets/{asset['id']}/rate", headers=auth, json={"score": 5, "comment": "光影很好"})
    assert rated.status_code == 200
    assert rated.json()["data"]["rating"] == 5

    renamed = client.patch(f"/api/assets/{asset['id']}", headers=auth, json={"title": "灯塔特写 v2"})
    assert renamed.json()["data"]["title"] == "灯塔特写 v2"


def test_asset_revise_creates_new_asset(client: TestClient, auth: dict[str, str], demo_episode: dict) -> None:
    assets = client.get("/api/assets", headers=auth, params={"episode_id": demo_episode["id"]}).json()["data"]["items"]
    asset = assets[0]
    response = client.post(
        f"/api/assets/{asset['id']}/revise",
        headers=auth,
        json={"issues": ["hand_broken", "blurry"], "note": "手部需要修"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert "perfect detailed hands" in data["revision"]["fix_prompt"]
    assert data["revision"]["issues"] == ["hand_broken", "blurry"]
    assert data["task"]["status"] == "succeeded"
    assert data["new_asset"]["id"] != asset["id"]

    history = client.get(f"/api/assets/{asset['id']}/revisions", headers=auth).json()["data"]
    assert history["total"] >= 1


def test_asset_batch_select(client: TestClient, auth: dict[str, str], demo_episode: dict) -> None:
    assets = client.get("/api/assets", headers=auth, params={"episode_id": demo_episode["id"]}).json()["data"]["items"]
    ids = [item["id"] for item in assets[:2]]
    response = client.post("/api/assets/batch", headers=auth, json={"ids": ids, "action": "select"})
    assert response.status_code == 200, response.text
    assert all(item["status"] == "selected" for item in response.json()["data"]["updated"])


def test_timeline_autofill_and_summary(client: TestClient, auth: dict[str, str], demo_episode: dict) -> None:
    response = client.get(f"/api/episodes/{demo_episode['id']}/timeline", headers=auth)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["summary"]["shot_count"] >= 8
    assert data["summary"]["total_duration"] > 0
    assert data["timeline"]["name"]

    refilled = client.post(f"/api/episodes/{demo_episode['id']}/timeline/auto-fill", headers=auth)
    assert refilled.status_code == 200
    assert refilled.json()["data"]["summary"]["shot_count"] >= data["summary"]["shot_count"]


def test_timeline_item_update_and_move(client: TestClient, auth: dict[str, str], demo_episode: dict) -> None:
    items = client.get(f"/api/episodes/{demo_episode['id']}/timeline", headers=auth).json()["data"]["items"]
    item = items[1]
    patched = client.patch(
        f"/api/timeline-items/{item['id']}",
        headers=auth,
        json={"subtitle": "林澈：灯塔还亮着。", "transition": "dissolve", "duration_seconds": 6.5},
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["transition"] == "dissolve"

    moved = client.post(f"/api/timeline-items/{item['id']}/move", headers=auth, json={"direction": "up"})
    assert moved.status_code == 200
    assert [row["seq"] for row in moved.json()["data"]["items"]] == list(
        range(1, len(moved.json()["data"]["items"]) + 1)
    )


def test_export_all_formats(client: TestClient, auth: dict[str, str], demo_episode: dict) -> None:
    csv_resp = client.get(f"/api/episodes/{demo_episode['id']}/export", headers=auth, params={"format": "csv"})
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    assert "镜号" in csv_resp.content.decode("utf-8-sig")

    json_resp = client.get(f"/api/episodes/{demo_episode['id']}/export", headers=auth, params={"format": "json"})
    assert json_resp.status_code == 200
    assert "shots" in json_resp.json()

    srt_resp = client.get(f"/api/episodes/{demo_episode['id']}/export", headers=auth, params={"format": "srt"})
    assert srt_resp.status_code == 200
    assert "-->" in srt_resp.content.decode("utf-8")

    zip_resp = client.get(f"/api/episodes/{demo_episode['id']}/export", headers=auth, params={"format": "zip"})
    assert zip_resp.status_code == 200
    assert zip_resp.content[:2] == b"PK"


def test_export_job_and_download(client: TestClient, auth: dict[str, str], demo_episode: dict) -> None:
    created = client.post(f"/api/episodes/{demo_episode['id']}/exports", headers=auth, json={"format": "zip"})
    assert created.status_code == 200, created.text
    job = created.json()["data"]
    assert job["payload"]["format"] == "zip"
    assert job["payload"]["shot_count"] >= 8

    downloaded = client.get(f"/api/exports/{job['id']}/download", headers=auth)
    assert downloaded.status_code == 200
    assert downloaded.content[:2] == b"PK"


def test_quality_checklist(client: TestClient, auth: dict[str, str], demo_episode: dict) -> None:
    response = client.get(f"/api/episodes/{demo_episode['id']}/checklist", headers=auth)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 8
    first = data["items"][0]
    patched = client.patch(
        f"/api/checklist/{first['id']}", headers=auth, json={"checked": True, "note": "已逐镜头核对发型与瞳色"}
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["checked"] is True
    assert patched.json()["data"]["checked_by"] == "林导"


def test_reviews_pending_and_decide(client: TestClient, auth: dict[str, str]) -> None:
    listed = client.get("/api/reviews", headers=auth, params={"status": "pending"}).json()["data"]
    assert listed["total"] >= 1
    review = listed["items"][0]

    decided = client.post(
        f"/api/reviews/{review['id']}/decide", headers=auth, json={"approve": True, "comment": "分镜节奏可以，进入生成"}
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["data"]["status"] == "approved"
    assert decided.json()["data"]["reviewer_name"] == "林导"

    again = client.post(f"/api/reviews/{review['id']}/decide", headers=auth, json={"approve": False})
    assert again.status_code == 409


def test_review_submit_for_asset(client: TestClient, auth: dict[str, str], demo_episode: dict) -> None:
    asset = client.get("/api/assets", headers=auth, params={"episode_id": demo_episode["id"]}).json()["data"]["items"][0]
    created = client.post(
        "/api/reviews",
        headers=auth,
        json={"target_type": "asset", "target_id": asset["id"], "title": "素材复审", "comment": "请确认手部"},
    )
    assert created.status_code == 200, created.text
    assert created.json()["data"]["status"] == "pending"
    stats = client.get("/api/reviews/stats", headers=auth).json()["data"]
    assert stats["total"] >= 2


def test_generation_stats(client: TestClient, auth: dict[str, str]) -> None:
    stats = client.get("/api/generation/stats", headers=auth).json()["data"]
    assert stats["total"] >= 1
    assert 0 <= stats["success_rate"] <= 100
    assert stats["by_status"]


def test_dashboard_overview_and_trend(client: TestClient, auth: dict[str, str]) -> None:
    overview = client.get("/api/dashboard/overview", headers=auth)
    assert overview.status_code == 200, overview.text
    data = overview.json()["data"]
    assert data["series_total"] >= 1
    assert data["shot_total"] >= 8
    assert data["tasks"]["total"] >= 1
    assert data["assets"]["total"] >= 2
    assert data["series_progress"]
    assert data["recent_tasks"]

    trend = client.get("/api/dashboard/trend", headers=auth, params={"days": 7})
    assert trend.status_code == 200
    items = trend.json()["data"]["items"]
    assert len(items) == 7
    assert items[-1]["total"] >= 1
