"""سكيمات المجتمع — الأصدقاء والرسائل."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class UserSearchOut(BaseModel):
    id: int
    username: str
    relation: str  # none | friend | pending_out | pending_in


class FriendOut(BaseModel):
    user_id: int
    username: str
    status: str          # accepted | pending
    direction: str       # friend | incoming | outgoing
    unread: int = 0


class FriendsListOut(BaseModel):
    friends: list[FriendOut] = []
    incoming: list[FriendOut] = []
    outgoing: list[FriendOut] = []


class MessageOut(BaseModel):
    id: int
    sender_id: int
    recipient_id: int
    body: str
    kind: str
    created_at: datetime
    mine: bool = False


class SendMessageIn(BaseModel):
    to_user_id: int
    body: str = Field(..., min_length=1, max_length=2000)

    @field_validator("body")
    @classmethod
    def _no_blank_body(cls, v: str) -> str:
        # رسالة فيها مسافات بس بتعدّي min_length لكن بتبقى فاضية بعد strip — نرفضها بوضوح.
        v = v.strip()
        if not v:
            raise ValueError("الرسالة فاضية.")
        return v


class UnreadOut(BaseModel):
    total: int
