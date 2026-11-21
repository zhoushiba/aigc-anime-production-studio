"""ComfyUI 适配器骨架。

真实用法：把 ComfyUI 的 API-format workflow 导出成 JSON，替换其中文本框的
节点 id 与 CLIPTextEncode 的输入，提交 /prompt，再轮询 /history/{prompt_id}。

当前仓库不随附 workflow（避免提交无关大文件），因此未配置
COMFYUI_BASE_URL + COMFYUI_WORKFLOW_PATH 时会抛 ProviderNotConfigured，
业务层将其捕获为 failed 任务并给出可读提示。
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.services.image_utils import load_font  # noqa: F401  保持与 mock 相同的依赖集合
from app.services.providers.base import (
    BaseProvider,
    GenerationRequest,
    GenerationResult,
    ProviderError,
    ProviderNotConfigured,
    ProviderTimeout,
)


class ComfyUIProvider(BaseProvider):
    name = "comfyui"
    label = "ComfyUI（本地/局域网 GPU）"
    requires_network = True

    def available(self) -> bool:
        return bool(settings.comfyui_base_url and settings.comfyui_workflow_path)

    def _load_workflow(self) -> dict[str, Any]:
        path = Path(settings.comfyui_workflow_path)
        if not path.exists():
            raise ProviderNotConfigured(f"找不到 ComfyUI workflow 文件：{path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _patch_workflow(self, workflow: dict[str, Any], request: GenerationRequest) -> dict[str, Any]:
        """把 prompt / 负向词 / seed / 尺寸写进 workflow 的文本与采样节点。"""
        patched = json.loads(json.dumps(workflow))
        for node in patched.values():
            class_type = node.get("class_type", "")
            inputs = node.setdefault("inputs", {})
            if class_type in {"CLIPTextEncode", "CLIPTextEncodeSDXL"}:
                text = str(inputs.get("text", ""))
                if "负面" in text or "negative" in text.lower():
                    inputs["text"] = request.negative_prompt
                else:
                    inputs["text"] = request.prompt
            if class_type in {"KSampler", "KSamplerAdvanced"}:
                inputs["seed"] = request.seed
                if "steps" in inputs:
                    inputs["steps"] = int(request.params.get("steps", inputs["steps"]))
                if "cfg" in inputs:
                    inputs["cfg"] = float(request.params.get("cfg_scale", inputs["cfg"]))
            if class_type in {"EmptyLatentImage", "EmptySD3LatentImage"}:
                inputs["width"] = request.size[0]
                inputs["height"] = request.size[1]
        return patched

    def generate(self, request: GenerationRequest) -> GenerationResult:  # pragma: no cover - 需真实服务
        if not self.available():
            raise ProviderNotConfigured(
                "ComfyUI 未配置：请设置 COMFYUI_BASE_URL 与 COMFYUI_WORKFLOW_PATH 后重启服务"
            )
        base = settings.comfyui_base_url.rstrip("/")
        workflow = self._patch_workflow(self._load_workflow(), request)
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(f"{base}/prompt", json={"prompt": workflow})
                resp.raise_for_status()
                prompt_id = resp.json().get("prompt_id")
                if not prompt_id:
                    raise ProviderError(f"ComfyUI 未返回 prompt_id：{resp.text[:200]}")

                deadline = time.time() + settings.generation_deadline_seconds
                while time.time() < deadline:
                    history = client.get(f"{base}/history/{prompt_id}")
                    history.raise_for_status()
                    data = history.json().get(prompt_id)
                    if data:
                        images = []
                        for output in data.get("outputs", {}).values():
                            images.extend(output.get("images", []))
                        if not images:
                            raise ProviderError("ComfyUI 任务完成但没有输出图片")
                        info = images[0]
                        img_resp = client.get(
                            f"{base}/view",
                            params={"filename": info["filename"], "subfolder": info.get("subfolder", ""), "type": "output"},
                        )
                        img_resp.raise_for_status()
                        from io import BytesIO

                        from PIL import Image

                        image = Image.open(BytesIO(img_resp.content)).convert("RGB")
                        return GenerationResult(
                            image=image,
                            width=image.width,
                            height=image.height,
                            seed=request.seed,
                            meta={"engine": "comfyui", "prompt_id": prompt_id, "filename": info["filename"]},
                        )
                    time.sleep(1.0)
        except httpx.HTTPError as exc:
            raise ProviderError(f"ComfyUI 请求失败：{exc}") from exc
        raise ProviderTimeout("ComfyUI 生成超时")
