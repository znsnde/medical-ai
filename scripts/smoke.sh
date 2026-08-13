#!/usr/bin/env bash
# 全栈冒烟：后端健康 / admin 登录 / 知识图谱非空 / 前端可达
# 用法：
#   CI（容器默认端口）：bash scripts/smoke.sh
#   本机 Docker 栈（端口自定义）：bash scripts/smoke.sh http://localhost:8001 http://localhost:8080
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
FRONTEND_URL="${2:-http://localhost}"
# CI 用 python3；本机 Git Bash 无 python3 时可 PYTHON=python 覆盖
PYTHON="${PYTHON:-python3}"

echo "==> 后端健康等待：${BASE_URL}/"
ok=""
for i in $(seq 1 90); do
  if curl -sf "$BASE_URL/" >/dev/null 2>&1; then ok=1; break; fi
  sleep 5
done
if [ -z "$ok" ]; then
  echo "[FAIL] 后端 90 次探活未就绪（450s 超时）" >&2
  exit 1
fi
echo "[ok] 后端就绪"

echo "==> admin 登录"
TOKEN=$(curl -sf -X POST "$BASE_URL/api/auth/login" -d "username=admin&password=admin123" \
  | $PYTHON -c "import sys,json;print(json.load(sys.stdin)['data']['token'])")
if [ -z "$TOKEN" ]; then
  echo "[FAIL] 登录未返回 token" >&2
  exit 1
fi
echo "[ok] 登录成功 (token ${#TOKEN} 字符)"

echo "==> 知识图谱非空（Neo4j seed 生效）"
curl -sf "$BASE_URL/api/kg/graph" -H "Authorization: Bearer $TOKEN" \
  | $PYTHON -c "import sys,json;d=json.load(sys.stdin)['data'];assert len(d['nodes'])>0,'graph empty';print('[ok] 图谱',len(d['nodes']),'节点')"

echo "==> 前端可达"
curl -sf "$FRONTEND_URL/" >/dev/null && echo "[ok] 前端正常"

echo "==> 全栈冒烟全部通过"
