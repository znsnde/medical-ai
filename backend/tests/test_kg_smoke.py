"""
医学知识图谱冒烟测试（依赖本地 Neo4j）
"""
from conftest import requires_neo4j, auth_headers


@requires_neo4j
def test_graph_full(client, admin_token):
    """全图数据：节点/关系数量 > 0"""
    r = client.get("/api/kg/graph", headers=auth_headers(admin_token))
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data["nodes"]) > 0
    assert len(data["links"]) > 0


@requires_neo4j
def test_graph_center_expansion(client, admin_token):
    """以「高血压」为中心展开子图 → 包含该节点"""
    r = client.get("/api/kg/graph", params={"center": "高血压", "depth": 2},
                   headers=auth_headers(admin_token))
    assert r.status_code == 200
    nodes = r.json()["data"]["nodes"]
    assert any(n["label"] == "高血压" for n in nodes)


@requires_neo4j
def test_graph_unknown_center_empty(client, admin_token):
    """不存在的中心 → 空 nodes"""
    r = client.get("/api/kg/graph", params={"center": "不存在的疾病XYZ"},
                   headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert r.json()["data"]["nodes"] == []


@requires_neo4j
def test_search_for_diagnosis_structure():
    """诊断关联知识查询返回约定结构（疾病/用药相互作用/并发症），支持用药清单"""
    from medical_business.knowledge_graph import search_for_diagnosis
    result = search_for_diagnosis("患者高血压伴头晕", medicines=["硝苯地平"])
    assert isinstance(result, dict)
    assert set(result.keys()) >= {"related_info", "drug_warnings", "complications"}
    # 高血压的病症命中
    assert any(r["disease"] == "高血压" for r in result["related_info"])
    # 用药相互作用返回结构正确
    for w in result["drug_warnings"]:
        assert w["drug"] == "硝苯地平"
        assert "interacts_with" in w


@requires_neo4j
def test_search_for_diagnosis_empty_on_no_match():
    """无命中 → 空结构"""
    from medical_business.knowledge_graph import search_for_diagnosis
    result = search_for_diagnosis("")
    assert result == {"related_info": [], "drug_warnings": [], "complications": []}
