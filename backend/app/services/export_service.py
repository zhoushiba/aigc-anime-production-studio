"""合成单导出：CSV / JSON / SRT / ZIP，全部基于数据库里的真实镜头数据。"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from typing import Any

from app.constants import TRANSITIONS

_CSV_HEADER = [
    "序号",
    "镜号",
    "景别",
    "机位",
    "运镜",
    "时长(秒)",
    "画面描述",
    "台词/字幕",
    "转场",
    "BGM/音效",
    "素材文件",
]


def _transition_label(value: str) -> str:
    if isinstance(TRANSITIONS, dict):
        entry = TRANSITIONS.get(value)
        if isinstance(entry, dict):
            return str(entry.get("label") or value)
        if isinstance(entry, str):
            return entry
    if isinstance(TRANSITIONS, list):
        for item in TRANSITIONS:
            if isinstance(item, dict) and item.get("key") == value:
                return str(item.get("label") or value)
    return value


def _accumulate(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把每条镜头换算成起止时间（秒），用于 SRT 与时间轴。"""
    cursor = 0.0
    for item in items:
        duration = float(item.get("duration_seconds") or 0)
        item["start"] = round(cursor, 2)
        cursor += duration
        item["end"] = round(cursor, 2)
    return items


def _srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hours, ms = divmod(ms, 3600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def build_csv(items: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_CSV_HEADER)
    for item in items:
        writer.writerow(
            [
                item.get("seq", ""),
                item.get("shot_no", ""),
                item.get("shot_size", ""),
                item.get("camera_angle", ""),
                item.get("camera_move", ""),
                item.get("duration_seconds", ""),
                (item.get("description") or "").replace("\n", " "),
                (item.get("subtitle") or "").replace("\n", " "),
                _transition_label(str(item.get("transition", "cut"))),
                item.get("audio_note", ""),
                item.get("file_path", ""),
            ]
        )
    return buffer.getvalue()


def build_json(items: list[dict[str, Any]], meta: dict[str, Any]) -> str:
    return json.dumps({"meta": meta, "shots": items}, ensure_ascii=False, indent=2)


def build_srt(items: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    index = 1
    for item in items:
        subtitle = (item.get("subtitle") or item.get("dialogue") or "").strip()
        if not subtitle:
            continue
        lines.append(str(index))
        lines.append(f"{_srt_time(float(item['start']))} --> {_srt_time(float(item['end']))}")
        lines.append(subtitle)
        lines.append("")
        index += 1
    return "\n".join(lines)


def build_export(
    items: list[dict[str, Any]],
    *,
    fmt: str,
    meta: dict[str, Any],
) -> tuple[bytes, str, str, dict[str, Any]]:
    """返回 (内容字节, 文件名后缀, MIME, 结构化 payload)。"""
    prepared = _accumulate([dict(item) for item in items])
    if fmt == "csv":
        content = build_csv(prepared).encode("utf-8-sig")
        mime = "text/csv; charset=utf-8"
    elif fmt == "json":
        content = build_json(prepared, meta).encode("utf-8")
        mime = "application/json; charset=utf-8"
    elif fmt == "srt":
        content = build_srt(prepared).encode("utf-8")
        mime = "application/x-subrip; charset=utf-8"
    elif fmt == "zip":
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("timeline.csv", build_csv(prepared).encode("utf-8-sig"))
            zf.writestr("timeline.json", build_json(prepared, meta))
            zf.writestr("subtitle.srt", build_srt(prepared))
            zf.writestr("meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
        content = buffer.getvalue()
        mime = "application/zip"
    else:
        raise ValueError(f"不支持的导出格式：{fmt}")

    payload = {
        "format": fmt,
        "shot_count": len(prepared),
        "total_duration": round(sum(float(item.get("duration_seconds") or 0) for item in prepared), 2),
        "subtitle_count": sum(1 for item in prepared if (item.get("subtitle") or item.get("dialogue"))),
    }
    return content, fmt, mime, payload
