"""رموز إعادة تعيين كلمة السر (OTP) المُرسلة بالبريد — مؤقتة وقابلة للانتهاء.

أمان: الرمز نفسه (6 أرقام) لا يُخزَّن أبداً — نخزّن تجزئته (bcrypt) فقط، وله
صلاحية قصيرة وعدّاد محاولات. الرمز الخام يوصل بريد المستخدم فقط، فلا يقدر أحد
حتى مدير الخادم استرجاعه من قاعدة البيانات.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    used: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="password_resets")  # noqa: F821
