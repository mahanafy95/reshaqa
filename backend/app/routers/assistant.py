"""راوتر المساعد الصحي الذكي — محادثة حرّة متعددة الأدوار + حفظ المحادثة + تسجيل وجبة بالأمر.

- POST '/assistant/chat': يستقبل آخر أدوار المحادثة ويرجّع ردّ المساعد. لا يرجّع 500 أبداً.
  • يحفظ كل دور في قاعدة البيانات (المحادثة تستمر بين الجلسات وعبر الأجهزة).
  • لو المستخدم قال «ضيف/سجّل ...» يستخرج الأصناف من سياق المحادثة ويسجّلها في يومه فعلاً.
- GET  '/assistant/history': يرجّع آخر رسائل محادثة المستخدم (لاستعادتها عند فتح الشاشة).
- DELETE '/assistant/history': يمسح محادثة المستخدم.
"""
import logging
import math
from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.billing import is_user_premium
from ..core.deps import get_current_user
from ..core.ratelimit import limiter
from ..database import get_db
from ..models.assistant import AssistantMessage
from ..models.enums import FoodSource, Meal, Sex, TargetMode
from ..models.food import FoodLogged
from ..models.profile import Profile
from ..models.user import User
from ..schemas._common import validate_log_date
from ..services import ai_assistant, meal_parser
from ..services.calories import determine_mode
from ..services.targets_service import get_current_weight

logger = logging.getLogger("reshaqa.assistant")

router = APIRouter(prefix="/assistant", tags=["المساعد الذكي"])

# حدود معقولة للقيم المستخرَجة من الـ AI (نمنع تسجيل قيم خرافية في يوميات المستخدم).
_MAX_GRAMS = 5000.0       # أقصى وزن للصنف الواحد (5 كجم)
_MAX_KCAL_PER_100 = 1000.0  # أقصى سعرات/100جم واقعية (الزيت الصافي ~900)
# نافذة منع التكرار: لو نفس الصنف اتسجّل في نفس الوجبة/اليوم خلال الثواني دي، نتخطّاه.
_DEDUP_WINDOW_SECONDS = 120

# ردّ ودّي ثابت لمّا المساعد الذكي مش مفعّل أو فشل (نرجع 200 دايماً، مفيش 500).
_AI_OFF_REPLY = (
    "المساعد الذكي لسه مش مفعّل — فعّل المفتاح المجاني وهبقى أرد عليك في أي حاجة 🙏"
)


def _limit_reply() -> str:
    return (
        f"وصلت لحد محادثات المساعد المجانية النهاردة ({settings.FREE_ASSISTANT_DAILY_LIMIT} رسالة) 🌙\n"
        "تقدر تكمّل بكرة، أو تشترك في Premium للاستخدام غير المحدود 💎. "
        "وتقدر دايماً تسجّل أكلك بالكتابة أو يدوي مجاناً."
    )

# أقصى عدد رسائل محفوظة لكل مستخدم (نقصّ الأقدم عشان منكبّرش الجدول بلا حدود).
_HISTORY_KEEP = 400

_SEX_AR = {Sex.male: "ذكر", Sex.female: "أنثى"}
_MODE_AR = {
    TargetMode.loss: "تخسيس",
    TargetMode.maintain: "تثبيت",
    TargetMode.gain: "زيادة وزن",
}
_MEAL_AR = {
    Meal.breakfast: "الفطار",
    Meal.lunch: "الغدا",
    Meal.dinner: "العشا",
    Meal.snack: "السناك",
}


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)
    # تاريخ اليوم المحلي للعميل (لتسجيل الوجبة في اليوم الصح). اختياري — يفضل اليوم لو غاب.
    date: date_type | None = None
    # نوع الوجبة المقترح من العميل (اختياري) — يُستخدم لو الـ AI ماحددش الوجبة.
    default_meal: Meal | None = None

    _v_date = field_validator("date")(validate_log_date)


class LoggedItem(BaseModel):
    name_ar: str
    grams: float
    calories: float
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    meal: str


class ChatResponse(BaseModel):
    reply: str
    logged: bool = False
    logged_items: list[LoggedItem] = []
    logged_total_calories: float = 0
    meal: str | None = None
    limit_reached: bool = False  # وصل المستخدم المجاني للحد اليومي


class HistoryMessage(BaseModel):
    role: str
    content: str
    created_at: datetime


class HistoryResponse(BaseModel):
    messages: list[HistoryMessage] = []


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


def _store_message(db: Session, user_id: int, role: str, content: str) -> None:
    """يضيف رسالة لمحادثة المستخدم (بدون commit — الراوتر بيعمل commit مرة واحدة)."""
    db.add(AssistantMessage(user_id=user_id, role=role, content=content[:8000]))


def _used_today(db: Session, user_id: int) -> int:
    """عدد رسائل المستخدم للمساعد النهاردة (UTC) — لحساب الحد اليومي المجاني."""
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    return db.scalar(
        select(func.count(AssistantMessage.id)).where(
            AssistantMessage.user_id == user_id,
            AssistantMessage.role == "user",
            AssistantMessage.created_at >= start,
        )
    ) or 0


def _daily_limit_reached(db: Session, user: User) -> bool:
    """True لو المستخدم المجاني وصل لحد رسائل المساعد اليومي (Premium غير محدود)."""
    limit = settings.FREE_ASSISTANT_DAILY_LIMIT
    if limit <= 0 or is_user_premium(db, user.id):
        return False
    return _used_today(db, user.id) >= limit


def _prune_history(db: Session, user_id: int) -> None:
    """يقصّ الرسائل الأقدم بحيث نحتفظ بأحدث _HISTORY_KEEP رسالة لكل مستخدم."""
    old_ids = db.scalars(
        select(AssistantMessage.id)
        .where(AssistantMessage.user_id == user_id)
        .order_by(AssistantMessage.id.desc())
        .offset(_HISTORY_KEEP)
    ).all()
    if old_ids:
        db.execute(delete(AssistantMessage).where(AssistantMessage.id.in_(old_ids)))


def _log_extracted_meal(
    db: Session,
    user: User,
    extracted: dict,
    *,
    log_date: date_type,
    default_meal: Meal | None,
) -> tuple[Meal, list[LoggedItem], float]:
    """يسجّل الأصناف المستخرَجة كوجبة في يوم المستخدم. يرجّع (نوع الوجبة، الأصناف، الإجمالي)."""
    # نسعّر الأصناف بنفس منطق /foods/parse (مكتبة أولاً، وإلا تقدير الـ AI، وإلا المقدّر المحلي).
    from .foods import _price_item  # استيراد محلي لتفادي أي حلقة استيراد

    meal_str = extracted.get("meal") or (default_meal.value if default_meal else None) or "snack"
    try:
        meal = Meal(meal_str)
    except ValueError:
        meal = Meal.snack
    if extracted.get("meal") not in ("breakfast", "lunch", "dinner", "snack") and not default_meal:
        logger.info("نوع الوجبة مش واضح — افتراضي snack (user=%s)", user.id)

    # UTC «ساذج» (بدون tzinfo) عشان المقارنة تشتغل على Postgres (timestamptz/UTC) و SQLite (naive UTC) سواء.
    dedup_after = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=_DEDUP_WINDOW_SECONDS)
    logged_items: list[LoggedItem] = []
    total = 0.0
    for it in extracted.get("items", [])[:25]:
        name = (it.get("name_ar") or "").strip()
        grams = _safe_num(it.get("grams"))
        if not name or grams is None or grams <= 0 or grams > _MAX_GRAMS:
            continue  # نتخطّى الأصناف غير الواقعية بدل ما نسجّل قيم فاسدة
        # منع التكرار: نفس الصنف في نفس الوجبة/اليوم خلال الثواني الأخيرة (لو قال «ضيف» تاني)
        dup = db.scalar(
            select(FoodLogged.id).where(
                FoodLogged.user_id == user.id, FoodLogged.date == log_date,
                FoodLogged.meal == meal, FoodLogged.name_ar == name,
                FoodLogged.created_at >= dedup_after,
            )
        )
        if dup is not None:
            continue

        kcal = _safe_num(it.get("kcal_per_100"))
        ai_kcal = kcal if (kcal is not None and 0 < kcal <= _MAX_KCAL_PER_100) else None
        priced = _price_item(db, name, 1.0, None, grams, meal, ai_kcal_per_100=ai_kcal)

        # لو الصنف اتسعّر بتقدير (مش مكتبة) والـ AI أدّى ماكروز، نكمّلها (ماكروز المكتبة أدق فنسيبها).
        p100, c100, f100 = (
            _safe_num(it.get("protein_per_100")), _safe_num(it.get("carbs_per_100")),
            _safe_num(it.get("fat_per_100")),
        )
        if priced.source != FoodSource.library and (p100 or c100 or f100):
            fr = grams / 100.0
            priced = priced.model_copy(update={
                "protein": round((p100 or 0) * fr, 1),
                "carbs": round((c100 or 0) * fr, 1),
                "fat": round((f100 or 0) * fr, 1),
            })

        db.add(
            FoodLogged(
                user_id=user.id, date=log_date, meal=meal, name_ar=priced.name_ar,
                amount=priced.grams, calories=priced.calories, protein=priced.protein,
                carbs=priced.carbs, fat=priced.fat, source=priced.source,
            )
        )
        logged_items.append(
            LoggedItem(
                name_ar=priced.name_ar, grams=priced.grams, calories=priced.calories,
                protein=priced.protein, carbs=priced.carbs, fat=priced.fat, meal=meal.value,
            )
        )
        total += priced.calories
    return meal, logged_items, round(total)


def _safe_num(value) -> float | None:
    """رقم منتهٍ (finite) أو None — يرفض bool/nan/inf (دفاع عند تسجيل وجبة من الـ AI)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    num = float(value)
    return num if math.isfinite(num) else None


def _build_log_confirmation(meal: Meal, items: list[LoggedItem], total: float) -> str:
    meal_ar = _MEAL_AR.get(meal, "وجبة")
    lines = [f"• {it.name_ar} ({round(it.grams)} جم) ≈ {round(it.calories)} سعرة" for it in items]
    return (
        f"تمام ✅ سجّلت في {meal_ar}:\n"
        + "\n".join(lines)
        + f"\nالمجموع ≈ {round(total)} سعرة. تقدر تراجعهم في سجلّ يومك وتعدّل لو محتاج."
    )


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
def chat(
    request: Request,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """محادثة حرّة مع المساعد — تحفظ المحادثة، وتسجّل الأكل لو المستخدم قال «ضيف/سجّل». ترد 200 دايماً."""
    messages = [{"role": m.role, "content": m.content} for m in payload.messages]
    profile_summary = _build_profile_summary(db, current_user)
    last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)

    logged = False
    logged_items: list[LoggedItem] = []
    logged_total = 0.0
    logged_meal: str | None = None
    reply: str | None = None
    limit_reached = False

    # الحد اليومي للمستخدم المجاني — لو وصله، نرجّع رسالة ترقية بدون نداء AI ولا تسجيل.
    if _daily_limit_reached(db, current_user):
        limit_reached = True
        reply = _limit_reply()

    # فعل التسجيل: لو المستخدم طلب يضيف/يسجّل أكل، نستخرجه من سياق المحادثة ونسجّله فعلاً.
    # نحفظ الرسائل بعد ما نخلّص (مرة واحدة) عشان نتجنّب نمط add/rollback/re-add الهشّ.
    if not limit_reached and last_user and settings.ai_enabled and meal_parser.wants_to_log(last_user["content"]):
        try:
            extracted = ai_assistant.extract_meal_to_log(messages)
            if extracted and extracted.get("items"):
                log_date = payload.date or date_type.today()
                meal, logged_items, logged_total = _log_extracted_meal(
                    db, current_user, extracted, log_date=log_date, default_meal=payload.default_meal,
                )
                if logged_items:
                    logged = True
                    logged_meal = meal.value
                    reply = _build_log_confirmation(meal, logged_items, logged_total)
        except Exception:  # تدهور رشيق — أي خطأ في التسجيل يرجّعنا للردّ العادي (مع تسجيل الخطأ)
            logger.exception("فشل تسجيل وجبة من المحادثة (user=%s)", current_user.id)
            db.rollback()  # نمسح أي صفوف FoodLogged أُضيفت جزئياً
            logged, logged_items, logged_total, logged_meal, reply = False, [], 0.0, None, None

    if reply is None and not limit_reached:
        reply = ai_assistant.chat_reply(messages, profile_summary) or _AI_OFF_REPLY

    # حفظ المحادثة (رسالة المستخدم + ردّ المساعد) مرة واحدة بعد اكتمال المعالجة.
    if last_user:
        _store_message(db, current_user.id, "user", last_user["content"])
    _store_message(db, current_user.id, "assistant", reply)
    _prune_history(db, current_user.id)
    db.commit()

    return ChatResponse(
        reply=reply,
        logged=logged,
        logged_items=logged_items,
        logged_total_calories=logged_total,
        meal=logged_meal,
        limit_reached=limit_reached,
    )


@router.get("/history", response_model=HistoryResponse)
@limiter.limit("60/minute")
def history(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=200),
) -> HistoryResponse:
    """آخر رسائل محادثة المستخدم (من الأقدم للأحدث) لاستعادتها عند فتح الشاشة."""
    rows = db.scalars(
        select(AssistantMessage)
        .where(AssistantMessage.user_id == current_user.id)
        .order_by(AssistantMessage.id.desc())
        .limit(limit)
    ).all()
    rows = list(reversed(rows))  # الأقدم -> الأحدث
    return HistoryResponse(
        messages=[
            HistoryMessage(role=r.role, content=r.content, created_at=r.created_at) for r in rows
        ]
    )


@router.delete("/history")
@limiter.limit("10/minute")
def clear_history(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """يمسح كل محادثة المستخدم مع المساعد."""
    result = db.execute(
        delete(AssistantMessage).where(AssistantMessage.user_id == current_user.id)
    )
    db.commit()
    return {"cleared": result.rowcount or 0}
