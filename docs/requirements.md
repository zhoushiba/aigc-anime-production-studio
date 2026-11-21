# 需求分析（requirements.md）

> 项目：AIGC 动漫番剧制作工作台 · `aigc-anime-production-studio`
> 对标岗位：宜宾澎湃人工智能科技有限公司 · AI 专项训练师（AIGC 动漫方向）

## 1. 岗位与业务背景

岗位职责要求把 AIGC 工具真正嵌进动漫制作流水线：从前期策划（剧本构思、分镜脚本、角色设定）到素材生成（文生图 / 图生视频），再到成片前的二次优化与审核交付。真实的制作团队痛点是：

1. **提示词散落在聊天记录里**，同一个人物在不同镜头里长得不一样（角色一致性）；
2. **生成任务没有台账**，谁在什么时候用什么参数生成了哪一版素材，事后无法复盘；
3. **素材没有归类与淘汰机制**，几十张候选图靠人工翻文件夹；
4. **成片合成单靠 Excel 维护**，镜头顺序、字幕、转场一改就丢版本；
5. **审核意见靠口头传递**，驳回后无法追溯改了什么。

本项目把上述环节做成一个可运行的平台，用一条真实闭环替代散乱的文件与聊天记录。

## 2. JD 职责逐条映射

| # | 岗位职责（原文要点） | 本项目对应实现 | 主要文件 / 模块 |
|---|---|---|---|
| 1 | 掌握主流 AIGC 工具在动漫制作中的应用 | 生成服务适配层：`mock`（离线可跑）、`comfyui`（本地 SD 工作流）、`openai`（云端图像模型），统一接口 `BaseProvider.generate()`；画风模板内置 12 套 | `backend/app/services/providers/`、`backend/app/constants.py` |
| 2 | 参与前期策划：剧本构思、分镜脚本、角色设定 | 剧本多版本（按版本号追加）、场次表、分镜脚本（景别/机位/运镜/时长/台词/BGM/排序）、角色设定卡（性格/外形 prompt/LoRA/seed）、场景卡 | `backend/app/routers/series.py`、`backend/app/routers/storyboard.py`、`frontend/src/views/SeriesDetailView.vue`、`StoryboardView.vue`、`CharactersView.vue` |
| 3 | 用 AIGC 生成动画素材，产出短视频 / 番剧片段 | 提示词构建器（主体+动作+镜头语言+画风+光影+画质词+负向词）、生成任务队列（排队/生成中/成功/失败/超时 + 轮询）、素材库、成片合成单与 CSV/JSON/SRT/ZIP 导出 | `backend/app/services/prompt_builder.py`、`backend/app/services/generation.py`、`backend/app/routers/composition.py` |
| 4 | 对生成内容二次优化，保证成片质量 | 素材评分与入选/淘汰、问题标注（手部崩坏/脸部崩坏/构图/色偏/多余肢体/模糊/文字伪影/风格漂移）→ 自动追加修正词 → 重绘 → 新旧素材并排对比、8 项成片质检清单、审核流通过/驳回 | `backend/app/routers/assets.py`、`backend/app/services/prompt_builder.py::fix_prompt`、`backend/app/routers/reviews.py`、`frontend/src/views/AssetsView.vue` |

## 3. 功能需求（10 条必做 + 落地说明）

| 功能 | 落地说明 |
|---|---|
| ① 登录注册 | JWT + PBKDF2 密码哈希；5 种角色：导演 / 分镜师 / 美术 / 审核 / 学员，`/api/auth/*` |
| ② 项目管理 | 番剧/短片：题材、集数、时长、风格、形态（竖屏/横屏）、状态机 `draft→in_production→review→completed→archived` |
| ③ 剧本管理 | 每集多版本剧本（`脚本版本 v1..vN`，只有一版 `is_current`），场次表与场次排序 |
| ④ 分镜脚本 | 镜号/景别/机位/运镜/时长/画面描述/台词/BGM，支持上移下移与整体重排 |
| ⑤ 角色设定卡 | 性格、外形提示词、一致性前缀、参考图、LoRA 名与权重、固定 seed、声线 |
| ⑥ AIGC 生成任务 | 文生图 / 图生视频；状态 `queued→running→succeeded/failed/timeout`；`GET /api/generation/tasks/{id}` 轮询；支持取消与重试 |
| ⑦ 素材库 | 按项目/角色/场次/镜头筛选，重命名、评分、入选/淘汰、二次生成（重绘） |
| ⑧ 成片合成单 | 按顺序的镜头清单（素材、字幕、时长、转场、音频备注），导出 CSV / JSON / SRT / ZIP |
| ⑨ 审核流 | 提交 → 通过 / 驳回（带意见）→ 状态流转，审核记录留痕 |
| ⑩ 数据看板 | 生成成功率、平均耗时、素材数、项目进度、近 7 日趋势、最近任务与最新素材 |

## 4. 非功能需求

- **可离线运行**：默认 `mock` 生成服务按 prompt+seed 确定性渲染占位图（PIL 本地绘制，不联网、不占 GPU），保证 `git clone` 后无需任何模型权重即可跑通全链路。
- **可切换到真实 AIGC**：配置 `COMFYUI_BASE_URL` 或 `OPENAI_API_KEY` 后通过 `provider` 字段切换，接口层不变。
- **可测试**：pytest 42 个用例覆盖鉴权、项目/剧本/分镜、生成状态机（含超时与失败分支）、素材二次优化、合成单与四种导出格式、审核流转、看板统计。
- **可观测**：统一响应体 `{code,message,data,request_id}`、统一异常处理、每个请求带 `X-Request-Id`、控制台结构化日志。
- **数据可迁移**：SQLAlchemy 2.0 ORM，SQLite 默认，改 `DATABASE_URL` 即切 PostgreSQL/MySQL（驱动装好后无需改代码）。

## 5. 验收标准（已实测）

| 项 | 结果 |
|---|---|
| 后端单元测试 | `python -m pytest -q` → **42 passed**（0 failed / 0 error） |
| 端到端冒烟 | 登录 → 建项目 → 建分集 → 保存剧本 → 建场次 → 建分镜 → 生成任务 → 素材入选 → 合成单导出 → 提交审核，全部 200 |
| 前端生产构建 | `npm.cmd run build` → `built in 1m 1s`，`dist/` 产物可用 |
| 真实截图 | `docs/screenshots/` 下 4 张（登录页、数据看板、分镜工作台、素材库） |
