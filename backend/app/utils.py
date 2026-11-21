"""通用工具：时间、时长、SRT 时间码、文件名清洗。"""

from __future__ import annotations

import re
from datetime import datetime

_SAFE_NAME = re.compile(r"[^0-9A-Za-z\u4e00-\u9fa5._-]+")


def utcnow() -> datetime:
    """当前 UTC 时间（去掉时区信息，SQLite 友好）。"""
    return datetime.utcnow()


def human_duration(seconds: float) -> str:
    """把秒数格式化为 ``01:23`` 或 ``1:02:03``。"""
    total = int(round(seconds or 0))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def srt_timecode(seconds: float) -> str:
    """SRT 时间码 ``HH:MM:SS,mmm``。"""
    total_ms = int(round((seconds or 0) * 1000))
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def safe_filename(name: str, default: str = "untitled") -> str:
    """清洗文件名，去掉路径分隔符与不可见字符。"""
    cleaned = _SAFE_NAME.sub("_", (name or "").strip()).strip("._-")
    return cleaned[:80] or default


def chunk_text(text: str, size: int) -> list[str]:
    """按长度切分文本（导出字幕、提示词预览使用）。"""
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]
