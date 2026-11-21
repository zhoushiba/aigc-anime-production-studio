# 系统架构（architecture.md）

## 1. 总体结构

```mermaid
flowchart LR
  subgraph Browser["浏览器（Vue3 SPA，hash 路由）"]
    V1["登录 / 看板"]
    V2["项目 · 剧本 · 分镜"]
    V3["提示词工作台 · 生成任务"]
    V4["素材库 · 合成单 · 审核流"]
  end

  subgraph API["FastAPI 应用（backend/app）"]
    R["routers 路由层<br/>auth/meta/series/storyboard/generation/assets/composition/reviews/dashboard"]
    S["services 业务层<br/>prompt_builder / generation / export_service / seed"]
    C["crud 数据访问层"]
    P["providers 适配层<br/>mock / comfyui / openai"]
  end

  subgraph Infra["基础设施"]
    DB[("SQLite<br/>20 张表")]
    FS[("本地存储 storage/<br/>assets · thumbs · exports")]
    W["ThreadPoolExecutor<br/>生成工作线程"]
  end

  Browser -->|"axios /api + JWT"| R
  R --> S
  R --> C
  S --> C
  S --> P
  C --> DB
  S --> W
  W --> P
  P -->|"PNG 字节"| FS
  Browser -->|"GET /media/*"| FS
```

要点：

- **分层**：`routers`（协议与校验，`deps.py` 注入当前用户）→ `services`（业务编排）→ `crud`（SQLAlchemy 查询）→ `models`（ORM）。路由里不写 SQL，服务里不碰 HTTP。
- **生成是异步的**：`services/generation.py` 用 `ThreadPoolExecutor` 跑任务，任务状态写回数据库，前端 4 秒轮询 `GET /api/generation/tasks/{id}`。测试与演示可开 `GENERATION_INLINE=1` 同步执行。
- **静态资源**：素材落盘到 `storage/assets/`，通过 `/media` 静态挂载回传；`frontend/dist` 存在时后端同时托管前端（单端口演示）。

## 2. 一次「分镜 → 成片合成单」的数据流

```mermaid
sequenceDiagram
  actor U as 导演
  participant FE as Vue3 前端
  participant API as FastAPI
  participant PB as prompt_builder
  participant GEN as generation runner
  participant PR as provider(mock)
  participant DB as SQLite
  participant FS as storage/

  U->>FE: 在分镜工作台点「生成」
  FE->>API: POST /api/generation/tasks {shot_id, prompt, negative_prompt, seed}
  API->>DB: 插入 generation_task(status=queued) + prompt_history
  API->>GEN: submit(task_id)
  API-->>FE: 201 {id, status:"queued"}
  GEN->>DB: status=running, progress=15, started_at
  GEN->>PR: generate(GenerationRequest)
  PR-->>GEN: GenerationResult(image, seed, meta)
  GEN->>FS: 写 assets/xxx.png + thumbs/xxx.jpg
  GEN->>DB: 建 asset(candidate) / task=succeeded / shot.asset_id / cover_asset_id
  FE->>API: GET /api/generation/tasks/{id}（每 4s）
  API-->>FE: status=succeeded, asset_url
  U->>FE: 素材评分 5 星 → 入选 → 二次优化（手部崩坏）
  FE->>API: POST /api/assets/{id}/revise {issues:["hand_broken"]}
  API->>PB: fix_prompt(原提示词, issues)
  PB-->>API: 追加 "perfect detailed hands..." 的修正提示词
  API->>GEN: 重绘任务
  U->>FE: 打开成片合成单 → 导出 CSV
  FE->>API: GET /api/episodes/{id}/export?format=csv
  API-->>FE: UTF-8 BOM CSV（镜号/景别/时长/台词/转场/BGM/素材）
```

## 3. 提示词构建流水线

```mermaid
flowchart TD
  A["主体 subject"] --> G["拼接（逗号分隔，去重）"]
  B["动作 action"] --> G
  C["镜头语言<br/>景别 + 机位 + 运镜"] --> G
  D["画风 style<br/>12 套预设"] --> G
  E["光影 lighting"] --> G
  F["画质词 quality"] --> G
  G --> H["角色一致性前缀<br/>prompt_prefix + LoRA + seed"]
  H --> I["正向提示词"]
  N1["用户负向词"] --> N2["+ 画风预设负向词"]
  N2 --> N3["+ 通用负向词 lowres/bad anatomy..."]
  N3 --> J["负向提示词"]
  I --> K["生成请求"]
  J --> K
```

`build_prompt()` 返回结构化结果（`parts` 里逐段可见），前端提示词工作台把它原样展示，方便教学与复用。

## 4. 生成状态机

```mermaid
stateDiagram-v2
  [*] --> queued: POST /generation/tasks
  queued --> running: 工作线程取到任务
  queued --> canceled: 用户取消
  running --> succeeded: provider 返回图像
  running --> failed: ProviderError / 未配置
  running --> timeout: 超过 GENERATION_DEADLINE_SECONDS
  failed --> queued: 重试（新建任务）
  timeout --> queued: 重试（新建任务）
  succeeded --> [*]
  failed --> [*]
  timeout --> [*]
  canceled --> [*]
```

服务重启时 `runner.warmup()` 把残留的 `running` 任务标记为 `failed`（错误信息「服务重启，任务中断，请重试」），避免出现永远转圈的任务。

## 5. 目录与职责

| 目录 | 职责 |
|---|---|
| `backend/app/routers/` | 10 个路由模块，统一 `prefix=/api`，业务路由统一挂 `Depends(get_current_user)` |
| `backend/app/services/` | 提示词构建、生成执行器、导出、种子数据；`providers/` 是 AIGC 适配层 |
| `backend/app/crud/` | 纯查询函数，返回 `Select` 或实体，供路由分页复用 |
| `backend/app/models.py` | 20 张表的 SQLAlchemy 2.0 声明式模型 |
| `backend/app/schemas.py` | Pydantic v2 请求模型（枚举校验、长度限制） |
| `frontend/src/views/` | 11 个页面视图（登录/看板/项目/项目详情/分镜/合成单/角色/提示词/任务/素材/审核） |
| `frontend/src/api/` | axios 实例 + 各领域 API 封装 + 文件下载封装 |

## 6. 设计取舍

| 决策 | 原因 |
|---|---|
| 生成默认用 `mock` provider | 作品集必须 `clone → 跑起来`，不能依赖 GPU 或云端 Key；mock 用 PIL 真实渲染 PNG（渐变天空、光斑、速度线、剪影、信息带），同一 seed+prompt 结果确定，便于测试断言 |
| 生成走线程池而非 Celery | 目标环境无 Redis/RabbitMQ；`ThreadPoolExecutor` + 数据库状态足够表达排队/运行/超时，且测试无需额外服务 |
| SQLite 作为默认库 | 免安装、文件级备份；ORM 层不写方言特有 SQL，切 PG/MySQL 只需换 `DATABASE_URL` |
| 前端不引 echarts | 趋势图用 CSS 柱状图即可满足看板表达，减少 1MB 级依赖与构建风险 |
| 审核用「提交-决策」两态而非复杂工作流引擎 | 动漫制作的实际审核是「分集/素材送审 → 导演或审核通过/驳回」，两态 + 意见 + 留痕已覆盖 |
