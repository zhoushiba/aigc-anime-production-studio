# 部署说明（deployment.md）

## 1. 本机运行（已验证）

环境：Windows 10/11 + PowerShell、Python 3.11.9、Node 24.20、SQLite 内置。

### 1.1 后端

```powershell
cd backend
python -m pip install -r requirements.txt
$env:PYTHONIOENCODING='utf-8'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

首次启动会自动：建表 → 写种子数据（5 个演示账号、1 个示例剧集《星海拾光》含 3 集 / 3 场 / 8 分镜 / 3 角色卡 / 3 场景卡 / 2 张真实生成素材 / 合成单 / 质检清单 / 1 条待审记录）→ 启动生成线程池。

验证：

```powershell
curl.exe -s http://127.0.0.1:8000/health
```

### 1.2 前端

```powershell
cd frontend
$env:Path = "D:\Apps\Develop\Environment\Node;" + $env:Path
npm.cmd install
npm.cmd run dev        # http://127.0.0.1:5173，已代理 /api 与 /media 到 8000
```

生产构建：

```powershell
npm.cmd run build      # 产物在 frontend/dist
npm.cmd run preview    # 本地预览 dist（端口 4173）
```

`frontend/dist` 存在时，后端会把前端挂到 `http://127.0.0.1:8000/#/`，单端口即可完整演示（本仓库截图就是这种方式拍的）。

## 2. 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `APP_ENV` | `dev` | 环境标识 |
| `DATABASE_URL` | `sqlite:///backend/data/app.db` | 换库只需改这里 |
| `STORAGE_DIR` | `backend/storage` | 素材/缩略图/导出目录 |
| `JWT_SECRET` | 随机生成 | **生产必须显式设置** |
| `TOKEN_EXPIRE_MINUTES` | `720` | token 有效期 |
| `GENERATION_PROVIDER` | `mock` | 默认生成服务 |
| `GENERATION_WORKERS` | `2` | 生成线程数 |
| `GENERATION_DEADLINE_SECONDS` | `60` | 任务截止时间，超过判 `timeout` |
| `GENERATION_INLINE` | `0` | `1` 时同步生成（测试用） |
| `COMFYUI_BASE_URL` | 空 | ComfyUI 服务地址，如 `http://127.0.0.1:8188` |
| `COMFYUI_WORKFLOW_PATH` | 空 | ComfyUI 工作流 JSON 路径 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | 云端图像接口 |
| `OPENAI_API_KEY` | 空 | 云端 Key |
| `OPENAI_IMAGE_MODEL` | `gpt-image-1` | 图像模型名 |
| `DEMO_USERNAME` / `DEMO_PASSWORD` | `director` / `anime2025` | 演示账号 |
| `SEED_DEMO` | `1` | 是否写种子数据 |

完整示例见仓库根 `.env.example`。

## 3. 切换到真实 AIGC 服务

### 3.1 ComfyUI（本地 SD / SDXL）

1. 启动 ComfyUI（默认 `http://127.0.0.1:8188`），在画布上搭好文生图工作流，导出 **API 格式** JSON。
2. 设置：

```powershell
$env:COMFYUI_BASE_URL = "http://127.0.0.1:8188"
$env:COMFYUI_WORKFLOW_PATH = "D:\ai\workflows\anime_t2i_api.json"
```

3. 适配层会改写工作流里的 `CLIPTextEncode` 正向/负向文本、`KSampler` 的 seed/steps/cfg、`EmptyLatentImage` 的宽高，然后 `POST /prompt` 提交并按 `GET /history/{prompt_id}` 轮询，最后 `GET /view` 取图。
4. 前端「生成任务」里把 provider 选为 `comfyui` 即可。

### 3.2 OpenAI 兼容图像接口

```powershell
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"
$env:OPENAI_API_KEY  = "sk-..."
$env:OPENAI_IMAGE_MODEL = "gpt-image-1"
```

适配层调用 `/images/generations`，兼容 `b64_json` 与 `url` 两种返回。

### 3.3 自定义服务

实现 `backend/app/services/providers/base.py` 的 `BaseProvider` 三个方法（`available/generate/describe`），在 `providers/__init__.py` 的 `PROVIDERS` 注册，无需改业务代码。

## 4. Docker 部署（本机未安装 Docker，未实测）

仓库自带 `docker-compose.yml`：`db`(PostgreSQL 16) + `backend`(uvicorn) + `frontend`(nginx 静态托管 + 反代 `/api`、`/media`)。

```bash
docker compose up -d --build
docker compose logs -f backend
```

启动后访问 `http://127.0.0.1:8080`。后端容器内 `DATABASE_URL=postgresql+psycopg://aigc:aigc@db:5432/aigc`，`db/init.sql` 会初始化扩展；素材持久化在命名卷 `assets`。

> CI/生产建议补充：`pip install psycopg[binary]`、关闭 `--reload`、由 nginx 处理静态资源与 gzip、`JWT_SECRET` 使用密钥管理服务注入。

## 5. 生产注意事项

1. **JWT_SECRET** 必须显式设置且不可提交到仓库。
2. 素材目录需要持久化卷并定期备份（`storage/assets`、`storage/exports`）。
3. 生成服务并发受 `GENERATION_WORKERS` 限制；真实 SD 每张图数十秒，建议 worker ≤ GPU 显存允许的并发数。
4. `GET /media/*` 当前公开可读；如需私有，可改为鉴权路由 + 短期签名 URL。
5. 数据库迁移建议引入 Alembic（当前用 `create_all` 保证开箱即用）。
6. 日志目前输出到 stdout，容器化后由 docker/ELK 收集；`X-Request-Id` 可串起前后端排查链路。

## 6. 常见问题

| 现象 | 原因与处理 |
|---|---|
| 启动报 `ModuleNotFoundError: PIL` | 未装依赖，`python -m pip install -r backend/requirements.txt` |
| 前端 401 一直跳登录 | 后端未启动或 `VITE_API_BASE` 指向错误；dev 模式走 vite 代理 |
| 图片 404 | `STORAGE_DIR` 与实际落盘目录不一致；检查 `backend/storage/assets` |
| 任务一直 `running` | 进程异常退出后未重启；重启后 `runner.warmup()` 会把它标为 failed |
| ComfyUI 返回 400 | 工作流 JSON 不是 API 格式；在 ComfyUI 里用「Save (API Format)」导出 |
| 中文乱码（控制台） | PowerShell 代码页问题，加 `$env:PYTHONIOENCODING='utf-8'` |
