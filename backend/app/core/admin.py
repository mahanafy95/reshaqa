"""صلاحيات الإشراف (سوبر أدمن).

مستخدم يُعدّ مشرفاً إذا كان عموده is_admin=True، أو كان اسمه ضمن ADMIN_USERNAMES
في الإعدادات (طريقة الإقلاع: تمنح المالك صلاحية الإشراف بدون تعديل قاعدة البيانات يدوياً).
"""
from fastapi import Depends, HTTPException, status

from ..config import settings
from ..models.user import User
from .deps import get_current_user


def is_user_admin(user: User) -> bool:
    return bool(user.is_admin) or user.username.lower() in settings.admin_usernames_set


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """تبعية تتطلّب صلاحية الإشراف — ترفع 403 لغير المشرفين."""
    if not is_user_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذه الصفحة للمشرفين فقط.",
        )
    return current_user
