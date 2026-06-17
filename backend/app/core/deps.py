"""تبعيات FastAPI المشتركة — استخراج المستخدم الحالي من رمز JWT.

كل الـ endpoints المحمية تعتمد على get_current_user، وكل استعلام يُفلتر بـ user_id
لضمان عزل بيانات كل مستخدم تماماً.
"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="بيانات الدخول غير صالحة أو منتهية. سجّل الدخول من جديد.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise _CREDENTIALS_EXC
        uid = int(user_id)
    except (jwt.PyJWTError, ValueError, TypeError):
        raise _CREDENTIALS_EXC

    user = db.get(User, uid)
    if user is None:
        raise _CREDENTIALS_EXC
    return user
