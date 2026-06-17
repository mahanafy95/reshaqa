"""يولّد PDF تجريبي للتحقق البصري من العربية (تقرير مفصّل)."""
import sys
from datetime import date, timedelta

from app.services import pdf_report
from app.services.reports import (
    OVER, UNDER, WITHIN, NO_DATA, DayAdherence, MonthlyReport, WeeklyReport,
)

start = date(2026, 3, 7)


def _day(off, cal, p, c, f, status):
    return DayAdherence(start + timedelta(days=off), 2200, cal, p, c, f, status)


days = [
    _day(0, 2150, 150, 200, 60, WITHIN),
    _day(1, 2600, 120, 280, 90, OVER),
    _day(2, 1500, 90, 150, 40, UNDER),
    _day(3, 2180, 160, 190, 58, WITHIN),
    _day(4, 2250, 155, 210, 62, WITHIN),
    _day(5, 0, 0, 0, 0, NO_DATA),
    _day(6, 2100, 145, 195, 55, WITHIN),
]
weekly = WeeklyReport(
    start=start, end=start + timedelta(days=6), days=days, adherent_days=4, logged_days=6,
    days_within=4, days_over=1, days_under=1,
    avg_eaten=2130, avg_target=2200, avg_protein=137, avg_carbs=204, avg_fat=61,
    best_day=start + timedelta(days=3), water_avg_ml=2100, activity_total_min=150,
    activity_total_calories=820, activity_sessions=4,
    weight_change_kg=-0.6, weight_slope_kg_week=-0.6,
    summary_ar="أسبوع كويس، التزمت 4 أيام من 7. كل أسبوع بنتحسّن 🙂",
)
monthly = MonthlyReport(
    year=2026, month=3, start=date(2026, 3, 1), end=date(2026, 3, 31), weeks=[weekly, weekly],
    total_adherent_days=14, total_logged_days=26, avg_eaten=2120,
    avg_protein=135, avg_carbs=200, avg_fat=60, water_avg_ml=2050,
    activity_total_min=600, activity_total_calories=3200,
    weight_change_kg=-2.3,
    summary_ar="شهر فيه تقدّم حقيقي — نزلت 2.3 كجم تقريباً. شغل جميل!",
)

with open(sys.argv[1], "wb") as f:
    f.write(pdf_report.weekly_pdf(weekly))
with open(sys.argv[2], "wb") as f:
    f.write(pdf_report.monthly_pdf(monthly))
print("PDFs written")
