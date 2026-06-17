"""راوتر المصادقة — تسجيل، دخول (JWT)، وبيانات المستخدم الحالي."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.admin import is_user_admin
from ..core.deps import get_current_user
from ..core.ratelimit import limiter
from ..core.security import create_access_token, hash_password, verify_password
from ..database import get_db
from ..models.user import User
from ..schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["المصادقة"])


def _user_out(user: User) -> UserOut:
    data = UserOut.model_validate(user)
    data.has_profile = user.profile is not None
    data.is_admin = is_user_admin(user)
    return data


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("8/hour")
def register(
    request: Request, payload: RegisterRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    # فحص عدم التكرار (غير حسّاس لحالة الأحرف لتفادي الالتباس)
    exists = db.scalar(
        select(User).where(func.lower(User.username) == payload.username.lower())
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="اسم المستخدم ده موجود بالفعل. جرّب اسم تاني.",
        )

    user = User(username=payload.username, password_hash=hash_password(payload.password))
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


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(current_user)
