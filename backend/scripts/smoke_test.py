"""端到端冒烟脚本：登录 → 建项目 → 建分集 → 存剧本 → 建场次 → 建分镜 →
生成素材 → 二次优化 → 合成单导出 → 提交审核 → 看板统计。

用法（在 backend 目录）：python scripts/smoke_test.py
前置：后端已在 8000 端口运行。
"""
from __future__ import annotations

import time

import httpx

BASE_URL = "http://127.0.0.1:8000"


def wait_health(timeout: float = 120.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if httpx.get(f"{BASE_URL}/health", timeout=3.0).status_code == 200:
                return
        except Exception:  # noqa: BLE001 - 启动期连接失败属正常
            pass
        time.sleep(1.0)
    raise SystemExit("后端未就绪")


def main() -> None:
    wait_health()
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        health = client.get("/health").json()["data"]
        print(f"[1] /health -> {health['status']} · {health['app']} v{health['version']} · providers={health['providers']}")

        login = client.post("/api/auth/login", json={"username": "director", "password": "anime2025"}).json()
        token = login["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"[2] 登录成功：{login['data']['user']['display_name']} / {login['data']['user']['role']}")

        series = client.post(
            "/api/series",
            headers=headers,
            json={
                "title": "冒烟验证项目（可删除）",
                "genre": "科幻",
                "logline": "用脚本验证从立项到出图的整条链路",
                "synopsis": "冒烟脚本自动创建",
                "episodes_planned": 1,
                "target_duration": 60,
                "style": "日系赛璐璐",
                "platform": "vertical",
            },
        ).json()["data"]
        series_id = series["id"]
        print(f"[3] 新建项目 #{series_id}：{series['title']}")

        episode = client.post(
            f"/api/series/{series_id}/episodes",
            headers=headers,
            json={"title": "第 1 集 冒烟分集", "summary": "冒烟"},
        ).json()["data"]
        episode_id = episode["id"]
        print(f"[4] 新建分集 #{episode_id}：{episode['title']}")

        script = client.put(
            f"/api/episodes/{episode_id}/script",
            headers=headers,
            json={"content": "第一幕：灯塔亮起。\n第二幕：少女转身。\n第三幕：星海之门开启。", "structure": "三幕式"},
        ).json()["data"]
        print(f"[5] 保存剧本 v{script['version']}（{len(script['content'])} 字）")

        scene = client.post(
            f"/api/episodes/{episode_id}/scenes",
            headers=headers,
            json={
                "title": "灯塔前的回望",
                "location": "废弃观测站",
                "time_of_day": "夜晚",
                "characters": "林澈",
                "action_text": "银发少女站在灯塔前缓缓回头，海风吹动发丝",
                "dialogue": "「这一次，我不会再逃。」",
                "mood": "安静而坚定",
                "duration_seconds": 18,
            },
        ).json()["data"]
        print(f"[6] 新建场次 #{scene['id']}：{scene['title']}（{scene['duration_seconds']}s）")

        shot = client.post(
            f"/api/episodes/{episode_id}/shots",
            headers=headers,
            json={
                "shot_size": "中景",
                "camera_angle": "仰视",
                "camera_move": "推",
                "duration_seconds": 6,
                "description": "银发少女站在灯塔前回头，海风吹动发丝",
                "dialogue": "「这一次，我不会再逃。」",
                "bgm": "温柔的钢琴",
            },
        ).json()["data"]
        shot_id = shot["id"]
        print(f"[7] 新建分镜 #{shot_id} {shot['shot_no']}：{shot['shot_size']}/{shot['camera_angle']}/{shot['camera_move']}")

        prompt = client.post(
            f"/api/shots/{shot_id}/prompt",
            headers=headers,
            json={"style": "日系赛璐璐", "save": True},
        ).json()["data"]
        print(f"[8] 生成提示词（{len(prompt['prompt'])} 字）：{prompt['prompt'][:110]}...")

        task = client.post(
            "/api/generation/tasks",
            headers=headers,
            json={
                "kind": "text2image",
                "provider": "mock",
                "series_id": series_id,
                "episode_id": episode_id,
                "shot_id": shot_id,
                "prompt": prompt["prompt"],
                "negative_prompt": prompt["negative_prompt"],
                "seed": 20240501,
                "params": {"steps": 24, "cfg_scale": 6.5},
            },
        ).json()["data"]
        task_id = task["id"]
        print(f"[9] 提交生成任务 #{task_id}：{task['status']}")

        detail = {}
        for _ in range(60):
            detail = client.get(f"/api/generation/tasks/{task_id}", headers=headers).json()["data"]
            print(f"    轮询 #{task_id} -> {detail['status']}（{detail['progress']}%）")
            if detail["status"] in {"succeeded", "failed", "timeout", "canceled"}:
                break
            time.sleep(1.0)
        asset_id = detail.get("asset_id")
        print(f"[10] 任务结束：{detail['status']}，耗时 {detail['duration_ms']}ms，素材 #{asset_id}")

        assets = client.get("/api/assets", headers=headers, params={"shot_id": shot_id}).json()["data"]
        print(f"[11] 该镜头素材 {assets['total']} 张：{assets['items'][0]['file_path']}")

        client.post(f"/api/assets/{asset_id}/rate", headers=headers, json={"score": 5, "comment": "构图与光影可用"})
        client.patch(f"/api/assets/{asset_id}", headers=headers, json={"status": "selected"})
        print("[12] 评分 5 星 + 入选")

        revision = client.post(
            f"/api/assets/{asset_id}/revise",
            headers=headers,
            json={"issues": ["hand_broken", "blurry"], "note": "手部结构崩坏，需要重绘双手"},
        ).json()["data"]
        revise_task_id = revision["task"]["id"]
        revise_detail = {}
        for _ in range(60):
            revise_detail = client.get(f"/api/generation/tasks/{revise_task_id}", headers=headers).json()["data"]
            if revise_detail["status"] in {"succeeded", "failed", "timeout", "canceled"}:
                break
            time.sleep(1.0)
        print(
            f"[13] 二次优化：追加修正词 -> ...{revision['revision']['fix_prompt'][-60:]!r}；"
            f"重绘任务 #{revise_task_id}={revise_detail['status']}，新素材 #{revise_detail['asset_id']}"
        )

        timeline = client.get(f"/api/episodes/{episode_id}/timeline", headers=headers).json()["data"]
        print(f"[14] 合成单「{timeline['timeline']['name']}」镜头 {timeline['summary']['shot_count']} 个、总时长 {timeline['summary']['total_duration']}s")

        exported = client.get(f"/api/episodes/{episode_id}/export", headers=headers, params={"format": "csv"})
        head = exported.content.decode("utf-8-sig").splitlines()[:2]
        print(f"[15] 导出 CSV {len(exported.content)} 字节；表头：{head[0]}")
        print(f"     第一行：{head[1][:120]}")

        checklist = client.get(f"/api/episodes/{episode_id}/checklist", headers=headers).json()["data"]
        print(f"[16] 质检清单 {len(checklist['items'])} 项；已勾选 {sum(1 for item in checklist['items'] if item['checked'])} 项")

        review = client.post(
            "/api/reviews",
            headers=headers,
            json={
                "series_id": series_id,
                "target_type": "episode",
                "target_id": episode_id,
                "title": "冒烟分集提交审核",
                "comment": "请审核分镜与素材一致性",
            },
        ).json()["data"]
        decided = client.post(
            f"/api/reviews/{review['id']}/decide",
            headers=headers,
            json={"approve": True, "comment": "通过，可进入下一阶段"},
        ).json()["data"]
        print(f"[17] 审核 #{review['id']}：{review['status']} -> {decided['status']}，审核人 {decided['reviewer_name']}")

        overview = client.get("/api/dashboard/overview", headers=headers).json()["data"]
        trend = client.get("/api/dashboard/trend", headers=headers, params={"days": 7}).json()["data"]
        print(
            f"[18] 看板：项目 {overview['series_total']}、分集 {overview['episode_total']}、分镜 {overview['shot_total']}、"
            f"素材 {overview['assets']['total']}、成功率 {overview['tasks']['success_rate']}%、"
            f"平均耗时 {overview['tasks']['avg_duration_ms']}ms、趋势点 {len(trend['items'])} 个"
        )
        print("\n冒烟通过：立项 → 剧本 → 场次 → 分镜 → 提示词 → 生成 → 素材 → 二次优化 → 合成单 → 导出 → 审核 → 看板")


if __name__ == "__main__":
    main()
