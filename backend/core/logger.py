"""
统一日志模块
- 控制台输出 + 滚动文件（logs/backend.log，10MB × 5）
- setup_logging() 在 main.py 启动时调用一次，配置 root logger
"""
import logging
import os
from logging.handlers import RotatingFileHandler

# 日志目录：backend/logs/
_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "backend.log")
_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

_configured = False


def setup_logging(level: int = logging.INFO):
    """初始化日志（幂等，重复调用无副作用）"""
    global _configured
    if _configured:
        return

    os.makedirs(_LOG_DIR, exist_ok=True)
    fmt = logging.Formatter(_FORMAT)

    root = logging.getLogger()
    root.setLevel(level)

    # 控制台输出
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    # 滚动文件输出（10MB 滚动，保留 5 份）
    file_handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    _configured = True


def get_logger(name: str = "app") -> logging.Logger:
    """获取命名 logger（配置在 root 上，各模块自动继承）"""
    return logging.getLogger(name)


def get_log_dir() -> str:
    """日志目录（backend/logs/），供审计查询等定位使用"""
    return _LOG_DIR


def get_log_file_path() -> str:
    """当前滚动日志文件（logs/backend.log）"""
    return _LOG_FILE
