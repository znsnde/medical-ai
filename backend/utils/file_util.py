import os
from config.settings import settings
from uuid import uuid4

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
    # 拆分文件名后缀
    suffix = filename.split(".")[-1]
    unique_name = f"{uuid4()}.{suffix}"
    save_dir = os.path.join(settings.UPLOAD_PATH, sub_dir)
    full_path = os.path.join(save_dir, unique_name)
    # 返回相对路径（存数据库——始终用正斜杠，保证URL兼容）
    rel_path = f"static/upload/{sub_dir}/{unique_name}"
    return full_path, rel_path