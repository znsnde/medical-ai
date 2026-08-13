# 智慧医疗后端镜像
# 基础：python:3.12-slim（镜像较大，torch ~2-3GB，首次构建需 10-30 分钟）
# 基础镜像钉到国内快的 daocloud 镜像源（绕过 Docker Hub 慢源）
FROM docker.m.daocloud.io/library/python:3.12-slim

# 国内网络：pip 走阿里云镜像；HuggingFace 走 hf-mirror.com（嵌入模型下载/预下载）
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    PIP_TRUSTED_HOST=mirrors.aliyun.com \
    HF_ENDPOINT=https://hf-mirror.com \
    CURL_CA_BUNDLE= \
    REQUESTS_CA_BUNDLE= \
    HF_HUB_DISABLE_SSL_VERIFY=1

# weasyprint(Pango/Cairo) + PDF 中文字体(Noto CJK) + 健康检查/下载工具(curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖（利用层缓存，改代码不重装依赖）
COPY requirements.txt .
# CPU 版 torch：后端仅用 CPU 推理嵌入模型。Linux 下默认 torch 会经 cuda-toolkit 拉取数 GB 的 nvidia-* 库，
# 故直接从阿里云 pytorch-wheels 镜像源按 URL 预装 2.12.1+cpu（192MB），之后 requirements 中的 torch==2.12.1 按 PEP440 视为已满足。
RUN pip install "https://mirrors.aliyun.com/pytorch-wheels/cpu/torch-2.12.1%2Bcpu-cp312-cp312-manylinux_2_28_x86_64.whl" \
        --extra-index-url https://mirrors.aliyun.com/pypi/simple/
RUN pip install -r requirements.txt

# 拷贝应用代码（.dockerignore 已排除 venv/.env/static/upload 等）
COPY . .

# 构建期预下载嵌入模型，避免容器首次 RAG 调用卡顿（失败不致命：首次调用时仍会走 hf-mirror 下载）
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" \
    || echo "[WARN] 嵌入模型预下载失败，将在首次调用时下载"

RUN chmod +x docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
