"""خدمة تقدير السعرات — قابلة للتبديل (heuristic / LLM / nutrition API).

الهدف: إعطاء تقدير تقريبي لأي أكلة بالاسم دون مطالبة المستخدم برقم.
المزوّد الافتراضي (none) يستخدم heuristic بالكلمات المفتاحية. لو الـ AI مفعّل
(GEMINI أو OpenRouter) نجرّب تقدير حقيقي من الـ AI أولاً (يعرف إن الخيار ~15
والعسل ~300/100جم...) ثم نرجع للـ heuristic عند أي فشل (لا يفشل التقدير أبداً).
"""
from dataclasses import dataclass

from ..config import settings

# محلّيات بدون سعرات (استيفيا/سكرالوز...) — سعراتها صفر فعليًا، مش زي السكر (≈٤٠٠).
_SWEETENERS = {
    "استيفيا", "استفيا", "ستيفيا", "ستفيا", "أستيفيا",
    "سكرالوز", "سكرلوز", "سوكرالوز",
    "أسبارتام", "اسبارتام", "اسبرتام",
    "سكارين", "سكرين", "ساكارين",
    "إريثريتول", "اريثريتول",
    "سويتنر", "stevia", "sucralose", "aspartame",
}
_SWEETENER_FILLERS = {
    "سكر", "محلي", "محلّي", "محلى", "طبيعي", "صناعي", "دايت", "بدون", "صفر",
    "سعرات", "سعره", "سعر", "حرارية", "زيرو", "نقي",
    "ملعقة", "ملعقه", "ملاعق", "كوب", "كوباية", "نقطة", "نقط", "قرص", "اقراص", "كيس", "ظرف",
}
_ZERO_CAL_PHRASES = (
    "صفر سعرات", "صفر سعره", "بدون سعرات", "زيرو سعرات", "زيرو كالوري",
    "0 سعرة", "0 سعرات", "zero cal", "محلي صناعي", "محلّي صناعي", "سكر دايت",
)
# مشروبات غازية/طاقة بنكهة دايت/زيرو — سعراتها ≈ صفر (مش زي العادية). بنشترط إنها مشروب
# معروف عشان «آيس كريم دايت» أو «زبادي لايت» يفضلوا أكل عادي ليه سعرات.
_DIET_SODAS = (
    "بيبسي", "بيبسى", "كوكا", "كولا", "سبرايت", "سفن", "سيفن", "ميرندا", "فانتا",
    "شويبس", "ردبول", "ريدبول", "مونستر", "سينالكو", "pepsi", "cola", "sprite", "fanta",
)
_ZERO_MARKERS = ("دايت", "زيرو", "لايت", "خفيف", "بدون سكر", "شوجر فري", "diet", "zero", "light", "sugar free")


def is_zero_cal_sweetener(name: str) -> bool:
    """True لو الاسم محلّي بدون سعرات (استيفيا/سكرالوز...)، أو مشروب غازي دايت/زيرو،
    أو فيه «صفر سعرات» صراحةً.

    محافظ: «سكر» لوحده يفضل سكر عادي، و«كيك استيفيا»/«آيس كريم دايت» يفضلوا أكل عادي.
    """
    q = (name or "").strip().lower().replace("،", " ")
    # الشوكولاتة (حتى الدايت/الخالية من السكر) ليها سعرات — ومنعًا للالتباس مع «كولا» جوّه «شوكولاتة»
    for variant in ("شوكولات", "شيكولات", "شكولات", "تشوكولات", "شوكلات"):
        if variant in q:
            return False
    if not q:
        return False
    if any(p in q for p in _ZERO_CAL_PHRASES):
        return True
    if any(b in q for b in _DIET_SODAS) and any(m in q for m in _ZERO_MARKERS):
        return True
    words = [w for w in q.split() if w not in _SWEETENER_FILLERS]
    return bool(words) and all(w in _SWEETENERS for w in words)


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
    provider: str            # heuristic | ai | openai | nutrition_api


# جدول heuristic: (كلمات مفتاحية, سعرات/100جم, بروتين, نشويات, دهون)
# مرتّب: الأكثر تحديداً أولاً (مقلي/حلويات) ثم العام، عشان «بطاطس مقلية» متتطابقش كخضار.
_KEYWORD_TABLE: list[tuple[tuple[str, ...], float, float, float, float]] = [
    (("زيت", "سمن", "زبدة"), 890, 0, 0, 99),
    (("عسل", "دبس", "مربى"), 304, 0.3, 82, 0),
    (("سكر",), 400, 0, 100, 0),
    (("مقلي", "مقلية", "محمر", "محمرة", "قلي"), 320, 8, 28, 19),
    (("حلو", "حلاو", "حلويات", "كيك", "تورتة", "بسكويت", "شوكولاتة", "جاتوه"), 400, 5, 55, 18),
    (("مكسرات", "لوز", "عين جمل", "كاجو", "فول سوداني"), 580, 18, 20, 50),
    # ---- أكلات مصرية شائعة (قيم تقريبية لكل 100جم مطبوخة — قابلة للتعديل يدويًا) ----
    # تيجي قبل المجموعات العامة عشان «كرنب محشي» يتحسب محشي مش خضار.
    (("كشري", "كشرى"), 150, 4.5, 27, 3),
    (("ملوخية", "ملوخيه"), 70, 4, 5, 4),
    (("طعمية", "طعميه", "فلافل"), 330, 13, 32, 17),
    (("محشي", "محاشي", "ورق عنب", "كرنب محشي"), 130, 3, 18, 5),
    (("كبدة", "كبده", "كبد"), 150, 21, 4, 5),
    (("بشاميل", "بشامل"), 190, 8, 18, 10),
    (("بيتزا", "برجر", "ساندويتش", "شاورما", "حواوشي"), 260, 12, 26, 12),
    # بطاطس/بطاطا (قبل «مشوي/مسلوق» العام عشان «بطاطس مسلوقة» متتحسبش كلحم مسلوق)
    (("بطاطس مسلوقة", "بطاطا مسلوقة", "بطاطس مسلوق", "بطاطا مسلوق"), 87, 2, 20, 0.1),
    (("بطاطس", "بطاطا"), 90, 2, 20, 0.1),
    (("مشوي", "مشوية", "مسلوق", "مسلوقة", "صدر"), 165, 26, 2, 6),
    (("شوربة", "حساء", "شربة"), 60, 3, 7, 2),
    (("عصير", "مشروب غازي", "كولا", "صودا"), 45, 0.3, 11, 0),
    (("مشروب", "شاي", "قهوة", "نسكافيه"), 35, 0.5, 7, 0.5),
    (("رز", "أرز", "مكرونة", "عيش", "خبز", "معكرونة", "برغل", "فريك"), 180, 5, 35, 2.5),
    (("دجاج", "فراخ", "لحم", "لحمة", "كفتة", "سمك", "تونة", "بيض"), 200, 22, 2, 12),
    (("جبنة", "جبن", "لبنة"), 280, 16, 4, 22),
    (("لبن", "حليب", "زبادي"), 65, 3.4, 5, 3.2),
    (("فول", "عدس", "حمص", "فاصوليا", "بقول"), 120, 8, 16, 2.5),
    # ---- خضروات بسيطة (~20 سعرة/100جم) ----
    (
        (
            "خيار", "خيارة", "طماطم", "طماطه", "بندورة", "جزر", "فلفل", "بصل", "ثوم",
            "كوسة", "كوسا", "باذنجان", "بزنجان", "ملفوف", "كرنب", "قرنبيط", "زهرة",
            "فجل", "بقدونس", "كزبرة", "جرجير", "خس", "سبانخ", "بامية", "فاصوليا خضراء",
            "سلطة", "خضار", "خضروات", "ورقيات",
        ),
        22, 1.2, 4.5, 0.2,
    ),
    # ---- فواكه (~50 سعرة/100جم) ----
    (
        (
            "تفاح", "تفاحة", "موز", "موزة", "برتقال", "برتقالة", "يوسفي", "ليمون",
            "فراولة", "فراوله", "عنب", "مانجو", "مانجه", "خوخ", "مشمش", "كمثرى",
            "جوافة", "رمان", "تين", "كيوي", "أناناس", "بطيخ", "شمام", "كانتالوب",
            "بلح", "تمر", "فاكهة", "فواكه",
        ),
        52, 0.7, 13, 0.2,
    ),
]

# تقدير افتراضي لأي أكلة غير معروفة — أقل من السابق (160) وأقرب لأكلة متوسطة خفيفة،
# مع ثقة منخفضة وملاحظة واضحة تطلب التعديل اليدوي.
_DEFAULT = (120.0, 5.0, 16.0, 4.0)


class HeuristicEstimator:
    provider = "heuristic"

    def estimate(self, name_ar: str, amount_g: float) -> EstimateResult:
        text = (name_ar or "").strip()
        # محلّي بدون سعرات (استيفيا/سكرالوز/«صفر سعرات») → صفر سعرة، مش زي السكر.
        if is_zero_cal_sweetener(text):
            return EstimateResult(
                name_ar=text, amount_g=amount_g, calories=0, protein=0, carbs=0, fat=0,
                per100_calories=0, confidence="high",
                note_ar="محلّي بدون سعرات — سعراته صفر تقريبًا.", provider="heuristic",
            )
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
            provider="heuristic",
        )


class _AIEstimator(HeuristicEstimator):
    """مُقدّر مدعوم بالذكاء الاصطناعي — يجرّب الـ AI أولاً ثم يرجع للـ heuristic عند الفشل."""

    provider = "ai"

    def estimate(self, name_ar: str, amount_g: float) -> EstimateResult:
        text = (name_ar or "").strip()
        # استيراد كسول لتجنّب أي مشاكل ترتيب استيراد دائري
        from . import ai_assistant

        try:
            ai = ai_assistant.estimate_calories_ai(text, amount_g)
        except Exception:
            ai = None

        if ai is not None:
            try:
                per100_cal = float(ai["kcal_per_100"])
                p = float(ai.get("protein", 0) or 0)
                c = float(ai.get("carbs", 0) or 0)
                f = float(ai.get("fat", 0) or 0)
            except (KeyError, TypeError, ValueError):
                per100_cal = None
            else:
                if per100_cal >= 0:
                    factor = amount_g / 100.0
                    return EstimateResult(
                        name_ar=text,
                        amount_g=amount_g,
                        calories=round(per100_cal * factor),
                        protein=round(p * factor, 1),
                        carbs=round(c * factor, 1),
                        fat=round(f * factor, 1),
                        per100_calories=per100_cal,
                        confidence="medium",
                        note_ar="تقدير من المساعد الذكي — راجعه وعدّله لو محتاج.",
                        provider=self.provider,
                    )

        # غياب المفتاح أو فشل الـ AI → الرجوع للـ heuristic المحلي
        return super().estimate(text, amount_g)


def get_estimator():
    """يُرجع المُقدِّر حسب الإعدادات (قابل للتبديل).

    لو الـ AI مفعّل (GEMINI/OpenRouter) نستخدم مُقدّراً مدعوماً بالـ AI (مع رجوع للـ heuristic)؛
    وإلا نستخدم الـ heuristic المحلي المجاني.
    """
    if settings.ai_enabled:
        return _AIEstimator()
    return HeuristicEstimator()
