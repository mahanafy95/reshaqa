"""راوتر المجتمع — الأصدقاء والرسائل (يضيفوا بعض ويشجّعوا بعض)."""
import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..database import get_db
from ..models.social import Friendship, Message
from ..models.user import User
from ..schemas.social import (
    FriendOut,
    FriendsListOut,
    MessageOut,
    SendMessageIn,
    UnreadOut,
    UserSearchOut,
)

router = APIRouter(prefix="/social", tags=["المجتمع"])

_CHEERS = [
    "كمّل، إنت جامد! 💪",
    "فخور بيك 👏 خطوة كمان!",
    "يوم جديد وفرصة جديدة 🌟",
    "إنت أقوى من اللي فاكر 💚",
    "خطوة بخطوة بتوصل لهدفك 🎯",
    "استمر، التزامك بيلهمني 🔥",
]


def _pair(db: Session, a: int, b: int) -> Friendship | None:
    """يرجّع صف الصداقة بين مستخدمين في أي اتجاه (أو None)."""
    return db.scalar(
        select(Friendship).where(
            or_(
                and_(Friendship.requester_id == a, Friendship.addressee_id == b),
                and_(Friendship.requester_id == b, Friendship.addressee_id == a),
            )
        )
    )


def _require_friends(db: Session, a: int, b: int) -> None:
    fr = _pair(db, a, b)
    if fr is None or fr.status != "accepted":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="لازم تكونوا أصدقاء الأول.")


def _user_or_404(db: Session, user_id: int) -> User:
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستخدم غير موجود.")
    return u


@router.get("/search", response_model=list[UserSearchOut])
def search_users(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """بحث عن مستخدمين بالاسم لإضافتهم (مع حالة العلاقة معاك)."""
    rows = db.scalars(
        select(User)
        .where(func.lower(User.username).like(f"%{q.strip().lower()}%"), User.id != current_user.id)
        .limit(20)
    ).all()
    out: list[UserSearchOut] = []
    for u in rows:
        fr = _pair(db, current_user.id, u.id)
        if fr is None:
            rel = "none"
        elif fr.status == "accepted":
            rel = "friend"
        elif fr.requester_id == current_user.id:
            rel = "pending_out"
        else:
            rel = "pending_in"
        out.append(UserSearchOut(id=u.id, username=u.username, relation=rel))
    return out


@router.post("/friends/request/{user_id}", response_model=FriendsListOut)
def send_friend_request(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="ماتقدرش تضيف نفسك 🙂")
    _user_or_404(db, user_id)
    fr = _pair(db, current_user.id, user_id)
    if fr is not None:
        if fr.status == "accepted":
            raise HTTPException(status_code=409, detail="إنتوا أصدقاء بالفعل.")
        # لو هو طلبك قبل كده → نقبل بدل ما نعمل طلب جديد
        if fr.requester_id == user_id:
            fr.status = "accepted"
            db.commit()
        else:
            raise HTTPException(status_code=409, detail="بعتّ طلب صداقة بالفعل.")
    else:
        db.add(Friendship(requester_id=current_user.id, addressee_id=user_id, status="pending"))
        db.commit()
    return _friends_list(db, current_user.id)


@router.post("/friends/{user_id}/accept", response_model=FriendsListOut)
def accept_friend(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fr = db.scalar(
        select(Friendship).where(
            Friendship.requester_id == user_id,
            Friendship.addressee_id == current_user.id,
            Friendship.status == "pending",
        )
    )
    if fr is None:
        raise HTTPException(status_code=404, detail="مفيش طلب صداقة من المستخدم ده.")
    fr.status = "accepted"
    db.commit()
    return _friends_list(db, current_user.id)


@router.delete("/friends/{user_id}", response_model=FriendsListOut)
def remove_or_decline(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """يرفض طلباً أو يحذف صداقة (في أي اتجاه)."""
    fr = _pair(db, current_user.id, user_id)
    if fr is not None:
        db.delete(fr)
        db.commit()
    return _friends_list(db, current_user.id)


def _unread_from(db: Session, me: int, other: int) -> int:
    return db.scalar(
        select(func.count()).select_from(Message).where(
            Message.sender_id == other, Message.recipient_id == me, Message.read_at.is_(None)
        )
    ) or 0


def _friends_list(db: Session, me: int) -> FriendsListOut:
    rows = db.scalars(
        select(Friendship).where(
            or_(Friendship.requester_id == me, Friendship.addressee_id == me)
        )
    ).all()
    friends: list[FriendOut] = []
    incoming: list[FriendOut] = []
    outgoing: list[FriendOut] = []
    for fr in rows:
        other_id = fr.addressee_id if fr.requester_id == me else fr.requester_id
        other = db.get(User, other_id)
        if other is None:
            continue
        if fr.status == "accepted":
            friends.append(FriendOut(user_id=other.id, username=other.username, status="accepted",
                                     direction="friend", unread=_unread_from(db, me, other.id)))
        elif fr.requester_id == me:
            outgoing.append(FriendOut(user_id=other.id, username=other.username, status="pending",
                                      direction="outgoing"))
        else:
            incoming.append(FriendOut(user_id=other.id, username=other.username, status="pending",
                                      direction="incoming"))
    return FriendsListOut(friends=friends, incoming=incoming, outgoing=outgoing)


@router.get("/friends", response_model=FriendsListOut)
def list_friends(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _friends_list(db, current_user.id)


@router.get("/messages/{user_id}", response_model=list[MessageOut])
def conversation(
    user_id: int,
    after_id: int = Query(0, ge=0, description="آخر رسالة عندك — يرجّع الأحدث منها (للاستطلاع)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """محادثة مع صديق. يعلّم الرسائل الواردة كمقروءة. ادعم after_id للاستطلاع الدوري."""
    _require_friends(db, current_user.id, user_id)
    me = current_user.id
    stmt = (
        select(Message)
        .where(
            or_(
                and_(Message.sender_id == me, Message.recipient_id == user_id),
                and_(Message.sender_id == user_id, Message.recipient_id == me),
            ),
            Message.id > after_id,
        )
        .order_by(Message.id.asc())
        .limit(200)
    )
    msgs = db.scalars(stmt).all()
    # علّم الوارد كمقروء
    now = datetime.now(timezone.utc)
    changed = False
    for m in msgs:
        if m.recipient_id == me and m.read_at is None:
            m.read_at = now
            changed = True
    if changed:
        db.commit()
    return [
        MessageOut(id=m.id, sender_id=m.sender_id, recipient_id=m.recipient_id, body=m.body,
                   kind=m.kind, created_at=m.created_at, mine=m.sender_id == me)
        for m in msgs
    ]


def _send(db: Session, me: int, to: int, body: str, kind: str) -> Message:
    msg = Message(sender_id=me, recipient_id=to, body=body, kind=kind)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.post("/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(
    payload: SendMessageIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_friends(db, current_user.id, payload.to_user_id)
    m = _send(db, current_user.id, payload.to_user_id, payload.body.strip(), "text")
    return MessageOut(id=m.id, sender_id=m.sender_id, recipient_id=m.recipient_id, body=m.body,
                      kind=m.kind, created_at=m.created_at, mine=True)


@router.post("/cheer/{user_id}", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def cheer(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """يبعت رسالة تشجيع سريعة لصديق."""
    _require_friends(db, current_user.id, user_id)
    m = _send(db, current_user.id, user_id, random.choice(_CHEERS), "cheer")
    return MessageOut(id=m.id, sender_id=m.sender_id, recipient_id=m.recipient_id, body=m.body,
                      kind=m.kind, created_at=m.created_at, mine=True)


@router.get("/unread", response_model=UnreadOut)
def total_unread(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total = db.scalar(
        select(func.count()).select_from(Message).where(
            Message.recipient_id == current_user.id, Message.read_at.is_(None)
        )
    ) or 0
    return UnreadOut(total=total)
