"""يولّد PDF تجريبي للتحقق البصري من العربية."""
import sys
from datetime import date, timedelta

from app.services import pdf_report
from app.services.reports import (
    OVER, UNDER, WITHIN, NO_DATA, DayAdherence, MonthlyReport, WeeklyReport,
)

start = date(2026, 3, 7)
days = [
    DayAdherence(start + timedelta(days=0), 2200, 2150, WITHIN),
    DayAdherence(start + timedelta(days=1), 2200, 2600, OVER),
    DayAdherence(start + timedelta(days=2), 2200, 1500, UNDER),
    DayAdherence(start + timedelta(days=3), 2200, 2180, WITHIN),
    DayAdherence(start + timedelta(days=4), 2200, 2250, WITHIN),
    DayAdherence(start + timedelta(days=5), 2200, 0, NO_DATA),
    DayAdherence(start + timedelta(days=6), 2200, 2100, WITHIN),
]
weekly = WeeklyReport(
    start=start, end=start + timedelta(days=6), days=days, adherent_days=4, logged_days=6,
    avg_eaten=2130, avg_target=2200, weight_change_kg=-0.6, weight_slope_kg_week=-0.6,
    summary_ar="أسبوع كويس، التزمت 4 أيام من 7. كل أسبوع بنتحسّن 🙂",
)
monthly = MonthlyReport(
    year=2026, month=3, start=date(2026, 3, 1), end=date(2026, 3, 31), weeks=[weekly, weekly],
    total_adherent_days=14, total_logged_days=26, avg_eaten=2120, weight_change_kg=-2.3,
    summary_ar="شهر فيه تقدّم حقيقي — نزلت 2.3 كجم تقريباً. شغل جميل!",
)

with open(sys.argv[1], "wb") as f:
    f.write(pdf_report.weekly_pdf(weekly))
with open(sys.argv[2], "wb") as f:
    f.write(pdf_report.monthly_pdf(monthly))
print("PDFs written")
