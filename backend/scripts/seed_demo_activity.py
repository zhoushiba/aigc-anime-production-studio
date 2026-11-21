"""给演示数据补充一批真实的生成任务与素材（走 mock provider 真渲染），
让看板与素材库在打开时就处于「工作中」的状态。

用法（在 backend 目录，且后端已在 8000 运行）：
    python scripts/seed_demo_activity.py
"""
from __future__ import annotations

import random
import time

import httpx

BASE_URL = "http://127.0.0.1:8000"
SEEDS = [101, 202, 303, 404, 505, 606]


def wait_task(client: httpx.Client, headers: dict, task_id: int, timeout: float = 90.0) -> dict:
    deadline = time.time() + timeout
    detail: dict = {}
    while time.time() < deadline:
        detail = client.get(f"/api/generation/tasks/{task_id}", headers=headers).json()["data"]
        if detail["status"] in {"succeeded", "failed", "timeout", "canceled"}:
            return detail
        time.sleep(0.6)
    return detail


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        token = client.post(
            "/api/auth/login", json={"username": "director", "password": "anime2025"}
        ).json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        series_list = client.get("/api/series", headers=headers).json()["data"]["items"]
        demo = next((item for item in series_list if not item["title"].startswith("冒烟")), series_list[0])
        series_id = demo["id"]
        detail = client.get(f"/api/series/{series_id}", headers=headers).json()["data"]
        episode = detail["episodes"][0]
        episode_id = episode["id"]
        shots = client.get(f"/api/episodes/{episode_id}/shots", headers=headers).json()["data"]["items"]
        print(f"演示项目 #{series_id}《{demo['title']}》分集 #{episode_id}，分镜 {len(shots)} 个")

        rng = random.Random(20240501)
        created: list[dict] = []
        for index, shot in enumerate(shots[:6]):
            prompt = shot["prompt"] or f"{shot['description']}, cel shading anime style, cinematic lighting"
            task = client.post(
                "/api/generation/tasks",
                headers=headers,
                json={
                    "kind": "text2image",
                    "provider": "mock",
                    "series_id": series_id,
                    "episode_id": episode_id,
                    "shot_id": shot["id"],
                    "prompt": prompt,
                    "negative_prompt": shot["negative_prompt"] or "lowres, bad anatomy",
                    "seed": SEEDS[index % len(SEEDS)],
                    "params": {"steps": 28, "cfg_scale": 7.0, "sampler": "dpmpp_2m"},
                },
            ).json()["data"]
            result = wait_task(client, headers, task["id"])
            print(f"  分镜 {shot['shot_no']} -> 任务 #{task['id']} {result['status']}（{result['duration_ms']}ms）素材 #{result['asset_id']}")
            if result.get("asset_id"):
                created.append({"asset_id": result["asset_id"], "shot_no": shot["shot_no"]})
                rating = rng.choice([4, 5, 5, 3])
                client.post(
                    f"/api/assets/{result['asset_id']}/rate",
                    headers=headers,
                    json={"score": rating, "comment": "构图与光影可用"},
                )

        # 前两张入选，第三张淘汰，其余保持候选，让素材库有不同状态
        for position, item in enumerate(created):
            status = "selected" if position < 2 else ("rejected" if position == 2 else None)
            if status:
                client.patch(f"/api/assets/{item['asset_id']}", headers=headers, json={"status": status})
        print(f"素材状态：入选 {min(2, len(created))} 张、淘汰 {1 if len(created) > 2 else 0} 张")

        # 一条超时任务，演示失败分支（mock 通过 params.force_timeout 触发）
        timeout_task = client.post(
            "/api/generation/tasks",
            headers=headers,
            json={
                "kind": "text2image",
                "provider": "mock",
                "series_id": series_id,
                "episode_id": episode_id,
                "shot_id": shots[-1]["id"],
                "prompt": shots[-1]["prompt"] or "silhouette of a lighthouse keeper, cel shading anime style",
                "negative_prompt": "lowres",
                "seed": 777,
                "params": {"force_timeout": True},
            },
        ).json()["data"]
        timeout_result = wait_task(client, headers, timeout_task["id"])
        print(f"超时演示任务 #{timeout_task['id']} -> {timeout_result['status']}（{timeout_result['error']}）")

        stats = client.get("/api/generation/stats", headers=headers).json()["data"]
        overview = client.get("/api/dashboard/overview", headers=headers).json()["data"]
        print(
            f"任务统计：总数 {stats['total']}、成功 {stats['succeeded']}、超时 {stats['timeout']}、"
            f"成功率 {stats['success_rate']}%、平均 {stats['avg_duration_ms']}ms"
        )
        print(f"看板：项目 {overview['series_total']}、分镜 {overview['shot_total']}、素材 {overview['assets']['total']}")


if __name__ == "__main__":
    main()
