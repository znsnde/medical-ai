"""
知识图谱查询 API
"""
from fastapi import APIRouter, Depends, Query
from core.security import get_current_user
from medical_business.knowledge_graph import (
    query_disease_info, query_by_symptom, search_all, query_drug_interaction, query_graph
)
from utils.common import resp_success

router = APIRouter()


@router.get("/disease", summary="查询疾病信息")
def kg_disease(name: str = Query(..., description="疾病名称"),
               user=Depends(get_current_user)):
    data = query_disease_info(name)
    return resp_success(data=data)


@router.get("/symptom", summary="按症状查询疾病")
def kg_symptom(symptom: str = Query(..., description="症状名称"),
               user=Depends(get_current_user)):
    data = query_by_symptom(symptom)
    return resp_success(data=data)


@router.get("/search", summary="全局搜索")
def kg_search(keyword: str = Query(..., description="关键词"),
              user=Depends(get_current_user)):
    data = search_all(keyword)
    return resp_success(data=data)


@router.get("/interaction", summary="查询药物相互作用")
def kg_interaction(drug: str = Query(..., description="药物名称"),
                   user=Depends(get_current_user)):
    data = query_drug_interaction(drug)
    return resp_success(data=data)


@router.get("/graph", summary="知识图谱可视化数据")
def kg_graph(center: str = Query(None, description="中心节点名称，为空返回全图"),
             depth: int = Query(2, ge=1, le=4, description="展开深度"),
             user=Depends(get_current_user)):
    data = query_graph(center, depth)
    return resp_success(data=data)
