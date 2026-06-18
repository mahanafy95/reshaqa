"""التحقّق من اشتراكات Google Play من جهة الخادم (مصدر الحقيقة).

يستخدم حساب خدمة (Service Account) لتوليد رمز وصول OAuth (JWT RS256 عبر PyJWT)،
ثم يستعلم purchases.subscriptionsv2 عبر httpx. بدون تبعيات ثقيلة (google-api-client).
يتعطّل بهدوء لو حساب الخدمة غير مضبوط (يُرجع None) فلا يكسر التطبيق.
"""
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import quote

import httpx
import jwt

from ..config import settings

logger = logging.getLogger("reshaqa.billing")

_ANDROIDPUBLISHER = "https://androidpublisher.googleapis.com/androidpublisher/v3"
_SCOPE = "https://www.googleapis.com/auth/androidpublisher"
_DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"

# تخزين مؤقت لرمز الوصول لتفادي توليده مع كل طلب
_token_cache: dict = {"token": None, "exp": 0.0}

# خريطة حالات Google Play إلى حالاتنا الداخلية
_STATE_MAP = {
    "SUBSCRIPTION_STATE_ACTIVE": "active",
    "SUBSCRIPTION_STATE_IN_GRACE_PERIOD": "in_grace_period",
    "SUBSCRIPTION_STATE_CANCELED": "canceled",
    "SUBSCRIPTION_STATE_EXPIRED": "expired",
    "SUBSCRIPTION_STATE_ON_HOLD": "on_hold",
    "SUBSCRIPTION_STATE_PAUSED": "paused",
    "SUBSCRIPTION_STATE_PENDING": "pending",
}


@dataclass
class PlaySubscription:
    status: str
    product_id: str | None
    expiry: datetime | None
    auto_renewing: bool
    acknowledged: bool


def _get_access_token() -> str | None:
    """يولّد (أو يعيد من الكاش) رمز وصول OAuth لحساب الخدمة."""
    now = time.time()
    if _token_cache["token"] and _token_cache["exp"] - 60 > now:
        return _token_cache["token"]
    try:
        sa = json.loads(settings.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON)
    except (json.JSONDecodeError, ValueError):
        logger.error("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON غير صالح")
        return None
    token_uri = sa.get("token_uri") or _DEFAULT_TOKEN_URI
    iat = int(now)
    claims = {
        "iss": sa.get("client_email"),
        "scope": _SCOPE,
        "aud": token_uri,
        "iat": iat,
        "exp": iat + 3600,
    }
    try:
        assertion = jwt.encode(claims, sa["private_key"], algorithm="RS256")
        resp = httpx.post(
            token_uri,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
            timeout=15.0,
        )
        if resp.status_code != 200:
            logger.error("فشل الحصول على رمز Google: %s %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["exp"] = now + float(data.get("expires_in", 3600))
        return _token_cache["token"]
    except Exception:
        logger.exception("تعذّر توليد رمز وصول حساب الخدمة")
        return None


def _parse_expiry(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # صيغة RFC3339 (Z) — نطبّعها لـ ISO
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def verify_purchase(purchase_token: str) -> PlaySubscription | None:
    """يستعلم حالة الاشتراك من Google Play. يُرجع None عند الفشل/عدم الضبط."""
    if not settings.billing_enabled or not purchase_token:
        return None
    token = _get_access_token()
    if token is None:
        return None
    url = (
        f"{_ANDROIDPUBLISHER}/applications/{settings.GOOGLE_PLAY_PACKAGE_NAME}"
        f"/purchases/subscriptionsv2/tokens/{quote(purchase_token, safe='')}"
    )
    try:
        resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15.0)
    except Exception:
        logger.exception("تعذّر الاتصال بـ Google Play")
        return None
    if resp.status_code != 200:
        logger.warning("استعلام Play رجّع %s: %s", resp.status_code, resp.text[:200])
        return None

    data = resp.json()
    state = data.get("subscriptionState", "")
    line_items = data.get("lineItems") or []
    first = line_items[0] if line_items else {}
    expiry = _parse_expiry(first.get("expiryTime"))
    ack = data.get("acknowledgementState") == "ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED"
    return PlaySubscription(
        status=_STATE_MAP.get(state, "unknown"),
        product_id=first.get("productId"),
        expiry=expiry,
        auto_renewing=bool(first.get("autoRenewingPlan")),
        acknowledged=ack,
    )


def acknowledge_purchase(purchase_token: str) -> bool:
    """يؤكّد استلام الاشتراك (مطلوب خلال 3 أيام وإلا يُسترجع تلقائياً)."""
    if not settings.billing_enabled:
        return False
    token = _get_access_token()
    if token is None:
        return False
    url = (
        f"{_ANDROIDPUBLISHER}/applications/{settings.GOOGLE_PLAY_PACKAGE_NAME}"
        f"/purchases/subscriptionsv2/tokens/{quote(purchase_token, safe='')}:acknowledge"
    )
    try:
        resp = httpx.post(url, headers={"Authorization": f"Bearer {token}"}, json={}, timeout=15.0)
        return resp.status_code in (200, 204)
    except Exception:
        logger.exception("تعذّر تأكيد الاشتراك")
        return False


def is_active_now(status: str, expiry: datetime | None) -> bool:
    """هل الاشتراك مفعّل الآن؟ (حالة نشطة + لم تنتهِ فترته)."""
    from ..models.subscription import ACTIVE_STATUSES

    if status not in ACTIVE_STATUSES:
        return False
    if expiry is None:
        return True
    return expiry > datetime.now(timezone.utc)
