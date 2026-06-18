"""سكيمات بلاغات المشاكل — إرسال البلاغ وعرضه وتحديث حالته."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class IssueIn(BaseModel):
    message: str = Field(..., min_length=3, max_length=2000)
    context: str | None = Field(None, max_length=200)


class IssueStatusIn(BaseModel):
    status: Literal["new", "seen", "resolved"]


class IssueOut(BaseModel):
    id: int
    user_id: int
    username: str
    message: str
    context: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
