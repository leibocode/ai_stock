from typing import TypeVar, Generic, Optional, Any
from pydantic import BaseModel

T = TypeVar('T')


class Response(BaseModel, Generic[T]):
    """统一API响应格式"""
    code: int = 0
    data: Optional[T] = None
    msg: str = "success"

    class Config:
        json_schema_extra = {
            "example": {
                "code": 0,
                "data": [],
                "msg": "success"
            }
        }


def success(data: Any, msg: str = "success") -> dict:
    """成功响应"""
    return {
        "code": 0,
        "data": data,
        "msg": msg
    }


def error(msg: str, code: int = 1) -> dict:
    """错误响应"""
    return {
        "code": code,
        "data": None,
        "msg": msg
    }
