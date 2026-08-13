from pymilvus import connections, utility, Collection, CollectionSchema, FieldSchema, DataType
from config.settings import settings
from core.logger import get_logger
from utils.common import resp_fail

logger = get_logger(__name__)

# 全局Milvus连接
def connect_milvus():
    try:
        # 使用默认 alias，与下方 utility.has_collection / Collection 保持一致
        # （此前用 alias="medical" 但查询走默认连接，导致 ConnectionNotExistException）
        connections.connect(
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT
        )
        logger.info("Milvus向量库连接成功")
        return None
    except Exception as e:
        logger.warning("Milvus连接失败: %s", e)
        return resp_fail(f"向量库连接异常：{str(e)}")


def _require_milvus_connected():
    """连接失败时抛出明确异常，由调用方捕获降级，避免继续走默认连接报 ConnectionNotExistException"""
    err = connect_milvus()
    if err is not None:
        raise RuntimeError(f"Milvus连接失败：{err}")

# 创建医疗知识库向量集合
def create_medical_collection():
    _require_milvus_connected()
    coll_name = "medical_knowledge_coll"
    # 存在则跳过创建
    if utility.has_collection(coll_name):
        coll = Collection(coll_name)
        # 幂等加载，确保可检索
        try:
            coll.load()
        except Exception as e:
            logger.warning("Milvus集合加载: %s", e)
        return coll
    # 定义字段（pymilvus 3.x 需用 CollectionSchema 包装）
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=384)
    ]
    coll = Collection(coll_name, CollectionSchema(fields, description="医疗知识库"))
    # 创建索引
    index_params = {
        "index_type": "IVF_FLAT",
        "metric_type": "L2",
        "params": {"nlist": 128}
    }
    coll.create_index(field_name="vector", index_params=index_params)
    coll.load()
    return coll

# 检索向量
def search_vector(embedding, top_k=3):
    coll = create_medical_collection()
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
    res = coll.search(
        data=[embedding],
        anns_field="vector",
        param=search_params,
        limit=top_k,
        output_fields=["text"]
    )
    return res
