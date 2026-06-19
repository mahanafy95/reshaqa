"""راوتر المساعد الصحي الذكي — محادثة حرّة متعددة الأدوار (منفصلة عن تسجيل الوجبات).

POST '/assistant/chat' يستقبل آخر أدوار المحادثة ويرجّع ردّ المساعد. لا يرجّع 500 أبداً:
لو المساعد الذكي متعطّل أو فشل، يرجّع ردّ ودّي بالعربي يوضّح إنه لسه مش مفعّل.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..core.ratelimit import limiter
from ..database import get_db
from ..models.enums import Sex, TargetMode
from ..models.profile import Profile
from ..models.user import User
from ..services import ai_assistant
from ..services.calories import determine_mode
from ..services.targets_service import get_current_weight

router = APIRouter(prefix="/assistant", tags=["المساعد الذكي"])

# ردّ ودّي ثابت لمّا المساعد الذكي مش مفعّل أو فشل (نرجع 200 دايماً، مفيش 500).
_AI_OFF_REPLY = (
    "المساعد الذكي لسه مش مفعّل — فعّل المفتاح المجاني وهبقى أرد عليك في أي حاجة 🙏"
)

_SEX_AR = {Sex.male: "ذكر", Sex.female: "أنثى"}
_MODE_AR = {
    TargetMode.loss: "تخسيس",
    TargetMode.maintain: "تثبيت",
    TargetMode.gain: "زيادة وزن",
}


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


class ChatResponse(BaseModel):
    reply: str


def _build_profile_summary(db: Session, user: User) -> str | None:
    """يبني سياق مختصر عن المستخدم من ملفه الشخصي لتخصيص ردّ المساعد (أو None لو مفيش ملف)."""
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        return None

    current_weight = get_current_weight(db, user.id, profile)
    mode = determine_mode(current_weight, profile.height_cm, profile.goal_weight_kg)

    parts: list[str] = []
    sex_ar = _SEX_AR.get(profile.sex)
    if sex_ar:
        parts.append(f"الجنس: {sex_ar}")
    if profile.age:
        parts.append(f"العمر: {profile.age} سنة")
    parts.append(f"الوزن الحالي: {round(current_weight, 1):g} كجم")
    if profile.goal_weight_kg is not None:
        parts.append(f"الوزن المستهدف: {profile.goal_weight_kg:g} كجم")
    parts.append(f"الهدف: {_MODE_AR.get(mode, 'تثبيت')}")
    return "، ".join(parts)


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
def chat(
    request: Request,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """محادثة حرّة مع المساعد الصحي الذكي — يرد دايماً 200 (تدهور رشيق بدون 500)."""
    messages = [{"role": m.role, "content": m.content} for m in payload.messages]

    profile_summary = _build_profile_summary(db, current_user)

    reply = ai_assistant.chat_reply(messages, profile_summary)
    if not reply:
        reply = _AI_OFF_REPLY
    return ChatResponse(reply=reply)
