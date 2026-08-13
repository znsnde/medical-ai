# 智慧医疗辅助诊断与电子病历结构化系统

基于 **FastAPI + Vue 3** 的医疗 AI 综合平台：电子病历智能结构化、AI 辅助诊断、医学知识图谱、RAG 检索增强、多模态影像分析、患者随访问答、医学文献速读、诊断报告导出。

## 核心功能

| 模块 | 说明 |
|---|---|
| 病历智能结构化 | LLM 实体抽取 + 关键词降级，结构化出症状/既往史/诊断/用药 |
| AI 辅助诊断 | DeepSeek 生成诊断建议，融合 RAG 临床指南 + 知识图谱关联知识 + 影像分析 |
| 医学知识图谱 | Neo4j 存储 20 种疾病的症状/用药/科室/治疗/相互作用/并发症，前端 ECharts 可视化 |
| RAG 检索增强 | 病历向量化后从 Milvus 召回相似医疗指南，作为 LLM 参考知识 |
| 多模态影像分析 | DICOM 元数据 + 像素特征（CT 值/HU）+ 临床病历 → LLM 生成影像解读，含诚实降级 |
| 患者随访问答 | 基于临床知识的多轮问诊对话 |
| 医学文献速读 | 论文上传 → LLM 生成摘要与核心结论 |
| 诊断报告导出 | PDF 报告生成与预览 |
| 用户与权限 | JWT 认证，管理员/医生/患者三角色 RBAC |
| 患者自助查看报告 | 患者手机号认领本人档案后，可查看我的病历、诊断报告并下载本人 PDF（三级归属校验） |
| 软删除与回收站 | 患者/病历/报告删除改软删（`is_deleted` 标记，文件保留），回收站支持级联恢复、彻底删除（purge）、清空回收站 |

## 技术架构

```
┌─────────────── 前端 (Vue 3 + Vite :5173) ───────────────┐
│  Element Plus / ECharts / vue-i18n / axios              │
│  /api 请求经 vite proxy → http://127.0.0.1:8000          │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP
┌─────────────── 后端 (FastAPI :8000) ────────────────────┐
│  13 业务模块路由 (api/*) + CORS + 全局异常 + 审计日志      │
│  业务层 medical_business/*                               │
│  ┌──────────┬──────────┬──────────┬──────────┬────────┐ │
│  │  DeepSeek │  Neo4j   │  Milvus  │  MySQL   │ 本地文件│ │
│  │ LLM/RAG/  │ 知识图谱  │ 向量检索  │  业务数据  │ 静态资源│ │
│  │ 影像解读   │          │          │          │        │ │
│  └──────────┴──────────┴──────────┴──────────┴────────┘ │
└──────────────────────────────────────────────────────────┘
```

| 组件 | 技术 | 用途 |
|---|---|---|
| 后端框架 | FastAPI (Python 3.12) | REST API |
| 前端 | Vue 3 + Vite + Element Plus + ECharts | SPA 管理端 |
| 关系库 | MySQL (SQLAlchemy) | 患者/病历/报告/用户 |
| 图数据库 | Neo4j | 疾病知识图谱 |
| 向量库 | Milvus (pymilvus) | 医疗指南向量检索 |
| 大模型 | DeepSeek (openai SDK) | 诊断/抽取/摘要/影像解读 |
| 嵌入模型 | sentence-transformers `all-MiniLM-L6-v2` (384维) | 文本向量化 |

## 目录结构

```
├── backend/
│   ├── api/                 # 路由层（13 个业务模块）
│   ├── medical_business/    # 业务逻辑（诊断/结构化/图谱/论文/随访）
│   ├── core/                # 核心服务（LLM/RAG/向量库/影像/日志/安全）
│   ├── dcmtk_handler/       # DICOM 解析
│   ├── db/                  # SQLAlchemy 模型、CRUD、初始化脚本（init_db.py）
│   ├── config/settings.py   # 配置（加载 .env）
│   ├── tests/               # pytest 冒烟测试（48 项）
│   ├── Dockerfile           # 后端容器化（含嵌入模型预下载）
│   └── main.py              # FastAPI 入口
├── frontend/                # Vue 3 前端（13 个页面）
│   ├── Dockerfile           # 多阶段构建：node 构建 → nginx 托管
│   └── nginx.conf           # history 路由回退 + /api、/static 反代
├── docker-compose.yml       # 一键部署编排（后端/前端/MySQL/Neo4j/Milvus）
├── scripts/
│   ├── seed_demo_data.py    # 演示数据一键重置（Neo4j + Milvus + 演示患者）
│   └── generate_reference_images.py  # 生成典型病例参考影像
├── docs/
│   └── DEMO.md              # 答辩演示脚本（演示路线 + 讲稿要点 + 常见追问）
└── README.md
```

## 环境要求

- Python 3.12 + Node.js（前端构建）
- MySQL 8、Neo4j（本机或 Docker）、Milvus（Docker 或本地，端口 19530）
- DeepSeek API Key（可访问外网；HuggingFace 模型下载走 hf-mirror.com 镜像）

## 快速启动

### 1. 后端

```bash
# 安装依赖（首次）
cd backend
python -m venv venv
venv/Scripts/pip install -r requirements.txt

# 配置环境变量：复制 backend/.env.example → backend/.env 并填写
# 启动（必须用 venv 的 python）
venv/Scripts/python.exe main.py
```

- 服务地址：http://127.0.0.1:8000
- 接口文档（Swagger）：http://127.0.0.1:8000/docs
- 默认管理员：`admin / admin123`

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

- 访问 http://localhost:5173 （`/api` 自动代理到后端 8000）

### 3. 初始化演示数据（可选）

```bash
# 重置 Neo4j 图谱（20 种疾病）+ Milvus 灌入 18 条医疗指南 + 建演示患者
#   （patient_demo/demo1234，档案手机号 13800001111，含病历 + 诊断报告 PDF）
backend/venv/Scripts/python.exe scripts/seed_demo_data.py
```

### 4. Docker 一键部署（全栈容器化）

前置：安装 Docker Desktop（含 `docker compose`）。

```bash
# ① 配置后端密钥：复制 .env.example 并填写 LLM_API_KEY / JWT_SECRET / NEO4J_PASS 等
cp backend/.env.example backend/.env

# ② （可选）自定义端口 / 镜像源：国内网络建议设置 REGISTRY 前缀（见 .env.example 注释）
cp .env.example .env

# ③ 一键构建并启动（首次构建后端镜像含 torch 嵌入模型，约 10-30 分钟）
docker compose up -d --build
```

- 前端：http://localhost （nginx 托管，端口默认 80，可用 `.env` 的 `FRONTEND_PORT` 修改）
- 后端：http://localhost:8000 ，接口文档 http://localhost:8000/docs
- 默认账号：`admin / admin123`

**首次启动自动初始化**（幂等，任一失败不阻塞系统启动，相关功能降级）：

1. 建 MySQL 数据表
2. 创建管理员账号 `admin/admin123`
3. Neo4j 图谱为空时重建 20 种疾病知识图谱
4. Milvus 医疗指南集合为空时灌入 18 条临床指南

**说明：**

- MySQL/Neo4j/Milvus 不映射宿主端口，仅容器内部网络互通，与本机已运行的同类服务**零端口冲突**。
- 上传的 DICOM/论文/PDF 报告持久化在 `backend/static/upload`（绑定挂载）。
- 真实密钥经 `backend/.env` 运行时注入，**不写入镜像层**。
- 停止：`docker compose down`（数据卷保留）；彻底清理：`docker compose down -v`。

## 配置说明（backend/.env）

| 变量 | 说明 |
|---|---|
| `DB_URL` | MySQL 连接串 |
| `LLM_API_KEY` / `LLM_BASE_URL` | DeepSeek API |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASS` | Neo4j 连接 |
| `MILVUS_HOST` / `MILVUS_PORT` | Milvus 向量库 |
| `HF_ENDPOINT` | HuggingFace 镜像（国内默认 `https://hf-mirror.com`，用于嵌入模型下载） |
| `JWT_SECRET` | JWT 签名密钥（随机 64 位 hex，勿复用 LLM_API_KEY） |
| `CORS_ORIGINS` | 允许的跨域来源（逗号分隔） |
| `SERVER_PORT` | 后端端口（默认 8000） |

## API 概览

所有接口前缀 `/api`，除登录/自助注册外均需 `Authorization: Bearer <token>`。

| 前缀 | 模块 | 主要接口 |
|---|---|---|
| `/api/auth` | 用户认证 | login、register、me、users（admin） |
| `/api/record` | 病历结构化 | struct（文本+DICOM 上传）、list、delete |
| `/api/diagnosis` | AI 诊断 | generate、list、detail、delete |
| `/api/patient` | 患者管理/随访/自助 | add、bind（手机号认领）、my-records、my-reports、chat、profile |
| `/api/paper` | 文献速读 | upload、search、analysis |
| `/api/report` | 诊断报告 | pdf/generate、pdf/{id}、pdf/download/{id}（患者仅本人） |
| `/api/kg` | 知识图谱 | graph、disease、symptom、interaction、search |
| `/api/dicom` | 影像 | preview、metadata |
| `/api/consultation` | 多轮问诊 | chat、sessions |
| `/api/reference-image` | 参考影像库 | list、by-record |
| `/api/dashboard` | 仪表盘 | stats |
| `/api/recycle` | 回收站 | patients/records/reports 列表、{type}/{id}/restore、{type}/{id}/purge、clear（admin/doctor） |
| `/api/system` | 系统 | info |

## 测试

```bash
cd backend
venv/Scripts/python.exe -m pytest tests/ -v
```

48 项冒烟测试（43 通过，5 项依赖宿主 Neo4j 自动 skip），覆盖：应用启动/路由/鉴权、登录与 RBAC、P0 安全（静态目录移除/越权封堵/会话归属/上传白名单）、RAG 降级、影像分析降级、诊断核心链路、患者自助（绑定/我的报告/PDF 本人放行他人 403）、软删除与回收站（级联软删/恢复、purge、清空、统计排除、二次删除防护）。MySQL/Neo4j 不可用时相关用例自动 skip，不阻塞其余。

## 项目亮点（论文/答辩素材）

1. **三级辅助决策**：RAG 指南（Milvus）→ 知识图谱关联知识（Neo4j）→ 影像分析（LLM），三层信息同时注入诊断建议。
2. **知识图谱可视化**：ECharts 力导向图，按节点类型着色、悬停高亮、中心搜索子图展开，支持日夜主题。
3. **多模态影像分析产品化**：DICOM 元数据 + 像素统计（HU 范围）驱动 LLM 生成三段式影像解读，诚实声明局限，LLM 不可用时优雅降级。
4. **健壮的降级设计**：RAG/图谱/影像/LLM 任一不可用均不阻塞主流程。
5. **患者数据按归属隔离**：医生侧"全院可见"模型下，患者自助仅能通过手机号认领本人档案，报告下载经 report→record→patient.user_id 三级归属校验，未绑定/他人/匿名一律拒绝。
6. **工程化**：JWT 独立密钥、CORS 白名单、全局异常统一包装、审计日志（登录/用户管理/诊断）、pytest 冒烟测试、一键种子脚本、Docker 一键部署（全栈容器化）、GitHub Actions 三阶段 CI（后端测试含 MySQL/Neo4j services + 前端构建 + compose 校验）。
7. **数据可恢复**：患者/病历/报告删除改软删除，误删可进回收站级联恢复；彻底删除（purge）才物理清行与文件，单事务保证一致。

## 常见问题

- **RAG 首次调用卡 3-4 分钟**：嵌入模型未下载且直连 huggingface.co 被墙。已通过 `HF_ENDPOINT=https://hf-mirror.com` 镜像下载并缓存；也可用 `HF_HUB_OFFLINE=1` 强制跳过 RAG。
- **诊断报告"影像分析"为降级文案**：说明 LLM 不可用或 DICOM 无像素数据，系统按设计降级为影像基础信息描述。
- **知识库混入病历原文**：病历结构化会自动把病历文本灌入 Milvus。需干净知识库时 drop `medical_knowledge_coll` 集合后重跑种子脚本。
- **Windows 下无热重载**：改动后端代码后需重启 `main.py` 进程。
- **Docker 拉取镜像慢/失败**：国内 Docker Hub 不稳定，在根目录 `.env` 设 `REGISTRY=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/` 后重跑 `docker compose up -d`。
- **`docker compose up` 报 backend/.env 缺失**：先 `cp backend/.env.example backend/.env` 并填写 LLM_API_KEY / JWT_SECRET。
- **与本机已装的 MySQL/Neo4j/Milvus 共存**：compose 内数据服务不映射宿主端口，端口不冲突；但资源占用翻倍，演示时建议本机服务与 Docker 二选一。
