"""توليد تقارير PDF عربية (RTL) — قابلة للمشاركة مع الطبيب/أخصائي التغذية.

يستخدم arabic-reshaper + python-bidi لتشكيل العربية بشكل صحيح، وخط Amiri.
"""
import io
import re
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .reports import OVER, UNDER, WITHIN, MonthlyReport, WeeklyReport

_FONT_PATH = Path(__file__).parent.parent / "assets" / "fonts" / "Amiri-Regular.ttf"
_FONT_NAME = "Amiri"
_FONT_REGISTERED = False

_STATUS_COLORS = {
    WITHIN: colors.HexColor("#1B998B"),
    OVER: colors.HexColor("#E08A3C"),
    UNDER: colors.HexColor("#3C7DD9"),
}

_DAY_NAMES = ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
_MONTH_NAMES = ["", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]


def _ensure_font() -> bool:
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return True
    if not _FONT_PATH.exists():
        return False
    pdfmetrics.registerFont(TTFont(_FONT_NAME, str(_FONT_PATH)))
    _FONT_REGISTERED = True
    return True


# إزالة الإيموجي والرموز (خط Amiri لا يحتويها فتظهر كمربعات)
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U00002B00-\U00002BFF"
    "\U00002300-\U000023FF"
    "\U0000FE00-\U0000FE0F"
    "\U00002190-\U000021FF"
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub("", str(text)).strip()


def ar(text: str) -> str:
    """يشكّل النص العربي ويعكسه للعرض الصحيح في PDF (مع إزالة الإيموجي)."""
    return get_display(arabic_reshaper.reshape(_strip_emoji(text)))


def _weight_phrase(change: float | None) -> str | None:
    """صياغة لفظية لتغيّر الوزن لتفادي التباس إشارة السالب في الـ PDF."""
    if change is None:
        return None
    if change < -0.05:
        return f"نزول {abs(change):g} كجم"
    if change > 0.05:
        return f"زيادة {change:g} كجم"
    return "ثابت تقريباً"


class _Page:
    """مساعد رسم RTL على صفحة A4."""

    def __init__(self, c: canvas.Canvas):
        self.c = c
        self.w, self.h = A4
        self.right = self.w - 20 * mm
        self.left = 20 * mm
        self.y = self.h - 25 * mm

    def line_rtl(self, text: str, size: int = 12, color=colors.black, gap: float = 7):
        self.c.setFont(_FONT_NAME, size)
        self.c.setFillColor(color)
        self.c.drawRightString(self.right, self.y, ar(text))
        self.y -= gap * mm

    def kv(self, label: str, value: str, size: int = 12):
        self.c.setFont(_FONT_NAME, size)
        self.c.setFillColor(colors.black)
        self.c.drawRightString(self.right, self.y, ar(label))
        self.c.drawString(self.left, self.y, ar(value))
        self.y -= 7 * mm

    def hr(self):
        self.c.setStrokeColor(colors.HexColor("#DDDDDD"))
        self.c.line(self.left, self.y, self.right, self.y)
        self.y -= 5 * mm

    def space(self, mm_amount: float = 3):
        self.y -= mm_amount * mm


def _header(p: _Page, title: str, subtitle: str):
    p.c.setFillColor(colors.HexColor("#1B998B"))
    p.c.rect(0, p.h - 18 * mm, p.w, 18 * mm, fill=1, stroke=0)
    p.c.setFont(_FONT_NAME, 18)
    p.c.setFillColor(colors.white)
    p.c.drawRightString(p.right, p.h - 12 * mm, ar("رشاقة — " + title))
    p.y = p.h - 28 * mm
    p.line_rtl(subtitle, size=11, color=colors.HexColor("#666666"))
    p.hr()


def weekly_pdf(report: WeeklyReport) -> bytes:
    if not _ensure_font():
        raise RuntimeError("خط العربية غير متوفّر (Amiri-Regular.ttf).")
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    p = _Page(c)
    _header(p, "تقرير أسبوعي", f"من {report.start} إلى {report.end}")

    p.kv("أيام الالتزام (ضمن الهدف):", f"{report.adherent_days} من 7")
    p.kv("أيام فيها تسجيل:", f"{report.logged_days} أيام")
    p.kv("متوسط المتناول:", f"{report.avg_eaten} سعرة")
    p.kv("متوسط الهدف:", f"{report.avg_target} سعرة")
    phrase = _weight_phrase(report.weight_change_kg)
    if phrase:
        p.kv("تغيّر الوزن خلال الأسبوع:", phrase)
    p.hr()

    p.line_rtl("تفصيل الأيام:", size=13)
    for i, d in enumerate(report.days):
        name = _DAY_NAMES[i] if i < len(_DAY_NAMES) else str(d.day)
        color = _STATUS_COLORS.get(d.status, colors.HexColor("#999999"))
        p.c.setFont(_FONT_NAME, 11)
        p.c.setFillColor(colors.black)
        p.c.drawRightString(p.right, p.y, ar(f"{name} ({d.day})"))
        p.c.setFillColor(color)
        p.c.drawString(p.left, p.y, ar(f"{d.status} — {d.eaten_calories}/{int(d.target_calories)} سعرة"))
        p.y -= 6.5 * mm

    p.hr()
    p.line_rtl(report.summary_ar, size=12, color=colors.HexColor("#1B998B"))
    p.space()
    p.line_rtl("تقرير للتوعية وليس بديلاً عن الاستشارة الطبية.", size=9, color=colors.HexColor("#999999"))

    c.showPage()
    c.save()
    return buf.getvalue()


def monthly_pdf(report: MonthlyReport) -> bytes:
    if not _ensure_font():
        raise RuntimeError("خط العربية غير متوفّر (Amiri-Regular.ttf).")
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    p = _Page(c)
    month_name = _MONTH_NAMES[report.month] if 1 <= report.month <= 12 else str(report.month)
    _header(p, "تقرير شهري", f"{month_name} {report.year}")

    p.kv("إجمالي أيام الالتزام:", f"{report.total_adherent_days} يوم")
    p.kv("إجمالي أيام التسجيل:", f"{report.total_logged_days} يوم")
    p.kv("متوسط المتناول اليومي:", f"{report.avg_eaten} سعرة")
    phrase = _weight_phrase(report.weight_change_kg)
    if phrase:
        p.kv("تغيّر الوزن خلال الشهر:", phrase)
    p.hr()

    p.line_rtl("مقارنة الأسابيع:", size=13)
    for idx, w in enumerate(report.weeks, start=1):
        p.c.setFont(_FONT_NAME, 11)
        p.c.setFillColor(colors.black)
        p.c.drawRightString(p.right, p.y, ar(f"الأسبوع {idx} (من {w.start} إلى {w.end})"))
        p.c.setFillColor(colors.HexColor("#1B998B"))
        p.c.drawString(p.left, p.y, ar(f"التزام {w.adherent_days} من 7، متوسط {w.avg_eaten} سعرة"))
        p.y -= 6.5 * mm

    p.hr()
    p.line_rtl(report.summary_ar, size=12, color=colors.HexColor("#1B998B"))
    p.space()
    p.line_rtl("تقرير للتوعية وليس بديلاً عن الاستشارة الطبية.", size=9, color=colors.HexColor("#999999"))

    c.showPage()
    c.save()
    return buf.getvalue()
