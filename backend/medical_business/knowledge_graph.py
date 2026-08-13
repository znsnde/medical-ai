"""
医学知识图谱模块
使用 Neo4j 存储疾病、症状、用药、治疗方案的关联关系
"""
from neo4j import GraphDatabase
from config.settings import settings
from core.logger import get_logger

logger = get_logger(__name__)

# Neo4j 配置（从 settings / .env 读取）
NEO4J_URI = settings.NEO4J_URI
NEO4J_USER = settings.NEO4J_USER
NEO4J_PASS = settings.NEO4J_PASS

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    return _driver


def close():
    global _driver
    if _driver:
        _driver.close()
        _driver = None


# ════════════════════════════════════════
#  查询接口
# ════════════════════════════════════════

def query_disease_info(disease_name: str) -> list:
    """查询疾病关联的症状、用药、科室"""
    with get_driver().session() as session:
        result = session.run("""
            MATCH (d:Disease {name: $name})
            OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
            OPTIONAL MATCH (d)-[:TREATED_BY]->(m:Medication)
            OPTIONAL MATCH (d)-[:BELONGS_TO]->(dept:Department)
            OPTIONAL MATCH (d)-[:HAS_TREATMENT]->(t:Treatment)
            RETURN d.name as disease,
                   collect(DISTINCT s.name) as symptoms,
                   collect(DISTINCT m.name) as medications,
                   collect(DISTINCT dept.name) as departments,
                   collect(DISTINCT t.name) as treatments
        """, name=disease_name)
        return [dict(r) for r in result]


def query_by_symptom(symptom: str) -> list:
    """根据症状查询可能的疾病"""
    with get_driver().session() as session:
        result = session.run("""
            MATCH (s:Symptom {name: $symptom})<-[:HAS_SYMPTOM]-(d:Disease)
            OPTIONAL MATCH (d)-[:TREATED_BY]->(m:Medication)
            RETURN d.name as disease, collect(DISTINCT m.name) as medications
        """, symptom=symptom)
        return [dict(r) for r in result]


def query_drug_interaction(drug_name: str) -> list:
    """查询药物相互作用"""
    with get_driver().session() as session:
        result = session.run("""
            MATCH (m:Medication {name: $drug})-[:INTERACTS_WITH]->(other:Medication)
            RETURN other.name as interacts_with,
                   m.contraindications as contraindications
        """, drug=drug_name)
        return [dict(r) for r in result]


def _node_id(node) -> str:
    """生成节点唯一 id：类型:名称"""
    labels = list(node.labels)
    label = labels[0] if labels else "Node"
    return f"{label}:{node.get('name', '')}"


def query_graph(center: str = None, depth: int = 2) -> dict:
    """返回知识图谱可视化数据 {nodes, links}

    - center 为空：返回全图所有节点与关系
    - center 非空：返回以该节点为中心、向外 depth 层的子图
    """
    nodes_map = {}   # id -> {id, label, type}
    links = []       # {source, target, rel, desc}
    link_keys = set()

    def add_node(node):
        nid = _node_id(node)
        if nid not in nodes_map:
            nodes_map[nid] = {"id": nid, "label": node["name"], "type": list(node.labels)[0]}

    def add_link(src, tgt, rel, desc):
        key = (src, tgt, rel)
        if key not in link_keys:
            link_keys.add(key)
            links.append({"source": src, "target": tgt, "rel": rel, "desc": desc})

    # 路径深度在 Cypher 中不能用参数，这里取整后作为字面量拼接（调用方已限制 1~4）
    depth = max(1, min(int(depth), 4))

    with get_driver().session() as session:
        if center:
            # 以 center 为中心向外扩展 depth 层的子图
            node_result = session.run(
                f"""MATCH (c {{name: $center}})
                    OPTIONAL MATCH p = (c)-[r*1..{depth}]-(m)
                    UNWIND nodes(p) AS nd
                    RETURN DISTINCT nd
                """, center=center)
            rel_result = session.run(
                f"""MATCH (c {{name: $center}})
                    OPTIONAL MATCH p = (c)-[r*1..{depth}]-(m)
                    UNWIND relationships(p) AS rr
                    RETURN DISTINCT startNode(rr) AS sn, endNode(rr) AS tn,
                           type(rr) AS rel, coalesce(rr.description, '') AS desc
                """, center=center)
            for rec in node_result:
                add_node(rec["nd"])
            for rec in rel_result:
                add_node(rec["sn"])
                add_node(rec["tn"])
                add_link(
                    _node_id(rec["sn"]), _node_id(rec["tn"]),
                    rec["rel"], rec["desc"]
                )
        else:
            # 全图
            node_result = session.run(
                "MATCH (n) RETURN n"
            )
            for rec in node_result:
                add_node(rec["n"])
            rel_result = session.run(
                """MATCH (n)-[r]->(m)
                   RETURN n AS sn, m AS tn, type(r) AS rel,
                          coalesce(r.description, '') AS desc
                """
            )
            for rec in rel_result:
                add_link(
                    _node_id(rec["sn"]), _node_id(rec["tn"]),
                    rec["rel"], rec["desc"]
                )

    return {"nodes": list(nodes_map.values()), "links": links}


def query_related_diseases(disease_name: str) -> list:
    """查询相关/并发症疾病"""
    with get_driver().session() as session:
        result = session.run("""
            MATCH (d:Disease {name: $name})-[:COMPLICATION_OF]->(related:Disease)
            RETURN related.name as related_disease
        """, name=disease_name)
        return [dict(r) for r in result]


def search_all(keyword: str) -> dict:
    """全局搜索疾病/症状/药物"""
    with get_driver().session() as session:
        diseases = session.run(
            "MATCH (d:Disease) WHERE d.name CONTAINS $k RETURN d.name as name LIMIT 10",
            k=keyword
        )
        symptoms = session.run(
            "MATCH (s:Symptom) WHERE s.name CONTAINS $k RETURN s.name as name LIMIT 10",
            k=keyword
        )
        meds = session.run(
            "MATCH (m:Medication) WHERE m.name CONTAINS $k RETURN m.name as name LIMIT 10",
            k=keyword
        )
        return {
            "diseases": [r["name"] for r in diseases],
            "symptoms": [r["name"] for r in symptoms],
            "medications": [r["name"] for r in meds],
        }


# ════════════════════════════════════════
#  初始化种子数据
# ════════════════════════════════════════

SEED_DATA = {
    "diseases": [
        {
            "name": "高血压",
            "symptoms": ["头痛", "头晕", "心悸", "耳鸣", "视力模糊"],
            "medications": ["硝苯地平", "卡托普利", "氯沙坦", "氢氯噻嗪"],
            "department": "内科",
            "treatments": ["低盐饮食", "规律运动", "定期监测血压", "戒烟限酒"],
        },
        {
            "name": "脑梗死",
            "symptoms": ["偏瘫", "言语不清", "口眼歪斜", "头晕", "意识障碍"],
            "medications": ["阿司匹林", "氯吡格雷", "阿托伐他汀", "依达拉奉"],
            "department": "神经内科",
            "treatments": ["溶栓治疗", "康复训练", "抗血小板治疗"],
        },
        {
            "name": "脑出血",
            "symptoms": ["剧烈头痛", "恶心呕吐", "意识丧失", "偏瘫", "癫痫"],
            "medications": ["甘露醇", "尼莫地平", "氨甲环酸"],
            "department": "神经内科",
            "treatments": ["外科手术", "颅内压监测", "止血治疗"],
        },
        {
            "name": "肺炎",
            "symptoms": ["发热", "咳嗽", "胸痛", "咳痰", "呼吸困难"],
            "medications": ["阿莫西林", "头孢呋辛", "左氧氟沙星", "阿奇霉素"],
            "department": "内科",
            "treatments": ["抗生素治疗", "雾化吸入", "氧疗"],
        },
        {
            "name": "慢阻肺",
            "symptoms": ["气短", "咳嗽", "咳痰", "喘息", "胸闷"],
            "medications": ["沙丁胺醇", "异丙托溴铵", "布地奈德", "茶碱"],
            "department": "内科",
            "treatments": ["戒烟", "氧疗", "肺康复训练"],
        },
        {
            "name": "腰椎间盘突出症",
            "symptoms": ["腰痛", "腿麻", "下肢放射痛", "行走困难", "腰部活动受限"],
            "medications": ["布洛芬", "甲钴胺", "乙哌立松"],
            "department": "骨科",
            "treatments": ["卧床休息", "物理治疗", "微创手术"],
        },
        {
            "name": "骨折",
            "symptoms": ["局部疼痛", "肿胀", "畸形", "活动受限", "骨擦音"],
            "medications": ["布洛芬", "塞来昔布", "钙片"],
            "department": "骨科",
            "treatments": ["石膏固定", "手术治疗", "康复锻炼"],
        },
        {
            "name": "冠心病",
            "symptoms": ["胸闷", "胸痛", "心悸", "气短", "乏力"],
            "medications": ["阿司匹林", "硝酸甘油", "美托洛尔", "阿托伐他汀"],
            "department": "内科",
            "treatments": ["冠脉支架", "搭桥手术", "生活方式干预"],
        },
        {
            "name": "2型糖尿病",
            "symptoms": ["多饮", "多食", "多尿", "体重下降", "乏力"],
            "medications": ["二甲双胍", "格列美脲", "胰岛素", "阿卡波糖"],
            "department": "内科",
            "treatments": ["饮食控制", "运动疗法", "血糖监测"],
        },
        {
            "name": "上呼吸道感染",
            "symptoms": ["发热", "咽痛", "鼻塞", "流涕", "咳嗽"],
            "medications": ["对乙酰氨基酚", "布洛芬", "氯苯那敏"],
            "department": "内科",
            "treatments": ["多休息", "多饮水", "对症治疗"],
        },
        {
            "name": "心力衰竭",
            "symptoms": ["呼吸困难", "乏力", "水肿", "心悸", "端坐呼吸"],
            "medications": ["呋塞米", "螺内酯", "培哚普利", "美托洛尔"],
            "department": "心内科",
            "treatments": ["限盐限水", "利尿治疗", "心脏康复"],
        },
        {
            "name": "消化性溃疡",
            "symptoms": ["上腹痛", "反酸", "烧心", "恶心", "黑便"],
            "medications": ["奥美拉唑", "雷尼替丁", "硫糖铝"],
            "department": "消化内科",
            "treatments": ["抑酸治疗", "根除幽门螺杆菌", "饮食调理"],
        },
        {
            "name": "哮喘",
            "symptoms": ["喘息", "胸闷", "气促", "咳嗽", "夜间加重"],
            "medications": ["沙丁胺醇", "布地奈德", "孟鲁司特"],
            "department": "呼吸内科",
            "treatments": ["规律吸入治疗", "避免过敏原", "急性发作处理"],
        },
        {
            "name": "肺结核",
            "symptoms": ["咳嗽", "咳痰", "低热", "盗汗", "消瘦"],
            "medications": ["异烟肼", "利福平", "吡嗪酰胺"],
            "department": "呼吸内科",
            "treatments": ["联合抗结核治疗", "规律服药", "痰菌监测"],
        },
        {
            "name": "病毒性肝炎",
            "symptoms": ["乏力", "食欲不振", "黄疸", "恶心", "肝区不适"],
            "medications": ["恩替卡韦", "替诺福韦", "甘草酸二铵"],
            "department": "感染科",
            "treatments": ["抗病毒治疗", "保肝治疗", "定期复查肝功能"],
        },
        {
            "name": "甲状腺功能亢进",
            "symptoms": ["心悸", "多汗", "手抖", "体重下降", "易怒"],
            "medications": ["甲巯咪唑", "丙硫氧嘧啶", "普萘洛尔"],
            "department": "内分泌科",
            "treatments": ["抗甲状腺药物治疗", "碘131治疗", "定期复查甲状腺功能"],
        },
        {
            "name": "胆囊炎",
            "symptoms": ["右上腹痛", "恶心呕吐", "发热", "黄疸"],
            "medications": ["头孢曲松", "甲硝唑", "山莨菪碱"],
            "department": "普外科",
            "treatments": ["抗感染治疗", "禁食胃肠减压", "胆囊切除手术"],
        },
        {
            "name": "肾结石",
            "symptoms": ["腰痛", "血尿", "尿频", "恶心"],
            "medications": ["坦索罗辛", "布洛芬", "枸橼酸钾"],
            "department": "泌尿外科",
            "treatments": ["大量饮水", "体外冲击波碎石", "输尿管镜碎石"],
        },
        {
            "name": "贫血",
            "symptoms": ["乏力", "头晕", "面色苍白", "心悸", "气短"],
            "medications": ["硫酸亚铁", "叶酸", "维生素B12"],
            "department": "内科",
            "treatments": ["补铁治疗", "病因治疗", "饮食补充"],
        },
        {
            "name": "骨质疏松症",
            "symptoms": ["腰背痛", "身高变矮", "骨痛", "易骨折"],
            "medications": ["阿仑膦酸钠", "碳酸钙", "维生素D"],
            "department": "骨科",
            "treatments": ["补钙", "抗骨质疏松药物", "防跌倒训练"],
        },
    ],
    "interactions": [
        ("阿司匹林", "布洛芬", "增加出血风险"),
        ("阿司匹林", "氯吡格雷", "联合使用增加出血风险"),
        ("硝苯地平", "克拉霉素", "增加低血压风险"),
        ("卡托普利", "氯沙坦", "不推荐联合使用"),
        ("华法林", "阿司匹林", "显著增加出血风险"),
        ("二甲双胍", "碘造影剂", "可能引起乳酸酸中毒"),
        ("美托洛尔", "硝苯地平", "联合降压可能引起心动过缓或血压过低"),
        ("奥美拉唑", "氯吡格雷", "奥美拉唑可能降低氯吡格雷的抗血小板活性"),
        ("二甲双胍", "胰岛素", "联合使用增加低血糖风险"),
        ("呋塞米", "布洛芬", "布洛芬可能减弱呋塞米的利尿效果并增加肾损伤风险"),
        ("沙丁胺醇", "普萘洛尔", "非选择性β受体阻滞剂可能拮抗支气管扩张作用"),
        ("阿仑膦酸钠", "碳酸钙", "两者需间隔服用，以免影响吸收"),
    ],
    "complications": [
        ("高血压", "脑梗死"),
        ("高血压", "冠心病"),
        ("高血压", "脑出血"),
        ("2型糖尿病", "冠心病"),
        ("2型糖尿病", "脑梗死"),
        ("冠心病", "心力衰竭"),
        ("高血压", "心力衰竭"),
        ("2型糖尿病", "心力衰竭"),
        ("哮喘", "慢阻肺"),
        ("贫血", "心力衰竭"),
        ("甲状腺功能亢进", "心力衰竭"),
        ("骨质疏松症", "骨折"),
    ],
}


def init_graph():
    """初始化/重置知识图谱数据"""
    driver = get_driver()
    with driver.session() as session:
        # 清空旧数据
        session.run("MATCH (n) DETACH DELETE n")

        # 创建节点
        for disease in SEED_DATA["diseases"]:
            session.run(
                "CREATE (d:Disease {name: $name})",
                name=disease["name"]
            )
            # 科室
            if disease["department"]:
                session.run(
                    "MERGE (dept:Department {name: $name})",
                    name=disease["department"]
                )
                session.run(
                    "MATCH (d:Disease {name: $dn}), (dept:Department {name: $dep}) "
                    "MERGE (d)-[:BELONGS_TO]->(dept)",
                    dn=disease["name"], dep=disease["department"]
                )
            # 症状
            for symptom in disease["symptoms"]:
                session.run("MERGE (s:Symptom {name: $name})", name=symptom)
                session.run(
                    "MATCH (d:Disease {name: $dn}), (s:Symptom {name: $sn}) "
                    "MERGE (d)-[:HAS_SYMPTOM]->(s)",
                    dn=disease["name"], sn=symptom
                )
            # 用药
            for med in disease["medications"]:
                session.run("MERGE (m:Medication {name: $name})", name=med)
                session.run(
                    "MATCH (d:Disease {name: $dn}), (m:Medication {name: $mn}) "
                    "MERGE (d)-[:TREATED_BY]->(m)",
                    dn=disease["name"], mn=med
                )
            # 治疗
            for treatment in disease["treatments"]:
                session.run("MERGE (t:Treatment {name: $name})", name=treatment)
                session.run(
                    "MATCH (d:Disease {name: $dn}), (t:Treatment {name: $tn}) "
                    "MERGE (d)-[:HAS_TREATMENT]->(t)",
                    dn=disease["name"], tn=treatment
                )

        # 药物相互作用
        for a, b, desc in SEED_DATA["interactions"]:
            session.run(
                "MATCH (a:Medication {name: $an}), (b:Medication {name: $bn}) "
                "MERGE (a)-[:INTERACTS_WITH {description: $desc}]->(b) "
                "MERGE (b)-[:INTERACTS_WITH {description: $desc}]->(a)",
                an=a, bn=b, desc=desc
            )

        # 并发症
        for a, b in SEED_DATA["complications"]:
            session.run(
                "MATCH (a:Disease {name: $an}), (b:Disease {name: $bn}) "
                "MERGE (a)-[:COMPLICATION_OF]->(b)",
                an=a, bn=b
            )

    logger.info("知识图谱初始化完成：%d 种疾病，%d 条药物相互作用",
                len(SEED_DATA['diseases']), len(SEED_DATA['interactions']))


def search_for_diagnosis(diagnosis_text: str, medicines: list = None) -> dict:
    """AI 诊断时查询知识图谱辅助（Neo4j 数据源）

    返回：
    - related_info: 诊断文本中命中的疾病及其症状/用药/科室/治疗
    - drug_warnings: 用药清单中的相互作用预警（INTERACTS_WITH）
    - complications: 命中疾病的并发症（COMPLICATION_OF）

    Neo4j 不可用时降级返回空结构，不阻塞诊断主流程。
    """
    result = {"related_info": [], "drug_warnings": [], "complications": []}
    if not diagnosis_text:
        return result

    try:
        with get_driver().session() as session:
            # 1. 命中疾病：疾病名或其任一症状出现在诊断文本中
            disease_rows = session.run("""
                MATCH (d:Disease)
                OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
                OPTIONAL MATCH (d)-[:TREATED_BY]->(m:Medication)
                OPTIONAL MATCH (d)-[:BELONGS_TO]->(dept:Department)
                OPTIONAL MATCH (d)-[:HAS_TREATMENT]->(t:Treatment)
                RETURN d.name AS disease,
                       collect(DISTINCT s.name) AS symptoms,
                       collect(DISTINCT m.name) AS medications,
                       collect(DISTINCT dept.name) AS departments,
                       collect(DISTINCT t.name) AS treatments
            """)
            matched_diseases = []
            for rec in disease_rows:
                name = rec["disease"]
                symptoms = [s for s in rec["symptoms"] if s]
                if name and (name in diagnosis_text or any(s in diagnosis_text for s in symptoms)):
                    matched_diseases.append(name)
                    result["related_info"].append({
                        "disease": name,
                        "symptoms": symptoms,
                        "medications": rec["medications"],
                        "departments": rec["departments"],
                        "treatments": rec["treatments"],
                    })

            # 2. 并发症（命中疾病的 COMPLICATION_OF）
            for name in matched_diseases:
                comp = session.run(
                    "MATCH (d:Disease {name: $n})-[:COMPLICATION_OF]->(r:Disease) "
                    "RETURN r.name AS related",
                    n=name
                )
                for rec in comp:
                    result["complications"].append({
                        "disease": name,
                        "related_disease": rec["related"],
                    })

            # 3. 用药相互作用（用药清单命中 INTERACTS_WITH）
            for drug in (medicines or []):
                if not drug:
                    continue
                inter = session.run(
                    "MATCH (m:Medication {name: $drug})-[r:INTERACTS_WITH]->(o:Medication) "
                    "RETURN o.name AS interacts_with, coalesce(r.description, '') AS description",
                    drug=drug
                )
                for rec in inter:
                    result["drug_warnings"].append({
                        "drug": drug,
                        "interacts_with": rec["interacts_with"],
                        "description": rec["description"],
                    })
    except Exception as e:
        logger.warning("[知识图谱查询跳过] %s", e)
        return {"related_info": [], "drug_warnings": [], "complications": []}

    return result
