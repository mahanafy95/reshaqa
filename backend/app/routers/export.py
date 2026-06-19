"""تصدير بيانات المستخدم — CSV لكل سجلّاته (شفافية وملكية البيانات، مهم للبيع/الخصوصية)."""
import csv
import io
from datetime import date as date_type

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..core.ratelimit import limiter
from ..database import get_db
from ..models.food import FoodLogged
from ..models.tracking import ActivityLog, WaistLog, WaterLog, WeightLog
from ..models.user import User

router = APIRouter(prefix="/export", tags=["تصدير البيانات"])


def _w(writer, *row) -> None:
    writer.writerow([("" if v is None else v) for v in row])


def _build_csv(db: Session, user_id: int) -> str:
    buf = io.StringIO()
    buf.write("﻿")  # BOM عشان Excel يقرأ العربي صح
    w = csv.writer(buf)

    _w(w, "رشاقة — تصدير البيانات")
    _w(w)
    # ---- الأكل ----
    _w(w, "الأكل المسجّل")
    _w(w, "التاريخ", "الوجبة", "الصنف", "الكمية (جم)", "سعرات", "بروتين", "كارب", "دهون", "المصدر")
    foods = db.scalars(
        select(FoodLogged).where(FoodLogged.user_id == user_id).order_by(FoodLogged.date, FoodLogged.id)
    ).all()
    for f in foods:
        meal = f.meal.value if hasattr(f.meal, "value") else f.meal
        src = f.source.value if hasattr(f.source, "value") else f.source
        _w(w, f.date, meal, f.name_ar, round(f.amount, 1), round(f.calories), round(f.protein, 1),
           round(f.carbs, 1), round(f.fat, 1), src)
    _w(w)
    # ---- الوزن ----
    _w(w, "الوزن")
    _w(w, "التاريخ", "الوزن (كجم)")
    for r in db.scalars(select(WeightLog).where(WeightLog.user_id == user_id).order_by(WeightLog.date)).all():
        _w(w, r.date, round(r.weight_kg, 1))
    _w(w)
    # ---- محيط الخصر ----
    _w(w, "محيط الخصر")
    _w(w, "التاريخ", "الخصر (سم)")
    for r in db.scalars(select(WaistLog).where(WaistLog.user_id == user_id).order_by(WaistLog.date)).all():
        _w(w, r.date, round(r.waist_cm, 1))
    _w(w)
    # ---- المياه ----
    _w(w, "المياه")
    _w(w, "التاريخ", "الكمية (مل)")
    for r in db.scalars(select(WaterLog).where(WaterLog.user_id == user_id).order_by(WaterLog.date)).all():
        _w(w, r.date, round(r.ml))
    _w(w)
    # ---- النشاط ----
    _w(w, "النشاط")
    _w(w, "التاريخ", "النوع", "الدقائق", "سعرات محروقة", "خطوات")
    for r in db.scalars(select(ActivityLog).where(ActivityLog.user_id == user_id).order_by(ActivityLog.date)).all():
        _w(w, r.date, r.type_ar, r.duration_min, round(r.calories_burned or 0), r.steps or 0)

    return buf.getvalue()


@router.get("")
@limiter.limit("5/minute")
def export_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """يصدّر كل بيانات المستخدم كملف CSV واحد (أكل/وزن/خصر/مياه/نشاط)."""
    content = _build_csv(db, current_user.id)
    fname = f"reshaqa_export_{date_type.today().isoformat()}.csv"
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
