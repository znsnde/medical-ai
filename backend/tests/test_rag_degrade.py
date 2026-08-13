"""
RAG 知识检索降级策略测试（纯单元测试，不依赖 Milvus / 模型）
核心断言：向量库或模型不可用时返回空列表，不抛异常、不阻塞主流程
"""


def test_rag_empty_when_query_blank():
    from core.medical_rag import rag_search_medical_knowledge
    assert rag_search_medical_knowledge("") == []
    assert rag_search_medical_knowledge("   ") == []


def test_rag_degrades_when_embedding_unavailable(monkeypatch):
    """嵌入模型不可用（返回 None）→ 跳过检索，返回空"""
    monkeypatch.setattr("core.medical_rag._safe_get_embedding", lambda text: None)
    from core.medical_rag import rag_search_medical_knowledge
    assert rag_search_medical_knowledge("高血压") == []


def test_rag_degrades_when_vector_search_fails(monkeypatch):
    """Milvus 检索抛异常 → 捕获并返回空"""
    monkeypatch.setattr("core.medical_rag._safe_get_embedding", lambda text: [0.0] * 384)

    def _boom(*args, **kwargs):
        raise RuntimeError("Milvus 连接失败")

    monkeypatch.setattr("core.vector_store.search_vector", _boom)
    from core.medical_rag import rag_search_medical_knowledge
    assert rag_search_medical_knowledge("高血压") == []


def test_rag_returns_matched_texts(monkeypatch):
    """正常路径：嵌入 + 检索命中 → 返回参考文本"""
    monkeypatch.setattr("core.medical_rag._safe_get_embedding", lambda text: [0.0] * 384)

    class _Hit:
        """模拟 Milvus 检索命中：hit.entity.get('text')"""
        def __init__(self, text):
            self.entity = {"text": text}

    monkeypatch.setattr(
        "core.vector_store.search_vector",
        lambda *a, **k: [[_Hit("高血压用药指南：低盐饮食、规律监测血压")]],
    )
    from core.medical_rag import rag_search_medical_knowledge
    result = rag_search_medical_knowledge("高血压")
    assert len(result) == 1
    assert "高血压" in result[0]


def test_rag_filters_by_distance_threshold(monkeypatch):
    """距离超过阈值（不相关噪声）→ 丢弃；低于阈值保留"""
    monkeypatch.setattr("core.medical_rag._safe_get_embedding", lambda text: [0.0] * 384)
    from config.settings import settings
    from core.medical_rag import rag_search_medical_knowledge

    class _Hit:
        def __init__(self, text, distance):
            self.entity = {"text": text}
            self.distance = distance

    # 一个相关（0.5 < 阈值），两个噪声（1.2 / 1.5 > 默认阈值 1.0）
    monkeypatch.setattr(
        "core.vector_store.search_vector",
        lambda *a, **k: [[
            _Hit("高血压用药指南：低盐饮食、规律监测血压", 0.5),
            _Hit("编程语言教程", 1.2),
            _Hit("旅游攻略", 1.5),
        ]],
    )
    result = rag_search_medical_knowledge("高血压")
    assert len(result) == 1
    assert "高血压" in result[0]

    # 无 distance 属性的命中（兼容模拟对象）默认保留，不误伤
    class _HitNoDist:
        def __init__(self, text):
            self.entity = {"text": text}

    monkeypatch.setattr(
        "core.vector_store.search_vector",
        lambda *a, **k: [[_HitNoDist("糖尿病饮食建议")]],
    )
    result = rag_search_medical_knowledge("糖尿病")
    assert len(result) == 1
    assert "糖尿病" in result[0]
