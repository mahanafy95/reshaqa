"""خدمة OCR لجدول التغذية — تحليل نص ملصق التغذية لاستخراج القيم.

دالة parse_nutrition_text منفصلة وقابلة للاختبار. تتعرّف على المصطلحات
العربية والإنجليزية الشائعة على ملصقات التغذية.
"""
import re
from dataclasses import dataclass

from ..config import settings


@dataclass
class NutritionExtract:
    calories: float | None
    protein: float | None
    carbs: float | None
    fat: float | None
    basis_ar: str           # "لكل 100 جرام" أو "لكل حصة" أو "غير محدد"
    raw_text: str


# مرادفات كل عنصر (عربي + إنجليزي)
_PATTERNS = {
    "calories": [
        r"سعر(?:ات)?(?:\s*حرارية)?", r"طاقة", r"calories", r"energy", r"kcal", r"السعرات",
    ],
    "protein": [r"بروتين", r"protein"],
    "carbs": [r"كربوهيدرات", r"نشويات", r"carbohydrate[s]?", r"carbs", r"كارب"],
    "fat": [r"دهون", r"دهن", r"fat", r"الدهون"],
}

_NUMBER = r"(\d+(?:[.,]\d+)?)"


def _find_value(text: str, keys: list[str]) -> float | None:
    for key in keys:
        # رقم بعد الكلمة المفتاحية (مع احتمال وحدة بينهما)
        m = re.search(key + r"[^0-9\n]{0,15}?" + _NUMBER, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except ValueError:
                continue
    return None


def parse_nutrition_text(text: str) -> NutritionExtract:
    """يستخرج السعرات والماكروز من نص ملصق تغذية (عربي/إنجليزي)."""
    t = text or ""
    basis = "غير محدد"
    if re.search(r"100\s*(?:جم|جرام|g\b|gram)", t, re.IGNORECASE):
        basis = "لكل 100 جرام"
    elif re.search(r"حصة|الحصة|serving|portion", t, re.IGNORECASE):
        basis = "لكل حصة"

    return NutritionExtract(
        calories=_find_value(t, _PATTERNS["calories"]),
        protein=_find_value(t, _PATTERNS["protein"]),
        carbs=_find_value(t, _PATTERNS["carbs"]),
        fat=_find_value(t, _PATTERNS["fat"]),
        basis_ar=basis,
        raw_text=t.strip(),
    )


def ocr_image_to_text(image_bytes: bytes) -> str | None:
    """يحوّل صورة إلى نص حسب المزوّد المُهيّأ. None لو لا يوجد محرك OCR."""
    provider = settings.OCR_PROVIDER
    if provider == "tesseract":
        try:
            import io

            import pytesseract  # type: ignore
            from PIL import Image

            img = Image.open(io.BytesIO(image_bytes))
            return pytesseract.image_to_string(img, lang="ara+eng")
        except Exception:
            return None
    # cloud_vision أو مزوّدون آخرون يُضافون هنا
    return None
