from typing import Any, Optional

from pydantic import BaseModel


class BaseResponse(BaseModel):
    status: str
    message: str
    data: Optional[Any] = None