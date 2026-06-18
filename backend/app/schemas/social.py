"""سكيمات المجتمع — الأصدقاء والرسائل."""
from datetime import datetime

from pydantic import BaseModel, Field


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


class UnreadOut(BaseModel):
    total: int
