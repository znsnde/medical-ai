import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

class Settings(BaseSettings):
    # 数据库
    DB_URL: str = os.getenv("DB_URL")
    # LLM大模型
    LLM_API_KEY: str = os.getenv("LLM_API_KEY")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL")
    # 文件路径
    UPLOAD_PATH: str = os.getenv("UPLOAD_PATH")
    # Milvus向量库
    MILVUS_HOST: str = os.getenv("MILVUS_HOST")
    MILVUS_PORT: str = os.getenv("MILVUS_PORT")
    # Neo4j图数据库
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASS: str = os.getenv("NEO4J_PASS", "neo4j")
    # 服务端口
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", 8000))
    # JWT签名密钥（独立随机值，勿复用 LLM_API_KEY）
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    # CORS 允许来源（逗号分隔）
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://[::1]:5173"
    )
    # RAG 检索相似度阈值：Milvus L2 距离上限，超过视为不相关噪声丢弃
    # （实测 all-MiniLM-L6-v2 + 医疗指南：相关命中 <1.0，无关 ≥0.97，默认取 1.0）
    RAG_DISTANCE_THRESHOLD: float = float(os.getenv("RAG_DISTANCE_THRESHOLD", 1.0))

    @property
    def cors_origin_list(self) -> list:
        """CORS 来源列表"""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

settings = Settings()