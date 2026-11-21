"""把当前数据库导出为 db/schema.sql 与 db/seed.sql。

用法（在 backend 目录）：python scripts/export_db.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
DB_PATH = BACKEND_DIR / "data" / "app.db"
OUT_DIR = PROJECT_DIR / "db"

# 种子文件里保留的业务数据表（避免把任务/素材等运行时数据写进仓库）
SEED_TABLES = ["users", "series", "episodes", "scripts", "script_scenes", "characters", "scene_cards"]


def quote(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def dump_schema(conn: sqlite3.Connection) -> str:
    rows = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type IN ('table','index') AND sql IS NOT NULL "
        "AND name NOT LIKE 'sqlite_%' ORDER BY type DESC, name"
    ).fetchall()
    header = [
        "-- AI ModelOps / AIGC 动漫番剧制作工作台 —— 数据库结构（由 scripts/export_db.py 自动导出）",
        "-- 数据库：SQLite（默认）。切换到 PostgreSQL/MySQL 时可直接参考本文件的表与约束定义。",
        "",
    ]
    return "\n".join(header) + "\n\n".join(row[0].strip() + ";" for row in rows) + "\n"


def dump_seed(conn: sqlite3.Connection) -> str:
    lines = [
        "-- AIGC 动漫番剧制作工作台 —— 演示数据（由 scripts/export_db.py 自动导出）",
        "-- 应用启动时会自动写入等价种子（backend/app/services/seed.py），本文件用于快速理解数据形态。",
        "",
    ]
    for table in SEED_TABLES:
        try:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        except sqlite3.Error:
            continue
        if not rows:
            continue
        columns = [item[1] for item in conn.execute(f"PRAGMA table_info({table})")]
        col_text = ", ".join(columns)
        lines.append(f"-- {table}：{len(rows)} 行")
        for row in rows:
            values = ", ".join(quote(value) for value in row)
            lines.append(f"INSERT INTO {table} ({col_text}) VALUES ({values});")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"数据库不存在：{DB_PATH}，请先启动一次后端以生成数据")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        schema = dump_schema(conn)
        seed = dump_seed(conn)
    finally:
        conn.close()
    (OUT_DIR / "schema.sql").write_text(schema, encoding="utf-8")
    (OUT_DIR / "seed.sql").write_text(seed, encoding="utf-8")
    print(f"已导出 {OUT_DIR / 'schema.sql'}（{len(schema.splitlines())} 行）")
    print(f"已导出 {OUT_DIR / 'seed.sql'}（{len(seed.splitlines())} 行）")


if __name__ == "__main__":
    main()
