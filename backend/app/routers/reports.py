"""راوتر التقارير — أسبوعي/شهري (JSON) + تصدير PDF قابل للمشاركة."""
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.billing import require_premium
from ..database import get_db
from ..models.profile import Profile
from ..models.user import User
from ..schemas.reports import MonthlyReportOut, WeeklyReportOut
from ..services import pdf_report, reports

router = APIRouter(prefix="/reports", tags=["التقارير"])


def _require_profile(db: Session, user_id: int) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="أكمل ملفك الشخصي الأول.")
    return profile


def _default_month(year: int | None, month: int | None) -> tuple[int, int]:
    today = date_type.today()
    return (year or today.year), (month or today.month)


@router.get("/weekly", response_model=WeeklyReportOut)
def weekly_report(
    week_of: date_type | None = Query(None, description="أي يوم داخل الأسبوع (افتراضياً النهاردة)"),
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    profile = _require_profile(db, current_user.id)
    report = reports.build_weekly(db, current_user.id, profile, week_of or date_type.today())
    return WeeklyReportOut.model_validate(report)


@router.get("/monthly", response_model=MonthlyReportOut)
def monthly_report(
    year: int | None = Query(None, ge=2020, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    profile = _require_profile(db, current_user.id)
    y, m = _default_month(year, month)
    report = reports.build_monthly(db, current_user.id, profile, y, m)
    return MonthlyReportOut.model_validate(report)


@router.get("/weekly.pdf")
def weekly_report_pdf(
    week_of: date_type | None = Query(None),
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    profile = _require_profile(db, current_user.id)
    report = reports.build_weekly(db, current_user.id, profile, week_of or date_type.today())
    pdf = pdf_report.weekly_pdf(report)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="weekly_{report.start}.pdf"'},
    )


@router.get("/monthly.pdf")
def monthly_report_pdf(
    year: int | None = Query(None, ge=2020, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    profile = _require_profile(db, current_user.id)
    y, m = _default_month(year, month)
    report = reports.build_monthly(db, current_user.id, profile, y, m)
    pdf = pdf_report.monthly_pdf(report)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="monthly_{y}_{m:02d}.pdf"'},
    )
