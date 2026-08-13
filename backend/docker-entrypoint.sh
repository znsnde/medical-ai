#!/bin/sh
# 容器启动入口：
#   1. Alembic 迁移 schema（fail-fast：缺表时应用不可用，阻塞启动）
#   2. 初始化 admin 账号 / Neo4j 图谱 / Milvus 指南（seed，幂等，失败不阻塞启动）
#   3. 用 uvicorn 显式启动（避开 python main.py 在 Linux 下开启 reload 的问题）
set -e

echo "==> 迁移数据库 schema（Alembic）..."
python -m db.migrate

echo "==> 初始化数据库与知识库（seed）..."
python -m db.init_db || echo "  [WARN] init_db 部分步骤失败，系统仍将启动（相关功能降级）"

echo "==> 启动后端服务 (port ${SERVER_PORT:-8000})"
exec uvicorn main:app --host 0.0.0.0 --port "${SERVER_PORT:-8000}"
