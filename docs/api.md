# 接口文档（api.md）

- Base URL：`http://127.0.0.1:8000/api`
- 交互式文档：`http://127.0.0.1:8000/docs`（Swagger UI）、`/redoc`
- 鉴权：除 `/api/auth/login`、`/api/auth/register`、`/api/meta/options` 外，全部需要 `Authorization: Bearer <token>`；缺失或过期返回 `401 {code:40100}`
- 统一响应体：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "3f7c1d9a8b2e4c60"
}
```

`code=0` 表示成功；业务错误 `code` 为 5 位业务码（如 `40901` 用户名已存在），HTTP 状态码同步语义（401/403/404/409/422/500）。每个响应都带 `X-Request-Id`，与日志、`request_id` 一致。

## 1. 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | 注册，body `{username,password,display_name,role}`；角色 director/storyboard/artist/reviewer/student |
| POST | `/auth/login` | 登录，body `{username,password}` → `{token,token_type,expires_in,user}` |
| GET | `/auth/me` | 当前用户 |

```bash
curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"director","password":"anime2025"}'
```

## 2. 元数据

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/meta/options` | 题材、12 套画风、景别、机位、运镜、转场、平台、角色、各类状态、剧本结构、质检项、二次优化问题项、生成服务列表 |

## 3. 项目 / 分集 / 剧本 / 场次

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/series?page=1&size=20&search=&status=` | 项目分页列表 |
| POST | `/series` | 新建项目 `{title,genre,logline,synopsis,episodes_planned,target_duration,style,platform}` |
| GET | `/series/{id}` | 项目详情（含分集、角色数、场景数、进度） |
| PATCH/DELETE | `/series/{id}` | 更新 / 删除（级联） |
| GET/POST | `/series/{id}/episodes` | 分集列表 / 新建分集 |
| GET/PATCH/DELETE | `/episodes/{id}` | 分集详情 / 更新状态 / 删除 |
| GET/PUT | `/episodes/{id}/script` | 读取当前剧本 / 保存新版本（版本号自增，旧版置非当前） |
| GET | `/episodes/{id}/scripts` | 剧本版本历史 |
| GET/POST | `/episodes/{id}/scenes` | 场次列表 / 新建场次 |
| PATCH/DELETE | `/scenes/{id}` | 更新 / 删除场次 |
| POST | `/scenes/{id}/move` | 场次上移/下移 `{direction:"up"|"down"}` |

## 4. 分镜 / 角色 / 场景卡 / 提示词

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/episodes/{id}/shots` | 分镜列表（含总时长）/ 新建分镜 |
| GET/PATCH/DELETE | `/shots/{id}` | 分镜详情 / 更新 / 删除 |
| POST | `/shots/{id}/move` | 上移下移 |
| POST | `/episodes/{id}/shots/reorder` | 整体重排 `{ordered_ids:[1,3,2]}` |
| POST | `/shots/{id}/prompt` | 由分镜生成提示词，`{style,temperature?}`；`save=true` 时写回分镜并置状态 `prompted` |
| GET/POST | `/series/{id}/characters` | 角色卡列表 / 新建 |
| PATCH/DELETE | `/characters/{id}` | 更新 / 删除角色卡 |
| GET/POST | `/series/{id}/scene-cards` | 场景卡列表 / 新建 |
| PATCH/DELETE | `/scene-cards/{id}` | 更新 / 删除场景卡 |
| POST | `/prompts/build` | 提示词构建器：主体/动作/镜头/画风/光影/画质/一致性 → `{prompt,negative_prompt,parts,style}` |
| GET/POST | `/prompts/templates` | 模板列表（12 套内置）/ 新建 |
| DELETE | `/prompts/templates/{id}` | 删除自定义模板（内置模板 `40904` 不可删） |
| GET | `/prompts/history?series_id=&limit=` | 最近提示词与任务记录 |
| GET | `/prompts/issues` | 二次优化问题项（8 个） |

```bash
curl -s -X POST http://127.0.0.1:8000/api/prompts/build \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"subject":"银发少女","action":"站在灯塔前回头","shot_size":"中景","camera_angle":"仰视","camera_move":"推","style":"日系赛璐璐"}'
```

## 5. AIGC 生成任务

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/generation/providers` | 已注册生成服务与可用性（mock/comfyui/openai） |
| POST | `/generation/tasks` | 提交任务 `{kind,prompt,negative_prompt,provider,series_id,episode_id,shot_id,seed,params}` |
| GET | `/generation/tasks?status=&kind=&shot_id=&page=&size=` | 任务分页 |
| GET | `/generation/tasks/{id}` | **轮询接口**：状态、进度、耗时、错误、产出素材 |
| POST | `/generation/tasks/{id}/cancel` | 取消（仅排队中） |
| POST | `/generation/tasks/{id}/retry` | 重试（以原 prompt/seed 新建任务） |
| GET | `/generation/stats` | 成功率、平均耗时、各状态计数 |

任务状态：`queued`（排队）→ `running`（生成中）→ `succeeded` / `failed` / `timeout`；失败或超时可用 `retry` 重投。`params.force_timeout=true` 可让 mock 服务演示超时分支。

## 6. 素材库

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/assets?series_id=&episode_id=&shot_id=&character_id=&status=&kind=&keyword=` | 素材分页 |
| GET | `/assets/stats` | 总数、各状态、各类型、平均评分、占用空间 |
| GET | `/assets/{id}` | 素材详情 |
| PATCH | `/assets/{id}` | 重命名 `{title}` / 改状态 `{status}` / 评分 `{rating}` / 审核备注 |
| POST | `/assets/{id}/rate` | 打分 `{score:1-5,comment}` |
| GET | `/assets/{id}/revisions` | 二次优化链路 |
| POST | `/assets/{id}/revise` | **二次优化**：`{issues:["hand_broken"],note}` → 自动追加修正词并重绘，返回 `{revision,task,new_asset}` |
| POST | `/assets/batch` | 批量操作 `{ids:[..],action:"select"|"reject"|"archive"}` |

## 7. 成片合成单与导出

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/episodes/{id}/timeline` | 合成单（不存在时按分镜自动生成）与镜头清单 |
| PUT | `/episodes/{id}/timeline` | 改名 / 状态 |
| POST | `/episodes/{id}/timeline/auto-fill` | 按当前分镜重建镜头清单 |
| PATCH | `/timeline-items/{id}` | 改字幕 / 时长 / 转场 / 音频备注 |
| POST | `/timeline-items/{id}/move` | 镜头上下移 |
| GET | `/episodes/{id}/export?format=csv|json|srt|zip` | 直接下载导出文件 |
| POST | `/episodes/{id}/exports` | 生成导出任务并落盘，返回记录 |
| GET | `/episodes/{id}/exports` | 导出历史 |
| GET | `/exports/{id}/download` | 下载历史导出文件 |
| GET | `/episodes/{id}/checklist` | 8 项成片质检清单 |
| PATCH | `/checklist/{id}` | 勾选 / 备注 |

导出内容：CSV（镜号、景别、机位、运镜、时长、画面、台词、转场、BGM、素材文件，带 UTF-8 BOM 便于 Excel 打开）、JSON（`meta` + `shots`）、SRT（按顺序累加时长的字幕）、ZIP（四件套打包）。

## 8. 审核流

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/reviews?status=&target_type=` | 审核分页 |
| GET | `/reviews/stats` | 待审 / 通过 / 驳回计数 |
| POST | `/reviews` | 提交审核 `{series_id,target_type,target_id,title,comment}` |
| GET | `/reviews/{id}` | 详情 |
| POST | `/reviews/{id}/decide` | 决策 `{approve:true|false,comment}`；已处理再决策返回 `409` |

## 9. 数据看板

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/dashboard/overview` | 项目/分集/分镜/角色/用户计数、待审数、生成统计、素材统计、项目进度、最近任务与素材 |
| GET | `/dashboard/trend?days=7` | 按天聚合：任务数、成功、失败、成功率、平均耗时 |

## 10. 其他

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查（无需鉴权）：版本、数据库、种子信息、生成服务 |
| GET | `/media/{path}` | 素材主图与缩略图静态访问 |
| GET | `/docs` | Swagger UI |

## 11. 错误码

| code | HTTP | 含义 |
|---|---|---|
| 0 | 200 | 成功 |
| 40000/42200 | 400/422 | 参数校验失败（`details` 指出字段） |
| 40100 | 401 | 未登录 / token 无效 |
| 40300 | 403 | 角色无权限 |
| 40400 | 404 | 资源不存在 |
| 40900/40901/40903/40904 | 409 | 冲突（重名、内置模板不可删等） |
| 50001 | 500 | 数据库错误 |
| 50000 | 500 | 未捕获异常 |
