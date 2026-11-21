"""离线 Mock 生成器：按 prompt + seed 确定性生成占位图，无网络依赖。"""

from __future__ import annotations

import hashlib

from PIL import Image

from app.services.image_utils import render_placeholder
from app.services.providers.base import (
    BaseProvider,
    GenerationRequest,
    GenerationResult,
    ProviderTimeout,
)


class MockProvider(BaseProvider):
    """把 prompt 的哈希当作「模型推理」，渲染一张确定性占位图。

    设计目标：让整条业务链路（任务 → 状态机 → 素材 → 合成单 → 审核）
    在没有 GPU、没有网络的环境下也能真实跑通；它不是「假装生成」——
    图片确实按 prompt/seed 计算出来，换 prompt 换 seed 图就不同。
    """

    name = "mock"
    label = "离线占位生成器"
    requires_network = False

    def available(self) -> bool:
        return True

    def generate(self, request: GenerationRequest) -> GenerationResult:
        # 支持 params.force_timeout：用于演示/测试超时分支
        if request.params.get("force_timeout"):
            raise ProviderTimeout("生成超时：超过任务截止时间（mock 强制超时标记）")

        digest = hashlib.sha256(
            f"{request.prompt}|{request.negative_prompt}|{request.seed}".encode("utf-8")
        ).hexdigest()
        steps = int(request.params.get("steps", 28))
        cfg = float(request.params.get("cfg_scale", 7.0))
        sampler = str(request.params.get("sampler", "dpmpp_2m"))

        image = render_placeholder(
            seed=request.seed,
            size=request.size,
            prompt=request.prompt,
            shot_label=request.shot_label,
            style_label=request.style_label,
            kind=request.params.get("kind", "text2image"),
            provider=self.name,
        )
        return GenerationResult(
            image=image,
            width=image.width,
            height=image.height,
            seed=request.seed,
            meta={
                "engine": "mock-diffusion/1.0",
                "sampler": sampler,
                "steps": steps,
                "cfg_scale": cfg,
                "prompt_hash": digest[:16],
                "negative_prompt": request.negative_prompt,
                "simulated": True,
            },
        )


__all__ = ["MockProvider", "Image"]
