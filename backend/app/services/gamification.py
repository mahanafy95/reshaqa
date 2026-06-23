"""تحفيز المستخدم — سلسلة الأيام المتتالية (Streaks) والإنجازات.

كله مُشتقّ من سجلّات الأكل الموجودة (مفيش جداول جديدة): بنحسب الأيام اللي فيها
تسجيل أكل ونطلّع السلسلة الحالية والأطول وإجمالي الأيام + شارات إنجاز.
"""
from datetime import date as date_type
from datetime import timedelta

from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from ..models.food import FoodLogged


def _logged_dates(db: Session, user_id: int) -> list[date_type]:
    """كل الأيام (تواريخ مميّزة) اللي المستخدم سجّل فيها أكل، تصاعدياً."""
    rows = db.scalars(
        select(distinct(FoodLogged.date))
        .where(FoodLogged.user_id == user_id)
        .order_by(FoodLogged.date)
    ).all()
    return [d for d in rows if d is not None]


def _current_streak(dates_set: set[date_type], today: date_type) -> int:
    """عدد الأيام المتتالية المنتهية النهاردة (أو إمبارح لو لسه ماسجّلش النهاردة)."""
    if not dates_set:
        return 0
    # نبدأ من النهاردة لو فيها تسجيل، وإلا من إمبارح (مانكسرش السلسلة قبل ما اليوم يخلص)
    if today in dates_set:
        cursor = today
    elif (today - timedelta(days=1)) in dates_set:
        cursor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    while cursor in dates_set:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _longest_streak(dates: list[date_type]) -> int:
    """أطول سلسلة أيام متتالية في التاريخ كله."""
    if not dates:
        return 0
    dates = sorted(set(dates))  # دفاعيًا: منعتمدش على ترتيب المُدخَل
    longest = run = 1
    for prev, cur in zip(dates, dates[1:]):
        if cur - prev == timedelta(days=1):
            run += 1
            longest = max(longest, run)
        elif cur != prev:  # فجوة (التواريخ مميّزة فالمساواة مش متوقّعة)
            run = 1
    return longest


# الإنجازات المشتقّة — (المفتاح، النص، الرمز، شرط الفتح)
_ACHIEVEMENT_DEFS = [
    ("first_log", "أول تسجيل", "🎯", lambda s: s["total_days_logged"] >= 1),
    ("streak_3", "٣ أيام متتالية", "🔥", lambda s: s["longest_streak"] >= 3),
    ("streak_7", "أسبوع كامل", "⭐", lambda s: s["longest_streak"] >= 7),
    ("streak_30", "شهر كامل", "🏆", lambda s: s["longest_streak"] >= 30),
    ("days_30", "٣٠ يوم تسجيل", "📅", lambda s: s["total_days_logged"] >= 30),
    ("days_100", "١٠٠ يوم تسجيل", "💎", lambda s: s["total_days_logged"] >= 100),
]


def compute(db: Session, user_id: int, today: date_type | None = None) -> dict:
    """يرجّع تحفيز المستخدم: السلسلة الحالية/الأطول + إجمالي الأيام + الإنجازات."""
    today = today or date_type.today()
    dates = _logged_dates(db, user_id)
    dates_set = set(dates)
    stats = {
        "current_streak": _current_streak(dates_set, today),
        "longest_streak": _longest_streak(dates),
        "total_days_logged": len(dates_set),
    }
    achievements = [
        {"key": key, "title_ar": title, "emoji": emoji, "unlocked": cond(stats)}
        for key, title, emoji, cond in _ACHIEVEMENT_DEFS
    ]
    return {**stats, "achievements": achievements}
