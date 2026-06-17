"""أدوات تحقّق مشتركة للسكيمات."""
from datetime import date, timedelta

_MIN_DATE = date(2000, 1, 1)


def validate_log_date(d: date | None) -> date | None:
    """يرفض التواريخ المستقبلية غير المنطقية والقديمة جداً.

    يُسمح بفارق يوم واحد لمراعاة فروق المنطقة الزمنية (المستخدم قد يكون متقدّماً عن UTC).
    """
    if d is None:
        return d
    today = date.today()
    if d > today + timedelta(days=1):
        raise ValueError("التاريخ في المستقبل وغير مسموح.")
    if d < _MIN_DATE:
        raise ValueError("التاريخ قديم جداً وغير صالح.")
    return d
