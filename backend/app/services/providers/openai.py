"""OpenAI 图像接口（gpt-image-1 / dall-e-3）适配器骨架。

配置 OPENAI_BASE_URL + OPENAI_API_KEY 后即可切换；未配置时抛 ProviderNotConfigured。
"""

from __future__ import annotations

import base64
import io

from PIL import Image

from app.config import settings
from app.services.providers.base import (
    BaseProvider,
    GenerationRequest,
    GenerationResult,
    ProviderError,
    ProviderNotConfigured,
)


class OpenAIImageProvider(BaseProvider):
    name = "openai"
    label = "OpenAI 图像接口"
    requires_network = True

    def available(self) -> bool:
        return bool(settings.openai_base_url and settings.openai_api_key)

    def generate(self, request: GenerationRequest) -> GenerationResult:  # pragma: no cover - 需真实密钥
        if not self.available():
            raise ProviderNotConfigured("OpenAI 未配置：请设置 OPENAI_BASE_URL 与 OPENAI_API_KEY 后重启服务")

        import httpx

        size = request.params.get("openai_size")
        if not size:
            size = "1024x1536" if request.size[1] >= request.size[0] else "1536x1024"
        payload = {
            "model": settings.openai_image_model,
            "prompt": request.prompt if not request.negative_prompt else f"{request.prompt}\n避免出现：{request.negative_prompt}",
            "size": size,
            "n": 1,
        }
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(
                    f"{settings.openai_base_url.rstrip('/')}/images/generations",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()["data"][0]
        except httpx.HTTPError as exc:
            raise ProviderError(f"OpenAI 图像接口调用失败：{exc}") from exc
        except (KeyError, IndexError) as exc:
            raise ProviderError("OpenAI 返回结构异常：缺少 data[0]") from exc

        if data.get("b64_json"):
            raw = base64.b64decode(data["b64_json"])
        elif data.get("url"):
            import httpx as _httpx

            with _httpx.Client(timeout=60.0) as client:
                raw = client.get(data["url"]).content
        else:
            raise ProviderError("OpenAI 未返回图片内容")

        image = Image.open(io.BytesIO(raw)).convert("RGB")
        return GenerationResult(
            image=image,
            width=image.width,
            height=image.height,
            seed=request.seed,
            meta={"engine": f"openai:{settings.openai_image_model}", "revised_prompt": data.get("revised_prompt", "")},
        )
