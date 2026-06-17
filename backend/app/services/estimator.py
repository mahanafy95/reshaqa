"""خدمة تقدير السعرات — قابلة للتبديل (heuristic / LLM / nutrition API).

الهدف: إعطاء تقدير تقريبي لأي أكلة بالاسم دون مطالبة المستخدم برقم.
المزوّد الافتراضي (none) يستخدم heuristic بالكلمات المفتاحية. مزوّدو LLM/API
يحاولون أولاً ثم يرجعون للـ heuristic عند أي فشل (لا يفشل التقدير أبداً).
"""
from dataclasses import dataclass

from ..config import settings


@dataclass
class EstimateResult:
    name_ar: str
    amount_g: float
    calories: float
    protein: float
    carbs: float
    fat: float
    per100_calories: float
    confidence: str          # high | medium | low
    note_ar: str
    provider: str            # heuristic | openai | nutrition_api


# جدول heuristic: (كلمات مفتاحية, سعرات/100جم, بروتين, نشويات, دهون)
_KEYWORD_TABLE: list[tuple[tuple[str, ...], float, float, float, float]] = [
    (("زيت", "سمن", "زبدة"), 890, 0, 0, 99),
    (("مقلي", "مقلية", "محمر", "محمرة", "قلي"), 320, 8, 28, 19),
    (("مشوي", "مشوية", "مسلوق", "مسلوقة", "صدر"), 165, 26, 2, 6),
    (("سلطة", "خضار", "خضروات", "سبانخ", "خس"), 45, 2, 6, 1.5),
    (("شوربة", "حساء", "شربة"), 60, 3, 7, 2),
    (("حلو", "حلاو", "حلويات", "كيك", "تورتة", "بسكويت", "شوكولاتة", "جاتوه"), 400, 5, 55, 18),
    (("عصير", "مشروب غازي", "كولا", "صودا"), 45, 0.3, 11, 0),
    (("مشروب", "شاي", "قهوة", "نسكافيه"), 35, 0.5, 7, 0.5),
    (("رز", "أرز", "مكرونة", "عيش", "خبز", "معكرونة", "برغل", "فريك"), 180, 5, 35, 2.5),
    (("دجاج", "فراخ", "لحم", "لحمة", "كفتة", "سمك", "تونة", "بيض"), 200, 22, 2, 12),
    (("جبنة", "جبن", "لبنة"), 280, 16, 4, 22),
    (("لبن", "حليب", "زبادي"), 65, 3.4, 5, 3.2),
    (("فول", "عدس", "حمص", "فاصوليا", "بقول"), 120, 8, 16, 2.5),
    (("فاكهة", "فواكه", "تفاح", "موز", "برتقال", "عنب", "بطيخ", "مانجو"), 60, 0.8, 15, 0.2),
    (("مكسرات", "لوز", "عين جمل", "كاجو", "فول سوداني"), 580, 18, 20, 50),
    (("بيتزا", "برجر", "ساندويتش", "شاورما", "حواوشي"), 260, 12, 26, 12),
]

# تقدير افتراضي متوازن لأي أكلة غير معروفة
_DEFAULT = (160.0, 7.0, 18.0, 6.5)


class HeuristicEstimator:
    provider = "heuristic"

    def estimate(self, name_ar: str, amount_g: float) -> EstimateResult:
        text = (name_ar or "").strip()
        per100 = _DEFAULT
        confidence = "low"
        note = "تقدير تقريبي — تقدر تعدّل الرقم يدوياً لو عندك القيمة الدقيقة."
        for keywords, cal, p, c, f in _KEYWORD_TABLE:
            if any(k in text for k in keywords):
                per100 = (cal, p, c, f)
                confidence = "medium"
                note = "تقدير تقريبي حسب نوع الأكلة — تقدر تعدّله يدوياً."
                break

        factor = amount_g / 100.0
        return EstimateResult(
            name_ar=text,
            amount_g=amount_g,
            calories=round(per100[0] * factor),
            protein=round(per100[1] * factor, 1),
            carbs=round(per100[2] * factor, 1),
            fat=round(per100[3] * factor, 1),
            per100_calories=per100[0],
            confidence=confidence,
            note_ar=note,
            provider=self.provider,
        )


class _FallbackEstimator(HeuristicEstimator):
    """قاعدة لمزوّدين خارجيين — يحاولون ثم يرجعون للـ heuristic عند الفشل."""

    provider = "heuristic"

    def estimate(self, name_ar: str, amount_g: float) -> EstimateResult:
        # محاولة المزوّد الخارجي هنا مستقبلاً (LLM/API). في حال غياب المفتاح أو الفشل:
        return super().estimate(name_ar, amount_g)


def get_estimator():
    """يُرجع المُقدِّر حسب الإعدادات (قابل للتبديل)."""
    provider = settings.CALORIE_ESTIMATOR_PROVIDER
    if provider == "openai" and settings.OPENAI_API_KEY:
        return _FallbackEstimator()
    if provider == "nutrition_api" and settings.NUTRITION_API_KEY:
        return _FallbackEstimator()
    return HeuristicEstimator()
