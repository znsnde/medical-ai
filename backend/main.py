import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.settings import settings
from core.logger import setup_logging, get_logger

# 导入全部业务路由
from api import record_api, diagnosis_api, patient_api, paper_api, report_api, auth_api, dashboard_api, dicom_api, reference_image_api, consultation_api, system_api, kg_api, recycle_api
import db.models
import uvicorn

# 初始化日志（root logger，各模块自动继承）
setup_logging()
logger = get_logger("main")

# 初始化FastAPI应用
app = FastAPI(
    title="智慧医疗辅助诊断与电子病历结构化系统",
    version="1.0",
    description="实现病历结构化、AI辅助诊断、患者随访、医学文献速读、诊断报告导出全功能"
)

# ── CORS（生产跨域；开发期由 vite proxy 转发，此处保证直接访问后端也放行） ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 全局异常处理：统一 JSON 包装，保留 HTTP 状态码（前端拦截器依赖 status） ──
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning("HTTP %s 请求失败 %s: %s", exc.status_code, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "msg": exc.detail, "detail": exc.detail, "data": None},
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("未处理异常 %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "msg": "服务器内部错误，请稍后重试", "detail": "服务器内部错误", "data": None},
    )

# 注：不挂载 /static 公开目录。上传文件（报告PDF/DICOM/文献）一律经带鉴权接口下载，
# 避免患者隐私文件被未授权访问（参考影像经 /api/reference-image 鉴权返回）。

# 注册所有模块路由
app.include_router(
    record_api.router,
    prefix="/api/record",
    tags=["病历智能结构化模块"]
)
app.include_router(
    diagnosis_api.router,
    prefix="/api/diagnosis",
    tags=["AI辅助诊断模块"]
)
app.include_router(
    patient_api.router,
    prefix="/api/patient",
    tags=["患者随访&问答模块"]
)
app.include_router(
    patient_api.protected,
    prefix="/api/patient",
    tags=["患者管理模块(受保护)"]
)
app.include_router(
    paper_api.router,
    prefix="/api/paper",
    tags=["医学文献速读模块"]
)
app.include_router(
    report_api.router,
    prefix="/api/report",
    tags=["诊断可视化报告模块"]
)
app.include_router(
    auth_api.router,
    prefix="/api/auth",
    tags=["用户认证模块"]
)
app.include_router(
    dashboard_api.router,
    prefix="/api/dashboard",
    tags=["仪表盘模块"]
)
app.include_router(
    dicom_api.router,
    prefix="/api/dicom",
    tags=["DICOM影像模块"]
)
app.include_router(
    reference_image_api.router,
    prefix="/api/reference-image",
    tags=["典型病例参考影像模块"]
)
app.include_router(
    consultation_api.router,
    prefix="/api/consultation",
    tags=["智能问诊模块"]
)
app.include_router(
    system_api.router,
    prefix="/api/system",
    tags=["系统管理模块"]
)
app.include_router(
    kg_api.router,
    prefix="/api/kg",
    tags=["医学知识图谱模块"]
)
app.include_router(
    recycle_api.router,
    prefix="/api/recycle",
    tags=["回收站模块"]
)

# 根路径测试接口
@app.get("/", summary="服务健康检测接口")
def root():
    return {
        "msg": "智慧医疗后端服务启动成功",
        "server_port": settings.SERVER_PORT,
        "docs_url": "http://127.0.0.1:8000/docs"
    }

# 程序入口启动
if __name__ == "__main__":
    # schema 由 Alembic 统一管理：迁移失败直接阻塞启动（缺表时应用不可用）
    from db import migrate
    migrate.run()
    import platform
    use_reload = platform.system() != "Windows"  # Windows下关闭热重载避免进程残留
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.SERVER_PORT,
        reload=use_reload
    )