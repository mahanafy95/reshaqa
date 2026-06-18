"""نموذج المستخدم — مصادقة بـ username/كلمة سر، أو بريد + دخول جوجل (اختياري)."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    # البريد اختياري — مطلوب فقط لإعادة تعيين كلمة السر أو الربط بحساب جوجل
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    # معرّف جوجل الثابت (sub) لمستخدمي تسجيل الدخول بجوجل
    google_sub: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    # قابل لأن يكون فارغاً لحسابات جوجل التي لا تملك كلمة سر
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    profile: Mapped["Profile"] = relationship(  # noqa: F821
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    password_resets: Mapped[list["PasswordReset"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    subscription: Mapped["Subscription"] = relationship(  # noqa: F821
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
