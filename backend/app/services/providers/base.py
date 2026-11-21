"""AIGC Provider 接口定义。

真实接入只需实现 BaseProvider.generate()，然后在 providers/__init__.py 注册。
本项目的默认实现是 MockProvider（离线可跑），ComfyUI / OpenAI 适配器给出
完整调用骨架，配置好地址即可切换。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from PIL import Image


class ProviderError(RuntimeError):
    """Provider 执行失败（会被任务状态机记为 failed）。"""


class ProviderNotConfigured(ProviderError):
    """Provider 需要的地址 / 密钥未配置。"""


class ProviderTimeout(ProviderError):
    """Provider 超过截止时间（会被任务状态机记为 timeout）。"""


@dataclass
class GenerationRequest:
    prompt: str
    negative_prompt: str = ""
    seed: int = 0
    size: tuple[int, int] = (720, 1280)
    params: dict[str, Any] = field(default_factory=dict)
    shot_label: str = ""
    style_label: str = ""


@dataclass
class GenerationResult:
    image: Image.Image
    width: int
    height: int
    seed: int
    meta: dict[str, Any] = field(default_factory=dict)


class BaseProvider(ABC):
    """所有生成后端的统一接口。"""

    name: str = "base"
    label: str = "基础后端"
    requires_network: bool = False

    @abstractmethod
    def available(self) -> bool:
        """是否具备执行条件（地址/密钥是否配置）。"""

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """执行一次生成；失败抛 ProviderError 子类。"""

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "available": self.available(),
            "requires_network": self.requires_network,
        }
