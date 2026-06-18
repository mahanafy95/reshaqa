"""راوتر لوحة الإشراف (سوبر أدمن) — إدارة المستخدمين وبياناتهم وكلمات سرهم.

كل المسارات محميّة بـ get_admin_user (صلاحية إشراف إلزامية).
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.admin import get_admin_user, is_user_admin
from ..core.billing import user_is_premium
from ..core.security import hash_password
from ..database import get_db
from ..models.food import FoodLogged
from ..models.profile import Profile
from ..models.subscription import Subscription
from ..models.tracking import WeightLog
from ..models.user import User
from ..schemas.admin import (
    AdminActionResult,
    AdminCreateUser,
    AdminFoodOut,
    AdminProfileOut,
    AdminUserDetail,
    AdminUserSummary,
    AdminWeightOut,
    BulkDeleteRequest,
    BulkDeleteResult,
    ChangeUsernameRequest,
    GrantPremiumRequest,
    ResetPasswordRequest,
    SetAdminRequest,
)
from ..services import targets_service

router = APIRouter(prefix="/admin", tags=["الإشراف"])


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستخدم غير موجود.")
    return user


def _safe_target(db: Session, user: User, profile: Profile | None):
    """يحسب (هدف السعرات, BMI, البرنامج, حالة الوزن) إن أمكن، وإلا قيم None."""
    if profile is None:
        return None, None, None, None
    try:
        result, _cw, _pl = targets_service.compute_for_user(db, user.id, profile)
        return result.target_calories, result.bmi, str(result.mode.value), result.weight_status
    except Exception:
        return None, None, None, None


@router.get("/users", response_model=list[AdminUserSummary])
def list_users(
    q: str = Query("", description="بحث باسم المستخدم"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    stmt = select(User)
    if q.strip():
        stmt = stmt.where(User.username.ilike(f"%{q.strip()}%"))
    stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    users = db.scalars(stmt).all()

    out: list[AdminUserSummary] = []
    for u in users:
        profile = db.scalar(select(Profile).where(Profile.user_id == u.id))
        foods_count = db.scalar(
            select(func.count()).select_from(FoodLogged).where(FoodLogged.user_id == u.id)
        ) or 0
        weights_count = db.scalar(
            select(func.count()).select_from(WeightLog).where(WeightLog.user_id == u.id)
        ) or 0
        last_food_date = db.scalar(
            select(func.max(FoodLogged.date)).where(FoodLogged.user_id == u.id)
        )
        latest_weight = db.scalar(
            select(WeightLog.weight_kg)
            .where(WeightLog.user_id == u.id)
            .order_by(WeightLog.date.desc())
            .limit(1)
        )
        target_cal, _bmi, mode, wstatus = _safe_target(db, u, profile)
        sub = db.scalar(select(Subscription).where(Subscription.user_id == u.id))
        out.append(
            AdminUserSummary(
                id=u.id,
                username=u.username,
                is_admin=is_user_admin(u),
                created_at=u.created_at,
                has_profile=profile is not None,
                current_weight_kg=latest_weight if latest_weight is not None else (
                    profile.weight_kg if profile else None
                ),
                goal_weight_kg=profile.goal_weight_kg if profile else None,
                target_calories=target_cal,
                mode=mode,
                weight_status=wstatus,
                is_premium=user_is_premium(sub),
                foods_count=foods_count,
                weights_count=weights_count,
                last_food_date=last_food_date,
            )
        )
    return out


@router.post("/users", response_model=AdminUserSummary, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminCreateUser, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """إضافة مستخدم جديد باسم وكلمة سر (مع إمكانية جعله مشرفاً)."""
    exists = db.scalar(
        select(User).where(func.lower(User.username) == payload.username.lower())
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="اسم المستخدم ده موجود بالفعل. جرّب اسم تاني.",
        )
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_admin=payload.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return AdminUserSummary(
        id=user.id,
        username=user.username,
        is_admin=is_user_admin(user),
        created_at=user.created_at,
        has_profile=False,
        foods_count=0,
        weights_count=0,
    )


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def user_detail(
    user_id: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    user = _get_user_or_404(db, user_id)
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    target_cal, bmi, mode, wstatus = _safe_target(db, user, profile)

    foods_count = db.scalar(
        select(func.count()).select_from(FoodLogged).where(FoodLogged.user_id == user.id)
    ) or 0
    weights_count = db.scalar(
        select(func.count()).select_from(WeightLog).where(WeightLog.user_id == user.id)
    ) or 0

    recent_foods = db.scalars(
        select(FoodLogged)
        .where(FoodLogged.user_id == user.id)
        .order_by(FoodLogged.date.desc(), FoodLogged.created_at.desc())
        .limit(10)
    ).all()
    recent_weights = db.scalars(
        select(WeightLog)
        .where(WeightLog.user_id == user.id)
        .order_by(WeightLog.date.desc())
        .limit(10)
    ).all()

    prof_out = None
    if profile is not None:
        prof_out = AdminProfileOut(
            age=profile.age,
            sex=str(getattr(profile.sex, "value", profile.sex)),
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            activity_level=str(getattr(profile.activity_level, "value", profile.activity_level)),
            goal_weight_kg=profile.goal_weight_kg,
            goal_rate=profile.goal_rate,
        )

    return AdminUserDetail(
        id=user.id,
        username=user.username,
        is_admin=is_user_admin(user),
        created_at=user.created_at,
        profile=prof_out,
        target_calories=target_cal,
        bmi=bmi,
        mode=mode,
        weight_status=wstatus,
        is_premium=user_is_premium(
            db.scalar(select(Subscription).where(Subscription.user_id == user.id))
        ),
        foods_count=foods_count,
        weights_count=weights_count,
        recent_foods=[
            AdminFoodOut(
                date=f.date,
                meal=str(getattr(f.meal, "value", f.meal)),
                name_ar=f.name_ar,
                amount=f.amount,
                calories=f.calories,
            )
            for f in recent_foods
        ],
        recent_weights=[
            AdminWeightOut(date=w.date, weight_kg=w.weight_kg) for w in recent_weights
        ],
    )


@router.post("/users/{user_id}/reset-password", response_model=AdminActionResult)
def reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(db, user_id)
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return AdminActionResult(message=f"تم تعيين كلمة سر جديدة للمستخدم {user.username}.")


@router.post("/users/{user_id}/username", response_model=AdminActionResult)
def change_username(
    user_id: int,
    payload: ChangeUsernameRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """تغيير اسم مستخدم (مع فحص عدم التكرار)."""
    user = _get_user_or_404(db, user_id)
    if payload.new_username.lower() in settings.admin_usernames_set:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="الاسم ده محجوز للمشرف.",
        )
    clash = db.scalar(
        select(User).where(
            func.lower(User.username) == payload.new_username.lower(), User.id != user_id
        )
    )
    if clash is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="اسم المستخدم ده موجود بالفعل. جرّب اسم تاني.",
        )
    old = user.username
    user.username = payload.new_username
    db.commit()
    return AdminActionResult(message=f"تم تغيير الاسم من {old} إلى {payload.new_username}.")


@router.post("/users/{user_id}/admin", response_model=AdminActionResult)
def set_admin(
    user_id: int,
    payload: SetAdminRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(db, user_id)
    # منع المشرف من سحب صلاحيته عن نفسه (تفادي قفل الحساب)
    if user.id == admin.id and not payload.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ماينفعش تسحب صلاحية الإشراف من نفسك.",
        )
    user.is_admin = payload.is_admin
    db.commit()
    verb = "تم منح" if payload.is_admin else "تم سحب"
    return AdminActionResult(message=f"{verb} صلاحية الإشراف للمستخدم {user.username}.")


@router.post("/users/{user_id}/premium", response_model=AdminActionResult)
def set_premium(
    user_id: int,
    payload: GrantPremiumRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """منح/سحب Premium يدوياً (مجاناً، بدون دفع) — للأصدقاء أو التجارب أو الهدايا.

    التفعيل ده مستقل تماماً عن Google Play (platform=manual، بلا عمولة).
    """
    user = _get_user_or_404(db, user_id)
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user.id))
    if payload.grant:
        if sub is None:
            sub = Subscription(user_id=user.id)
            db.add(sub)
        sub.platform = "manual"
        sub.product_id = "comp"
        sub.status = "active"
        sub.auto_renewing = False
        sub.current_period_end = (
            datetime.now(timezone.utc) + timedelta(days=payload.days) if payload.days else None
        )
        dur = f"لمدة {payload.days} يوم" if payload.days else "بدون انتهاء"
        msg = f"تم منح Premium للمستخدم {user.username} ({dur})."
    else:
        if sub is not None:
            sub.status = "expired"
            sub.current_period_end = datetime.now(timezone.utc)
        msg = f"تم سحب Premium من المستخدم {user.username}."
    db.commit()
    return AdminActionResult(message=msg)


@router.delete("/users/{user_id}", response_model=AdminActionResult)
def delete_user(
    user_id: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    user = _get_user_or_404(db, user_id)
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ماينفعش تحذف حسابك أنت.",
        )
    username = user.username
    db.delete(user)
    db.commit()
    return AdminActionResult(message=f"تم حذف المستخدم {username} وكل بياناته.")


@router.post("/users/bulk-delete", response_model=BulkDeleteResult)
def bulk_delete_users(
    payload: BulkDeleteRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """حذف مجموعة مستخدمين دفعة واحدة (لتنظيف الحسابات التجريبية).

    أمان: يتخطّى أي مشرف ويتخطّى حساب الطالب نفسه — لا يُحذفان أبداً.
    """
    deleted: list[str] = []
    skipped = 0
    for uid in set(payload.ids):
        user = db.get(User, uid)
        if user is None or user.id == admin.id or is_user_admin(user):
            skipped += 1
            continue
        deleted.append(user.username)
        db.delete(user)
    db.commit()
    return BulkDeleteResult(deleted=len(deleted), skipped=skipped, deleted_usernames=deleted[:50])
