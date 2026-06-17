"""محلّل لغة عربي (مصري) مجاني بالكامل — يحوّل كلام حر زي
"النهاردة اكلت بيضتين وكوباية لبن ورغيف عيش وعلى الغدا طبق رز وفرخة"
إلى أصناف منظّمة (اسم/كمية/وحدة/وجبة) جاهزة للتسعير والتسجيل.

منطق نصّي خالص بدون أي شبكة أو مفتاح أو LLM — صفر تكلفة.
التسعير (السعرات) بيتم في الراوتر عبر مكتبة الأكل + المقدّر المحلي.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ---------- تطبيع ----------
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫۰۱۲۳۴۵۶۷۸۹", "0123456789.0123456789")


def normalize(text: str) -> str:
    t = text.translate(_DIGITS)
    t = t.replace("ـ", "")  # tatweel
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ---------- كلمات الأرقام ----------
NUMBER_WORDS: dict[str, float] = {
    "نص": 0.5, "نصف": 0.5, "ربع": 0.25, "تلت": 0.333, "ثلث": 0.333,
    "واحد": 1, "واحدة": 1, "وحدة": 1, "واحده": 1,
    "اتنين": 2, "إتنين": 2, "اثنين": 2, "تنين": 2,
    "تلاتة": 3, "ثلاثة": 3, "تلاته": 3,
    "اربعة": 4, "أربعة": 4, "اربع": 4, "اربعه": 4,
    "خمسة": 5, "خمس": 5, "خمسه": 5,
    "ستة": 6, "ست": 6, "سته": 6,
    "سبعة": 7, "سبعه": 7, "سبع": 7,
    "تمنية": 8, "ثمانية": 8, "تمنيه": 8,
    "تسعة": 9, "تسعه": 9, "تسع": 9,
    "عشرة": 10, "عشره": 10, "عشر": 10,
}

# ---------- جدول الوحدات المنزلية (وحدة -> جرام افتراضي) ----------
# مرتّب: المرادفات الأطول أولاً حتى لا تُلتقط جزئياً.
UNIT_GRAMS: list[tuple[tuple[str, ...], float]] = [
    (("معلقة كبيرة", "ملعقة كبيرة", "معلقه كبيره", "م.ك"), 15.0),
    (("معلقة صغيرة", "ملعقة صغيرة", "معلقه صغيره", "م.ص"), 5.0),
    (("معلقة", "ملعقة", "معلقه", "ملعقه"), 10.0),
    (("كوب صغير", "فنجان", "فنجال"), 120.0),
    (("كوباية", "كوبايه", "كباية", "كبايه", "كوب"), 240.0),
    (("نص رغيف",), 45.0),
    (("رغيف", "عيش بلدي", "عيشة", "عيشه"), 90.0),
    (("شريحة", "شريحه"), 30.0),
    (("طبق كبير",), 450.0),
    (("طبق صغير",), 150.0),
    (("طبق", "صحن", "طبق متوسط"), 300.0),
    (("علبة", "علبه"), 170.0),
    (("كوز",), 200.0),
    (("حتة", "حته", "قطعة", "قطعه"), 60.0),
    (("كف", "حفنة", "حفنه"), 30.0),
    (("حبة", "حبه", "حبّة"), 80.0),
    (("لتر", "لتر"), 1000.0),
    (("كيلو", "كجم", "كيلوجرام"), 1000.0),
    (("جرام", "جم", "غرام", "g"), 1.0),
    (("مل", "ملي", "ml"), 1.0),
]
_LIQUID_UNITS = {"كوباية", "كوبايه", "كباية", "كبايه", "كوب", "كوب صغير", "فنجان", "فنجال", "لتر", "مل", "ملي", "ml"}


def unit_grams(unit_ar: str | None) -> float | None:
    if not unit_ar:
        return None
    for syns, g in UNIT_GRAMS:
        if unit_ar in syns:
            return g
    return None


# ---------- كلمات الوجبات ----------
MEAL_KEYWORDS: dict[str, str] = {
    "فطار": "breakfast", "الفطار": "breakfast", "فطرت": "breakfast", "افطرت": "breakfast",
    "ريوق": "breakfast", "الريوق": "breakfast",
    "غدا": "lunch", "الغدا": "lunch", "غدى": "lunch", "اتغديت": "lunch", "غداء": "lunch",
    "عشا": "dinner", "العشا": "dinner", "عشى": "dinner", "اتعشيت": "dinner", "عشاء": "dinner",
    "سناك": "snack", "سناكس": "snack", "تصبيرة": "snack",
}

# كلمات حشو تُزال من اسم الصنف
STOPWORDS = {
    "النهاردة", "النهارده", "انهاردة", "انهارده", "اكلت", "أكلت", "كلت", "شربت", "تناولت",
    "كان", "عندي", "على", "في", "من", "كمان", "و", "مع", "بتاع", "بتاعة", "حوالي", "تقريبا",
    "تقريباً", "زي", "نص", "،", "علي", "خدت", "اخدت",
}

_FRACTION_PREFIX = {"نص", "نصف", "ربع", "تلت", "ثلث"}


@dataclass
class ParsedItem:
    name_ar: str
    qty: float
    unit_ar: str | None
    meal: str
    raw_text: str


# كلمات تُتخطّى في بداية المقطع قبل البحث عن ماركر الوجبة (حشو/أفعال تمهيدية)
_LEADING_SKIP = {
    "على", "علي", "في", "وعلى", "وعلي", "و",
    "النهاردة", "النهارده", "انهاردة", "انهارده", "امبارح",
    "اكلت", "أكلت", "كلت", "تناولت", "خدت", "اخدت", "شربت", "كمان", "بعدين",
}


def _strip_leading_meal(seg: str) -> tuple[str | None, str]:
    """يكشف ماركر وجبة في بداية المقطع (حتى لو سبقه حشو زي "النهاردة فطرت") ويزيله."""
    tokens = seg.split()
    meal = None
    i = 0
    while i < len(tokens):
        tok = tokens[i].strip("،.,")
        if tok in MEAL_KEYWORDS:
            meal = MEAL_KEYWORDS[tok]
            i += 1
            continue
        if tok in _LEADING_SKIP:
            i += 1
            continue
        break
    return meal, " ".join(tokens[i:]).strip()


def _extract_qty_unit(frag: str) -> tuple[float, str | None, str]:
    """يطلّع (الكمية، الوحدة، اسم الصنف) من مقطع واحد."""
    norm = frag
    # 1) الوحدة (المرادفات الأطول أولاً)
    unit_ar: str | None = None
    for syns, _g in UNIT_GRAMS:
        for syn in syns:
            if re.search(rf"(^|\s){re.escape(syn)}(\s|$)", norm):
                unit_ar = syn
                norm = re.sub(rf"(^|\s){re.escape(syn)}(\s|$)", " ", norm, count=1)
                break
        if unit_ar:
            break

    qty: float | None = None
    # 2) رقم صريح
    m = re.search(r"\d+(?:\.\d+)?", norm)
    if m:
        qty = float(m.group())
        norm = (norm[: m.start()] + " " + norm[m.end():]).strip()

    tokens = norm.split()
    # 3) كلمة رقم (نص/اتنين/تلاتة...)
    if qty is None:
        for idx, tok in enumerate(tokens):
            tk = tok.strip("،.,")
            if tk in NUMBER_WORDS:
                qty = NUMBER_WORDS[tk]
                tokens.pop(idx)
                break

    # 4) المثنى (بيضتين/كوبايتين/رغيفين)
    if qty is None:
        for idx, tok in enumerate(tokens):
            tk = tok.strip("،.,")
            if len(tk) >= 5 and tk.endswith("تين"):
                stem = tk[:-3] + "ة"
                qty = 2
                tokens[idx] = stem
                break
            if len(tk) >= 5 and tk.endswith("ين") and unit_grams(tk[:-2]) is not None:
                qty = 2
                tokens[idx] = tk[:-2]
                if unit_ar is None:
                    unit_ar = tk[:-2]
                    tokens.pop(idx)
                break

    if qty is None:
        qty = 1.0

    # 5) إزالة كلمات الحشو وبناء الاسم
    name_tokens = [t for t in tokens if t.strip("،.,") and t.strip("،.,") not in STOPWORDS]
    name = " ".join(name_tokens).strip(" ،.")
    # لو الاسم فضي والكلمة كانت وحدة (زي "رغيف"/"كوب") فالوحدة نفسها هي الصنف
    if not name and unit_ar:
        name = unit_ar
    return qty, unit_ar, name


def parse_text(text: str, default_meal: str = "snack") -> list[ParsedItem]:
    """يحلّل نصاً حراً إلى قائمة أصناف. منطق خالص بدون قاعدة بيانات."""
    norm = normalize(text)
    if not norm:
        return []
    # تقسيم على الفواصل وحرف الواو الرابط (بمسافة قبله)
    segments = re.split(r"[،,؛]|\+|\n|\s+و\s*", norm)

    items: list[ParsedItem] = []
    current_meal = default_meal
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        meal_marker, residue = _strip_leading_meal(seg)
        if meal_marker:
            current_meal = meal_marker
        if not residue:
            continue
        qty, unit_ar, name = _extract_qty_unit(residue)
        if not name or len(name) < 2:
            continue
        items.append(ParsedItem(name_ar=name, qty=qty, unit_ar=unit_ar, meal=current_meal, raw_text=seg))
    return items


def resolve_grams(
    qty: float, unit_ar: str | None, lib_household_unit: str | None, lib_household_grams: float | None
) -> float:
    """يحوّل (كمية + وحدة) إلى جرامات. يفضّل الوحدة المنزلية للصنف من المكتبة لو مفيش وحدة صريحة."""
    g = unit_grams(unit_ar)
    if g is not None:
        return round(g * qty, 1)
    if lib_household_grams:
        return round(lib_household_grams * qty, 1)
    return round(100.0 * qty, 1)
