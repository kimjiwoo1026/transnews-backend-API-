from typing import Any, Optional, List
from pydantic import BaseModel

class NewsItem(BaseModel):
    title: str
    link: str
    article_link: str
    original_url: str
    source_name: str
    source_url: Optional[str] = None
    published: str
    content: str  

class BaseResponse(BaseModel):
    status: str
    message: str
    data: Optional[List[NewsItem]] = None