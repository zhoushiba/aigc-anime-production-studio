"""认证 / 项目 / 剧本 / 分镜 / 提示词 / 元数据 相关用例。"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "ok"
    assert any(item["name"] == "mock" for item in data["providers"])


def test_login_and_me(client: TestClient) -> None:
    login = client.post("/api/auth/login", json={"username": "director", "password": "anime2025"})
    assert login.status_code == 200
    token = login.json()["data"]["token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["role"] == "director"


def test_login_wrong_password(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"username": "director", "password": "wrong-pass"})
    assert response.status_code == 401
    assert response.json()["code"] == 40101


def test_require_token(client: TestClient) -> None:
    response = client.get("/api/series")
    assert response.status_code == 401
    assert response.json()["code"] == 40100


def test_register_new_artist(client: TestClient) -> None:
    payload = {"username": "artist_test", "password": "pass1234", "display_name": "测试美术", "role": "artist"}
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["user"]["role"] == "artist"
    login = client.post("/api/auth/login", json={"username": "artist_test", "password": "pass1234"})
    assert login.status_code == 200


def test_register_duplicate_username(client: TestClient) -> None:
    payload = {"username": "director", "password": "pass1234", "role": "director"}
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["code"] == 40901


def test_register_validation_error(client: TestClient) -> None:
    response = client.post("/api/auth/register", json={"username": "ab", "password": "123"})
    assert response.status_code == 422
    assert response.json()["code"] == 42200


def test_seed_series_listed(client: TestClient, auth: dict[str, str]) -> None:
    response = client.get("/api/series", headers=auth)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] >= 1
    assert any(item["title"] == "星海拾光" for item in data["items"])


def test_series_detail_has_episodes(client: TestClient, auth: dict[str, str], demo_series: dict) -> None:
    response = client.get(f"/api/series/{demo_series['id']}", headers=auth)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["episodes"]) >= 1
    assert data["character_count"] >= 1


def test_series_not_found(client: TestClient, auth: dict[str, str]) -> None:
    response = client.get("/api/series/999999", headers=auth)
    assert response.status_code == 404
    assert response.json()["code"] == 40400


def test_create_and_update_series(client: TestClient, auth: dict[str, str]) -> None:
    created = client.post(
        "/api/series",
        headers=auth,
        json={
            "title": "测试短片：雨夜便利店",
            "genre": "治愈",
            "logline": "一个加班的人与便利店店员的三分钟",
            "episodes_planned": 1,
            "target_duration": 60,
            "style": "清新水彩",
            "platform": "vertical",
        },
    )
    assert created.status_code == 200, created.text
    series = created.json()["data"]
    assert series["status"] == "draft"

    updated = client.patch(
        f"/api/series/{series['id']}", headers=auth, json={"status": "in_production", "synopsis": "已立项"}
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["status"] == "in_production"
    assert updated.json()["data"]["synopsis"] == "已立项"


def test_episode_create_and_script_versions(
    client: TestClient, auth: dict[str, str], demo_series: dict, demo_episode: dict
) -> None:
    created = client.post(
        f"/api/series/{demo_series['id']}/episodes",
        headers=auth,
        json={"title": "第 4 集 · 测试新增", "summary": "用于测试分集与剧本版本"},
    )
    assert created.status_code == 200, created.text
    episode = created.json()["data"]

    first = client.put(
        f"/api/episodes/{episode['id']}/script",
        headers=auth,
        json={"content": "第一版剧本：林澈走进观测站。", "structure": "三幕式"},
    )
    assert first.status_code == 200
    assert first.json()["data"]["version"] == 1

    second = client.put(
        f"/api/episodes/{episode['id']}/script",
        headers=auth,
        json={"content": "第二版剧本：林澈发现灯塔是活的。", "structure": "三幕式"},
    )
    assert second.json()["data"]["version"] == 2

    versions = client.get(f"/api/episodes/{episode['id']}/script", headers=auth)
    assert versions.status_code == 200
    data = versions.json()["data"]
    assert len(data["versions"]) == 2
    assert data["script"]["version"] == 2


def test_scene_create_and_move(client: TestClient, auth: dict[str, str], demo_episode: dict) -> None:
    created = client.post(
        f"/api/episodes/{demo_episode['id']}/scenes",
        headers=auth,
        json={
            "title": "天台对话",
            "location": "旧公寓天台",
            "time_of_day": "夜",
            "characters": "林澈、苏眠",
            "action_text": "苏眠把望远镜递给林澈。",
            "dialogue": "苏眠：你听，星星在响。",
            "duration_seconds": 18,
        },
    )
    assert created.status_code == 200, created.text
    scene = created.json()["data"]

    patched = client.patch(f"/api/scenes/{scene['id']}", headers=auth, json={"mood": "安静"})
    assert patched.status_code == 200
    assert patched.json()["data"]["mood"] == "安静"

    moved = client.post(f"/api/scenes/{scene['id']}/move", headers=auth, json={"direction": "up"})
    assert moved.status_code == 200
    seqs = [item["seq"] for item in moved.json()["data"]["items"]]
    assert seqs == list(range(1, len(seqs) + 1))


def test_seeded_shots(client: TestClient, auth: dict[str, str], demo_shots: list[dict]) -> None:
    assert len(demo_shots) >= 8
    assert all(item["shot_no"] for item in demo_shots)
    assert any(item["asset_id"] for item in demo_shots)


def test_shot_create_update_move(client: TestClient, auth: dict[str, str], demo_episode: dict) -> None:
    created = client.post(
        f"/api/episodes/{demo_episode['id']}/shots",
        headers=auth,
        json={
            "shot_size": "特写",
            "camera_angle": "仰视",
            "camera_move": "推",
            "duration_seconds": 3.5,
            "description": "林澈的眼睛里映出星光",
            "dialogue": "林澈：它一直在等我们。",
            "bgm": "钢琴单音",
        },
    )
    assert created.status_code == 200, created.text
    shot = created.json()["data"]
    assert shot["status"] == "draft"

    patched = client.patch(f"/api/shots/{shot['id']}", headers=auth, json={"shot_size": "近景", "status": "prompted"})
    assert patched.status_code == 200
    assert patched.json()["data"]["shot_size"] == "近景"

    moved = client.post(f"/api/shots/{shot['id']}/move", headers=auth, json={"direction": "up"})
    assert moved.status_code == 200
    assert len(moved.json()["data"]["items"]) >= 9


def test_shot_reorder(client: TestClient, auth: dict[str, str], demo_episode: dict) -> None:
    items = client.get(f"/api/episodes/{demo_episode['id']}/shots", headers=auth).json()["data"]["items"]
    ordered = [item["id"] for item in items]
    response = client.post(
        f"/api/episodes/{demo_episode['id']}/shots/reorder",
        headers=auth,
        json={"ordered_ids": list(reversed(ordered))},
    )
    assert response.status_code == 200
    result = response.json()["data"]["items"]
    assert [item["id"] for item in result] == list(reversed(ordered))
    # 还原顺序，避免影响后续用例
    client.post(
        f"/api/episodes/{demo_episode['id']}/shots/reorder",
        headers=auth,
        json={"ordered_ids": ordered},
    )


def test_prompt_from_shot(client: TestClient, auth: dict[str, str], demo_shots: list[dict]) -> None:
    shot = demo_shots[0]
    response = client.post(
        f"/api/shots/{shot['id']}/prompt",
        headers=auth,
        json={"shot_id": shot["id"], "consistency": True, "save": True},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["prompt"]
    assert "cel shading" in data["prompt"]
    assert data["negative_prompt"]
    assert data["shot"]["status"] in ("prompted", "generated", "approved")


def test_prompt_builder_formula(client: TestClient, auth: dict[str, str], demo_series: dict) -> None:
    response = client.post(
        "/api/prompts/build",
        headers=auth,
        json={
            "subject": "银发少女站在灯塔顶端",
            "action": "回头看向镜头",
            "shot_size": "近景",
            "camera_angle": "仰视",
            "camera_move": "推",
            "style": "新海诚光色",
            "lighting": "夜晚霓虹",
            "consistency": True,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert "银发少女" in data["prompt"]
    assert data["parts"]["subject"] == "银发少女站在灯塔顶端"
    assert data["parts"]["shot"]
    assert data["style"]["key"]
    assert "lowres" in data["negative_prompt"]


def test_prompt_templates_and_issues(client: TestClient, auth: dict[str, str]) -> None:
    templates = client.get("/api/prompts/templates", headers=auth)
    assert templates.status_code == 200
    items = templates.json()["data"]["items"]
    assert len(items) >= 12
    assert all(item["is_builtin"] for item in items)

    issues = client.get("/api/prompts/issues", headers=auth)
    assert issues.status_code == 200
    assert len(issues.json()["data"]["items"]) == 8


def test_characters_crud(client: TestClient, auth: dict[str, str], demo_series: dict) -> None:
    listed = client.get(f"/api/series/{demo_series['id']}/characters", headers=auth)
    assert listed.status_code == 200
    assert len(listed.json()["data"]["items"]) >= 3

    created = client.post(
        f"/api/series/{demo_series['id']}/characters",
        headers=auth,
        json={
            "name": "测试角色",
            "role_type": "配角",
            "personality": "话少、怕光",
            "appearance_prompt": "short black hair, freckles, oversized hoodie",
            "lora_name": "test_lora_v1",
            "lora_weight": 0.7,
            "seed": 8888,
        },
    )
    assert created.status_code == 200, created.text
    character = created.json()["data"]
    patched = client.patch(f"/api/characters/{character['id']}", headers=auth, json={"voice": "少年音"})
    assert patched.json()["data"]["voice"] == "少年音"
    deleted = client.delete(f"/api/characters/{character['id']}", headers=auth)
    assert deleted.status_code == 200


def test_scene_cards(client: TestClient, auth: dict[str, str], demo_series: dict) -> None:
    response = client.get(f"/api/series/{demo_series['id']}/scene-cards", headers=auth)
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) >= 3
    assert any(item["seed"] for item in items)


def test_meta_options(client: TestClient) -> None:
    response = client.get("/api/meta/options")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["styles"]) >= 12
    assert data["shot_sizes"] == ["远景", "全景", "中景", "近景", "特写"]
    assert "三幕式" in [item["name"] for item in data["structures"]]
    assert len(data["quality_items"]) == 8
