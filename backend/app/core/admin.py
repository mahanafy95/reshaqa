"""صلاحيات الإشراف (سوبر أدمن).

الفحص الحيّ يعتمد على عمود is_admin في قاعدة البيانات فقط — أمان.
أسماء ADMIN_USERNAMES تُستخدم كـ"إقلاع لمرة واحدة" عند بدء التطبيق (ترقّي الحسابات
الموجودة فعلاً)، ولا تُمنح الصلاحية أبداً لمجرد تطابق الاسم وقت الطلب (يمنع أن يسجّل
أي شخص بالاسم المحجوز ويصير مشرفاً).
"""
from fastapi import Depends, HTTPException, status

from ..models.user import User
from .deps import get_current_user


def is_user_admin(user: User) -> bool:
    return bool(user.is_admin)


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """تبعية تتطلّب صلاحية الإشراف — ترفع 403 لغير المشرفين."""
    if not is_user_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذه الصفحة للمشرفين فقط.",
        )
    return current_user
