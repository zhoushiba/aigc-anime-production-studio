"""Provider 注册表：业务层只依赖 get_provider(name)。"""

from __future__ import annotations

from app.config import settings
from app.services.providers.base import (
    BaseProvider,
    GenerationRequest,
    GenerationResult,
    ProviderError,
    ProviderNotConfigured,
    ProviderTimeout,
)
from app.services.providers.comfyui import ComfyUIProvider
from app.services.providers.mock import MockProvider
from app.services.providers.openai import OpenAIImageProvider

PROVIDERS: dict[str, BaseProvider] = {
    provider.name: provider
    for provider in (MockProvider(), ComfyUIProvider(), OpenAIImageProvider())
}


def get_provider(name: str | None = None) -> BaseProvider:
    key = (name or settings.default_provider or "mock").lower()
    provider = PROVIDERS.get(key)
    if provider is None:
        raise ProviderNotConfigured(f"未知的生成后端：{key}（可用：{', '.join(PROVIDERS)}）")
    return provider


def list_providers() -> list[dict]:
    return [provider.describe() for provider in PROVIDERS.values()]


__all__ = [
    "PROVIDERS",
    "BaseProvider",
    "GenerationRequest",
    "GenerationResult",
    "ProviderError",
    "ProviderNotConfigured",
    "ProviderTimeout",
    "get_provider",
    "list_providers",
]
