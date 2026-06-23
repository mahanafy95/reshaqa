"""راوتر المصادقة — تسجيل، دخول (JWT)، دخول بجوجل، إعادة تعيين كلمة السر بالبريد."""
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.admin import is_user_admin
from ..core.billing import user_is_premium
from ..core.deps import get_current_user
from ..core.ratelimit import limiter
from ..core.security import create_access_token, hash_password, verify_password
from ..database import get_db
from ..models.password_reset import PasswordReset
from ..models.user import User
from ..schemas.auth import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    SetEmailRequest,
    TokenResponse,
    UserOut,
)
from ..services import email_service
from ..services.google_auth import verify_google_id_token

router = APIRouter(prefix="/auth", tags=["المصادقة"])


def _user_out(user: User) -> UserOut:
    data = UserOut.model_validate(user)
    data.has_profile = user.profile is not None
    data.is_admin = is_user_admin(user)
    data.is_premium = user_is_premium(user.subscription)
    return data


def _email_taken(db: Session, email: str, exclude_user_id: int | None = None) -> bool:
    stmt = select(User).where(func.lower(User.email) == email.lower())
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    return db.scalar(stmt) is not None


def _unique_username_from_email(db: Session, email: str) -> str:
    """يولّد اسم مستخدم فريد من الجزء قبل @ في البريد (لحسابات جوجل الجديدة)."""
    base = re.sub(r"[^a-z0-9_]", "", (email.split("@")[0] or "").lower()) or "user"
    base = base[:24]
    if len(base) < 3:
        base = f"user{base}"
    candidate = base
    n = 0
    while db.scalar(select(User).where(func.lower(User.username) == candidate.lower())) is not None:
        n += 1
        suffix = str(secrets.randbelow(10000)) if n > 5 else str(n)
        candidate = f"{base[:24 - len(suffix)]}{suffix}"
    return candidate


def _aware(dt: datetime) -> datetime:
    """يضمن أن التاريخ يحمل منطقة زمنية (SQLite قد يرجّعه بدونها)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("8/hour")
def register(
    request: Request, payload: RegisterRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    # الأسماء المحجوزة للمشرف لا يجوز تسجيلها من العامة (يمنع تصعيد الصلاحية)
    if payload.username.lower() in settings.admin_usernames_set:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="الاسم ده محجوز، اختار اسم تاني.",
        )
    # فحص عدم التكرار (غير حسّاس لحالة الأحرف لتفادي الالتباس)
    exists = db.scalar(
        select(User).where(func.lower(User.username) == payload.username.lower())
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="اسم المستخدم ده موجود بالفعل. جرّب اسم تاني.",
        )
    if payload.email and _email_taken(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="البريد ده مستخدم بحساب تاني.",
        )

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(
    request: Request, payload: LoginRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    user = db.scalar(
        select(User).where(func.lower(User.username) == payload.username.lower())
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="اسم المستخدم أو كلمة السر غير صحيحة.",
        )
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/token", response_model=TokenResponse, include_in_schema=False)
@limiter.limit("10/minute")
def login_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """نقطة دخول متوافقة مع OAuth2 form (تُستخدم في صفحة توثيق Swagger)."""
    user = db.scalar(
        select(User).where(func.lower(User.username) == form_data.username.lower())
    )
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="اسم المستخدم أو كلمة السر غير صحيحة.",
        )
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/google", response_model=TokenResponse)
@limiter.limit("20/minute")
def google_login(
    request: Request, payload: GoogleAuthRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    """دخول/تسجيل بحساب جوجل — يتحقّق من الرمز ويُنشئ الحساب لو جديد (بدون كلمة سر)."""
    if not settings.google_login_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="تسجيل الدخول بجوجل مش مفعّل حالياً.",
        )
    info = verify_google_id_token(payload.id_token)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="تعذّر التحقّق من حساب جوجل. حاول تاني.",
        )

    sub = info["sub"]
    email = info["email"]
    user = db.scalar(select(User).where(User.google_sub == sub))

    if user is None and email and info["email_verified"]:
        # ربط بحساب موجود بنفس البريد (آمن لأن جوجل أكّد ملكية البريد)
        user = db.scalar(select(User).where(func.lower(User.email) == email))
        if user is not None and user.google_sub is None:
            user.google_sub = sub

    if user is None:
        username = _unique_username_from_email(db, email)
        user = User(
            username=username,
            email=email,
            google_sub=sub,
            password_hash=None,
        )
        db.add(user)

    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/email", response_model=UserOut)
@limiter.limit("6/hour")
def set_email(
    request: Request,
    payload: SetEmailRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    """يضيف/يعدّل بريد المستخدم الحالي (مطلوب لإعادة تعيين كلمة السر) — محدود ٦/ساعة ضد العبث."""
    if _email_taken(db, payload.email, exclude_user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="البريد ده مستخدم بحساب تاني.",
        )
    current_user.email = payload.email
    db.commit()
    db.refresh(current_user)
    return _user_out(current_user)


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("5/hour")
def forgot_password(
    request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> MessageResponse:
    """يرسل رمز إعادة تعيين (6 أرقام) للبريد. لا يكشف إن كان البريد مسجّلاً أم لا."""
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email))
    if user is not None:
        # سقف لكل حساب: أقصى عدد رموز في الساعة — يمنع التخمين بتدوير الرموز
        # (دفاع متعمّق مستقل عن تحديد المعدّل بالـ IP).
        hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent = db.scalar(
            select(func.count()).select_from(PasswordReset).where(
                PasswordReset.user_id == user.id, PasswordReset.created_at >= hour_ago
            )
        ) or 0
        if recent >= 5:
            return MessageResponse(
                message="لو البريد ده مسجّل عندنا، هيوصلك رمز إعادة التعيين على إيميلك خلال دقيقة."
            )
        # نُبطل أي رموز سابقة غير مستخدمة لنفس المستخدم
        for old in db.scalars(
            select(PasswordReset).where(
                PasswordReset.user_id == user.id, PasswordReset.used.is_(False)
            )
        ).all():
            old.used = True
        code = f"{secrets.randbelow(1_000_000):06d}"
        pr = PasswordReset(
            user_id=user.id,
            code_hash=hash_password(code),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_TTL_MINUTES),
        )
        db.add(pr)
        db.commit()
        email_service.send_password_reset_code(user.email, code)
    return MessageResponse(
        message="لو البريد ده مسجّل عندنا، هيوصلك رمز إعادة التعيين على إيميلك خلال دقيقة."
    )


@router.post("/reset-password", response_model=TokenResponse)
@limiter.limit("10/hour")
def reset_password(
    request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    """يتحقّق من الرمز ويعيّن كلمة سر جديدة ويسجّل الدخول مباشرة."""
    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="الرمز غير صحيح أو منتهي. اطلب رمز جديد.",
    )
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email))
    if user is None:
        raise invalid

    pr = db.scalar(
        select(PasswordReset)
        .where(PasswordReset.user_id == user.id, PasswordReset.used.is_(False))
        .order_by(PasswordReset.created_at.desc())
    )
    if pr is None or _aware(pr.expires_at) < datetime.now(timezone.utc):
        raise invalid

    # حد المحاولات — يمنع التخمين على الإنترنت
    if pr.attempts >= settings.OTP_MAX_ATTEMPTS:
        pr.used = True
        db.commit()
        raise invalid

    if not verify_password(payload.code, pr.code_hash):
        pr.attempts += 1
        if pr.attempts >= settings.OTP_MAX_ATTEMPTS:
            pr.used = True
        db.commit()
        raise invalid

    user.password_hash = hash_password(payload.new_password)
    pr.used = True
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/config")
def auth_config() -> dict:
    """إعدادات المصادقة العامة — تقرأها الواجهات لتفعيل الأزرار بدون إعادة بناء.

    بكده زر "الدخول بجوجل" واسترجاع كلمة السر يتفعّلوا بمجرّد ضبط متغيّرات
    البيئة في الخادم، من غير ما نعيد بناء الويب أو الموبايل.
    """
    ids = sorted(settings.google_client_ids_set)
    return {
        "google_login_enabled": settings.google_login_enabled,
        "google_client_id": ids[0] if ids else "",
        "email_reset_enabled": settings.email_enabled,
    }


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(current_user)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    """حذف حساب المستخدم الحالي وكل بياناته نهائياً (مطلوب لسياسة Google Play)."""
    db.delete(current_user)
    db.commit()
