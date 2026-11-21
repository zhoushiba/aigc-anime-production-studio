-- Docker 初始化脚本：PostgreSQL 容器首次启动时执行
-- 业务表由后端 SQLAlchemy 的 create_all() 自动创建（见 backend/app/database.py）

-- 需要的话可在这里开启扩展，例如：
-- CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 时区与编码
SET timezone = 'Asia/Shanghai';

COMMENT ON DATABASE aigc IS 'AIGC 动漫番剧制作工作台';
