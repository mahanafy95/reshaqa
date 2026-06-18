"""التحقّق من رمز هوية جوجل (ID token) — مجاني تماماً وبدون مفتاح API.

نستخدم نقطة google tokeninfo التي تتحقّق من توقيع الرمز وانتهائه عند جوجل نفسها،
ثم نتأكّد محلياً أن الجمهور (aud) أحد معرّفات العميل المسجّلة عندنا وأن المُصدِر جوجل.
لا تبعيات جديدة (httpx موجود أصلاً) ولا أي تكلفة.
"""
import logging

import httpx

from ..config import settings

logger = logging.getLogger("reshaqa.google")

_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
_VALID_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


def verify_google_id_token(id_token: str) -> dict | None:
    """يتحقّق من صحة رمز جوجل ويُرجع {email, sub, name, email_verified} أو None عند الفشل."""
    token = (id_token or "").strip()
    if not token:
        return None
    try:
        resp = httpx.get(_TOKENINFO_URL, params={"id_token": token}, timeout=10.0)
    except Exception:  # شبكة/مهلة — نفشل بهدوء (المستخدم يحاول تاني)
        logger.exception("تعذّر الاتصال بخدمة تحقّق جوجل")
        return None

    if resp.status_code != 200:
        return None

    try:
        data = resp.json()
    except ValueError:
        return None

    # التحقّق من الجمهور (aud): لازم يطابق أحد معرّفات العميل المسجّلة عندنا
    allowed = settings.google_client_ids_set
    if not allowed:  # غير مفعّل — لا نقبل أي رمز
        return None
    if data.get("aud") not in allowed:
        logger.warning("رمز جوجل بجمهور غير مسموح: %s", data.get("aud"))
        return None
    if data.get("iss") not in _VALID_ISSUERS:
        return None

    email = (data.get("email") or "").strip().lower()
    sub = data.get("sub")
    if not email or not sub:
        return None

    return {
        "email": email,
        "sub": str(sub),
        "name": (data.get("name") or email.split("@")[0]),
        "email_verified": str(data.get("email_verified", "false")).lower() == "true",
    }
