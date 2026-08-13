import os
import re
from pathlib import Path
from config.settings import settings
from uuid import uuid4

# 各子目录允许的扩展名（白名单，防路径分隔符/恶意后缀注入）
ALLOWED_SUFFIX = {
    "dicom": {"dcm", "dicom", "jpg", "jpeg", "png"},
    "record": {"pdf"},
    "paper": {"pdf"},
    "report": {"pdf"},
}
# 非法后缀时的安全兜底（按子目录取默认）
FALLBACK_SUFFIX = {"dicom": "png", "record": "pdf", "paper": "pdf", "report": "pdf"}

# 自动创建上传根目录
def init_upload_dir():
    if not os.path.exists(settings.UPLOAD_PATH):
        os.makedirs(settings.UPLOAD_PATH)
    # 分文件夹：病历PDF、DICOM影像、文献、生成报告
    sub_dirs = ["record", "dicom", "paper", "report"]
    for d in sub_dirs:
        full_path = os.path.join(settings.UPLOAD_PATH, d)
        if not os.path.exists(full_path):
            os.makedirs(full_path)

# 生成唯一存储路径，避免文件重名覆盖
def get_unique_save_path(sub_dir: str, filename: str) -> str:
    init_upload_dir()
    # 拆分文件名后缀，并剥离一切非字母数字字符（消除路径分隔符注入的可能）
    raw_suffix = filename.rsplit(".", 1)[-1] if "." in filename else ""
    suffix = re.sub(r"[^A-Za-z0-9]", "", raw_suffix).lower()
    allowed = ALLOWED_SUFFIX.get(sub_dir, set())
    if suffix not in allowed:
        suffix = FALLBACK_SUFFIX.get(sub_dir, "bin")
    unique_name = f"{uuid4()}.{suffix}"
    save_dir = os.path.join(settings.UPLOAD_PATH, sub_dir)
    full_path = os.path.join(save_dir, unique_name)
    # 返回相对路径（存数据库——始终用正斜杠，保证URL兼容）
    rel_path = f"static/upload/{sub_dir}/{unique_name}"
    return full_path, rel_path

# 安全删除物理文件：兼容相对/绝对路径，不存在或异常时静默跳过（删除 DB 行前调用）
def safe_unlink(rel_or_abs_path: str):
    if not rel_or_abs_path:
        return
    try:
        p = Path(rel_or_abs_path)
        # 相对路径按当前工作目录解析（存库路径形如 static/upload/report/<uuid>.pdf）
        if p.is_file():
            p.unlink()
    except OSError:
        pass