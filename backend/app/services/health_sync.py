"""خدمة مزامنة الصحة — هواوي (أولوية) ثم Health Connect ثم اليدوي.

استراتيجية عملية:
- المسار الأساسي الشغّال: الموبايل يقرأ البيانات على الجهاز (Huawei Health Kit SDK
  أو Android Health Connect) ويدفعها عبر POST /health/sync. الباك إند يخزّنها كنشاط+نوم.
- مسار OAuth هواوي من جهة الخادم: مُجهّز هيكلياً ويعمل عند تهيئة الـ credentials،
  وإلا يرجّع None (غير مُهيّأ) مع توجيه واضح.

السعرات المحروقة تُخزَّن للعرض كنشاط فقط ولا تُخصم من ميزانية الأكل أبداً.
"""
from dataclasses import dataclass
from datetime import date as date_type
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models.enums import ActivitySource
from ..models.tracking import ActivityLog, MoodLog

# نقاط هواوي (راجع توثيق Huawei Health Kit الحالي وقت التنفيذ — قد تتغيّر)
HUAWEI_AUTH_URL = "https://oauth-login.cloud.huawei.com/oauth2/v3/authorize"
HUAWEI_TOKEN_URL = "https://oauth-login.cloud.huawei.com/oauth2/v3/token"
# scopes شائعة لبيانات الخطوات/النشاط/النوم (تأكّد منها وقت التنفيذ)
HUAWEI_DEFAULT_SCOPES = [
    "openid",
    "https://www.huawei.com/healthkit/step.read",
    "https://www.huawei.com/healthkit/activity.read",
    "https://www.huawei.com/healthkit/sleep.read",
]


def huawei_configured() -> bool:
    return bool(settings.HUAWEI_HEALTH_CLIENT_ID and settings.HUAWEI_HEALTH_REDIRECT_URI)


def build_huawei_authorize_url(state: str) -> str | None:
    """يبني رابط موافقة هواوي. None لو غير مُهيّأ."""
    if not huawei_configured():
        return None
    params = {
        "response_type": "code",
        "client_id": settings.HUAWEI_HEALTH_CLIENT_ID,
        "redirect_uri": settings.HUAWEI_HEALTH_REDIRECT_URI,
        "scope": " ".join(HUAWEI_DEFAULT_SCOPES),
        "state": state,
        "access_type": "offline",
    }
    return f"{HUAWEI_AUTH_URL}?{urlencode(params)}"


def exchange_huawei_code(code: str) -> dict | None:
    """يبادل كود التفويض بتوكن. None لو غير مُهيّأ أو فشل الاتصال."""
    if not huawei_configured() or not settings.HUAWEI_HEALTH_CLIENT_SECRET:
        return None
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.HUAWEI_HEALTH_CLIENT_ID,
        "client_secret": settings.HUAWEI_HEALTH_CLIENT_SECRET,
        "redirect_uri": settings.HUAWEI_HEALTH_REDIRECT_URI,
    }
    try:
        resp = httpx.post(HUAWEI_TOKEN_URL, data=data, timeout=10.0)
        if resp.status_code != 200:
            return None
        return resp.json()
    except (httpx.HTTPError, ValueError):
        return None


@dataclass
class SyncResult:
    date: date_type
    saved_activity: bool
    saved_sleep: bool
    steps: int | None
    calories_burned: float | None
    note_ar: str


def apply_health_data(
    db: Session,
    user_id: int,
    *,
    day: date_type,
    source: ActivitySource,
    steps: int | None = None,
    active_minutes: int | None = None,
    calories_burned: float | None = None,
    sleep_hours: float | None = None,
    activity_type_ar: str | None = None,
) -> SyncResult:
    """يخزّن بيانات الصحة المسحوبة: نشاط (خطوات/دقائق/سعرات) + نوم.

    لا يُحسب أي شيء على ميزانية الأكل.
    """
    saved_activity = False
    if steps or active_minutes or calories_burned:
        type_ar = activity_type_ar or ("نشاط ومشي" if steps else "نشاط")
        db.add(
            ActivityLog(
                user_id=user_id,
                date=day,
                type_ar=type_ar,
                duration_min=active_minutes or 0,
                calories_burned=calories_burned,
                steps=steps,
                source=source,
            )
        )
        saved_activity = True

    saved_sleep = False
    if sleep_hours is not None:
        mood = db.scalar(
            select(MoodLog).where(MoodLog.user_id == user_id, MoodLog.date == day)
        )
        if mood is None:
            mood = MoodLog(user_id=user_id, date=day)
            db.add(mood)
        mood.sleep_hours = sleep_hours
        saved_sleep = True

    db.commit()
    return SyncResult(
        date=day,
        saved_activity=saved_activity,
        saved_sleep=saved_sleep,
        steps=steps,
        calories_burned=calories_burned,
        note_ar="اتسجّل كنشاط ونوم. السعرات المحروقة للعرض فقط وما اتخصمتش من ميزانية الأكل.",
    )
