"""الأمان — تجزئة كلمات السر (bcrypt) وإصدار/فحص رموز JWT."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from ..config import settings

# bcrypt يقبل 72 بايت كحد أقصى — نقصّ بأمان لتفادي استثناء على كلمات السر الطويلة جداً.
_BCRYPT_MAX_BYTES = 72


def _to_bcrypt_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """تُرجع تجزئة bcrypt كنص قابل للتخزين."""
    return bcrypt.hashpw(_to_bcrypt_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    """تتحقّق من مطابقة كلمة السر للتجزئة المخزّنة.

    تُرجع False بأمان لو ما فيش تجزئة مخزّنة (حساب جوجل بدون كلمة سر) — فلا
    يقدر أحد يسجّل دخول بكلمة سر على حساب جوجل-فقط.
    """
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    """تُصدر رمز JWT للمستخدم (subject = user id)."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """تفكّ الرمز وتُرجع الحمولة؛ ترفع jwt.PyJWTError عند الفشل."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
