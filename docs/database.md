# 数据库设计（database.md）

## 1. 总览

- 数据库：SQLite（默认，`backend/data/app.db`，WAL 模式）
- ORM：SQLAlchemy 2.0（`Mapped[...]` 声明式），共 **20 张表**
- 切换 PostgreSQL / MySQL：改 `DATABASE_URL` 即可（`postgresql+psycopg://...` / `mysql+pymysql://...`），代码无方言特例
- DDL 见 `db/schema.sql`，示例数据见 `db/seed.sql`

## 2. ER 图

```mermaid
erDiagram
  users ||--o{ series : owns
  series ||--o{ episodes : contains
  series ||--o{ characters : defines
  series ||--o{ scene_cards : defines
  series ||--o{ prompt_history : records
  series ||--o{ generation_tasks : queues
  episodes ||--o{ scripts : versions
  episodes ||--o{ script_scenes : scenes
  episodes ||--o{ storyboard_shots : shots
  episodes ||--|| timelines : timeline
  episodes ||--o{ quality_checklists : checks
  episodes ||--o{ export_jobs : exports
  scripts ||--o{ script_scenes : owns
  timelines ||--o{ timeline_items : items
  storyboard_shots ||--o{ timeline_items : referenced_by
  generation_tasks ||--o| assets : produces
  generation_tasks ||--o{ prompt_history : logs
  assets ||--o{ asset_ratings : rated
  assets ||--o{ asset_revisions : revised
  series ||--o{ reviews : reviewed
  users ||--o{ asset_ratings : gives
```

## 3. 表清单

| 表 | 说明 | 关键字段 |
|---|---|---|
| `users` | 平台用户 | `username` 唯一、`password_hash`(PBKDF2)、`role`(director/storyboard/artist/reviewer/student/admin) |
| `series` | 番剧 / 短片项目 | `title`、`genre`、`episodes_planned`、`target_duration`、`style`、`platform`(vertical/horizontal)、`status`、`cover_asset_id` |
| `episodes` | 分集 | `series_id`、`number`、`title`、`status`；唯一 `(series_id, number)` |
| `scripts` | 剧本版本 | `episode_id`、`version`、`structure`(三幕式/起承转合/自由)、`content`、`is_current`；唯一 `(episode_id, version)` |
| `script_scenes` | 场次 | `script_id`、`episode_id`、`seq`、`location`、`time_of_day`、`action_text`、`dialogue`、`duration_seconds` |
| `storyboard_shots` | 分镜 | `episode_id`、`seq`、`shot_no`、`shot_size`、`camera_angle`、`camera_move`、`duration_seconds`、`description`、`dialogue`、`bgm`、`prompt`、`negative_prompt`、`asset_id`、`status` |
| `characters` | 角色设定卡 | `personality`、`appearance_prompt`、`prompt_prefix`、`lora_name`、`lora_weight`、`seed`、`voice` |
| `scene_cards` | 场景设定卡 | `description`、`atmosphere`、`prompt`、`prompt_prefix`、`seed` |
| `prompt_templates` | 画风/提示词模板（12 套内置） | `style_key`、`content`、`negative_prompt`、`is_builtin` |
| `prompt_history` | 提示词与任务历史 | `series_id`、`shot_id`、`task_id`、`prompt`、`negative_prompt`、`params_json` |
| `generation_tasks` | 生成任务 | `kind`(text2image/img2video)、`provider`、`prompt`、`params_json`、`status`(queued/running/succeeded/failed/timeout/canceled)、`progress`、`error`、`asset_id`、`seed`、`duration_ms` |
| `assets` | 素材 | `kind`、`title`、`file_path`、`thumb_path`、`width`、`height`、`file_size`、`seed`、`provider`、`status`(candidate/selected/rejected/archived)、`rating`、`meta_json` |
| `asset_ratings` | 素材评分 | `asset_id`、`user_id`、`score`(1-5)、`comment` |
| `asset_revisions` | 二次优化记录 | `asset_id`→`new_asset_id`、`issues_json`、`fix_prompt`、`task_id` |
| `timelines` | 成片合成单 | `episode_id` 唯一、`name`、`total_duration`、`status`、`platform`、`resolution` |
| `timeline_items` | 合成单镜头 | `seq`、`shot_id`、`asset_id`、`duration_seconds`、`subtitle`、`transition`、`audio_note` |
| `quality_checklists` | 成片质检清单 | 唯一 `(episode_id, item_key)`、`checked`、`note`、`checked_by` |
| `export_jobs` | 导出记录 | `format`(csv/json/srt/zip)、`file_path`、`status`、`payload_json` |
| `reviews` | 审核单 | `target_type`(episode/timeline/asset)、`target_id`、`status`(pending/approved/rejected)、`comment`、`reviewer_name`、`decided_at` |

## 4. 索引与约束

- 唯一约束：`users.username`、`prompt_templates.name`、`(episodes.series_id, number)`、`(scripts.episode_id, version)`、`(quality_checklists.episode_id, item_key)`、`timelines.episode_id`
- 外键：全部开启 `PRAGMA foreign_keys=ON`；删除项目时服务层级联删除分集下的剧本/场次/分镜/合成单/质检/导出
- 常用索引：`generation_tasks.status`、`generation_tasks.series_id`、`assets.status`、`assets.series_id`、`reviews.status`

## 5. 一致性设计

1. **剧本版本**：保存时同集旧版本 `is_current=False`，新版本号 = `max(version)+1`，只有一版是当前版；版本历史可回看。
2. **分镜序号**：上移/下移/重排后统一把 `seq` 重排成 `1..n`，`shot_no` 同步为 `SH01..SHnn`，避免空洞。
3. **生成任务与素材**：任务成功后才创建 `asset`，并回写 `task.asset_id`、`shot.asset_id`、`series.cover_asset_id`（仅首次），保证「任务-素材-分镜-封面」链路一致。
4. **审核流转**：只有 `pending` 能决策，决策后写 `decided_at` 与审核人；通过分集审核时把分集状态推进到 `approved`，驳回则回到 `storyboard` 等待修改。
5. **二次优化**：`asset_revisions` 保留「原素材 → 问题 → 修正提示词 → 新素材」的完整链路，可追溯每一次重绘。

## 6. 备份与迁移

```powershell
# 文件级备份（SQLite + WAL）
Copy-Item backend\data\app.db backend\data\app.db.bak

# 切换到 PostgreSQL（示例）
$env:DATABASE_URL = "postgresql+psycopg://user:pass@127.0.0.1:5432/aigc_studio"
python -m uvicorn app.main:app --port 8000
```

表结构由 `Base.metadata.create_all()` 在启动时自动创建；生产环境建议改用 Alembic 管理迁移（见 `docs/roadmap.md`）。
