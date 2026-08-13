def resp_success(data=None, msg: str = "操作成功"):
    """成功返回统一格式"""
    return {
        "code": 200,
        "msg": msg,
        "data": data
    }

def resp_fail(msg: str = "操作失败", code: int = 400):
    """失败返回统一格式"""
    return {
        "code": code,
        "msg": msg,
        "data": None
    }