"""بحث غذائي خارجي لأكلة/منتج مش موجود في مكتبتنا المحلية.

بيجرّب مصدرين مجانيين بالترتيب:
1) Gemini (generateContent عادي بمفتاح مجاني) — معرفته بسعرات الأكل ممتازة وحصّته سخيّة.
   («بحث Google» grounding مدفوع → بيترجّع 429 على الباقة المجانية، فمتعطّل افتراضيًا.)
2) OpenFoodFacts (بحث بالاسم) — مجاني وبدون مفتاح؛ أفضل للمنتجات المعبّأة بأسماء لاتينية.
يرجّع None لو الاتنين فشلوا. لا يرفع استثناء أبداً.

النتيجة لكل 100 جرام. لو اتمرّر db بنخزّن النتيجة في FoodLibrary (flush فقط — الراوتر
بيعمل commit) عشان المرة الجاية تطلع فورًا من غير إنترنت ويلاقيها المساعد كمان.
"""
import logging
import re
from dataclasses import dataclass

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings

logger = logging.getLogger("reshaqa.food_lookup")

OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_MAX_KCAL = 900.0
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")


@dataclass
class FoodNutrition:
    kcal_per_100: float
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None
    source: str = ""              # openfoodfacts | gemini_search
    matched_name: str | None = None


def _bound_kcal(value) -> float | None:
    try:
        k = float(value)
    except (TypeError, ValueError):
        return None
    return round(k, 1) if 0 < k <= _MAX_KCAL else None


def _bound_macro(value) -> float | None:
    try:
        m = float(value)
    except (TypeError, ValueError):
        return None
    return round(m, 1) if 0 <= m <= 100 else None


def _search_openfoodfacts(name: str) -> FoodNutrition | None:
    """بحث بالاسم في OpenFoodFacts (endpoint النص الكامل القديم — v2 مابيدعمش بحث نصّي)."""
    try:
        resp = httpx.get(
            OFF_SEARCH_URL,
            params={
                "search_terms": name, "search_simple": 1, "action": "process", "json": 1,
                "page_size": 5, "sort_by": "unique_scans_n",
                "fields": "product_name,product_name_ar,brands,nutriments,code",
            },
            headers={"User-Agent": settings.OFF_USER_AGENT},
            timeout=settings.FOOD_LOOKUP_OFF_TIMEOUT,
        )
        if resp.status_code != 200:  # 503 = تجاوز الحد (10/دقيقة/IP)
            return None
        products = resp.json().get("products") or []
    except (httpx.HTTPError, ValueError):
        return None
    for p in products:
        nutr = p.get("nutriments") or {}
        cal = nutr.get("energy-kcal_100g")
        if cal is None and nutr.get("energy_100g"):
            cal = nutr["energy_100g"] / 4.184  # kJ -> kcal
        kcal = _bound_kcal(cal)
        if kcal is None:
            continue
        nm = p.get("product_name_ar") or p.get("product_name") or name
        return FoodNutrition(
            kcal_per_100=kcal,
            protein=_bound_macro(nutr.get("proteins_100g")),
            carbs=_bound_macro(nutr.get("carbohydrates_100g")),
            fat=_bound_macro(nutr.get("fat_100g")),
            source="openfoodfacts", matched_name=str(nm).strip()[:80] or name,
        )
    return None


_KCAL_NEAR_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:سعرة|سعرات|سعر حراري|كيلو ?كالوري|kcal|cal\b|calories?)", re.IGNORECASE
)
_KCAL_AFTER_RE = re.compile(
    r"(?:سعرة|سعرات|سعرات حرارية|kcal|calories?)\D{0,12}(\d+(?:\.\d+)?)", re.IGNORECASE
)


def _extract_kcal(text: str) -> float | None:
    """يطلّع رقم السعرات من ردّ نصّي، ويتجنّب «100» بتاعة «100 جرام» في السؤال."""
    t = text.replace("٫", ".").replace("،", " ")
    for rx in (_KCAL_NEAR_RE, _KCAL_AFTER_RE):
        m = rx.search(t)
        if m:
            k = _bound_kcal(m.group(1))
            if k is not None:
                return k
    # وإلا أول رقم معقول مش 100 (السؤال نفسه فيه «100 جرام»)
    for m in _NUM_RE.finditer(t):
        if m.group(0) not in ("100", "100.0"):
            k = _bound_kcal(m.group(0))
            if k is not None:
                return k
    return None


def _ask_gemini(name: str) -> FoodNutrition | None:
    """يسأل Gemini عن سعرات الأكلة لكل 100 جرام.

    افتراضيًا نداء عادي (generateContent بدون أداة بحث) — مجاني وحصّته سخيّة ومعرفة
    Gemini بسعرات الأكل ممتازة. «التأريض ببحث Google» (tools.google_search) ميزة مدفوعة
    (الباقة المجانية بترجّع 429)، فمنفعّلهوش غير لو GEMINI_GROUNDING_ENABLED=True.
    """
    key = settings.GEMINI_API_KEY.strip()
    if not key:
        return None
    url = _GEMINI_URL.format(model=settings.FOOD_LOOKUP_GEMINI_MODEL)
    use_search = settings.GEMINI_GROUNDING_ENABLED
    if use_search:
        prompt = (
            f"دوّر على الإنترنت عن «{name}» وجيب سعراته الحرارية لكل 100 جرام من مصدر غذائي موثوق. "
            "اكتب جملة قصيرة فيها رقم السعرات لكل 100 جرام بوضوح (مثال: «الكشري ~150 سعرة لكل 100 جرام»)."
        )
    else:
        prompt = (
            f"كام سعرة حرارية في 100 جرام من «{name}»؟ ردّ بجملة قصيرة فيها رقم السعرات لكل "
            "100 جرام بوضوح (مثال: «الكشري ~150 سعرة لكل 100 جرام»). لو مش متأكد قدّر أقرب رقم معقول."
        )
    body: dict = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0},
    }
    if use_search:
        body["tools"] = [{"google_search": {}}]
    try:
        resp = httpx.post(
            url,
            params={"key": key},
            json=body,
            timeout=settings.FOOD_LOOKUP_GEMINI_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning("Gemini food-lookup رجّع %s: %s", resp.status_code, resp.text[:160])
            return None
        parts = resp.json()["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts)
    except Exception:
        logger.exception("فشل نداء Gemini للبحث الغذائي")
        return None
    kcal = _extract_kcal(text)
    if kcal is None:
        return None
    return FoodNutrition(kcal_per_100=kcal, source="gemini", matched_name=name[:80])


def _remember(db: Session, query_name: str, result: FoodNutrition) -> None:
    """يخزّن النتيجة في FoodLibrary (flush فقط) عشان تتفتكر وتطلع فورًا المرة الجاية."""
    from ..models.food import FoodLibrary

    name = (result.matched_name or query_name).strip()[:120]
    if not name:
        return
    try:
        exists = db.scalar(
            select(FoodLibrary).where(func.lower(FoodLibrary.name_ar) == name.lower()).limit(1)
        )
        if exists is not None:
            return
        db.add(FoodLibrary(
            name_ar=name, calories_per_100=result.kcal_per_100,
            protein=result.protein or 0, carbs=result.carbs or 0, fat=result.fat or 0,
            region="web",
        ))
        db.flush()
    except Exception:
        logger.exception("فشل تخزين نتيجة البحث الغذائي")


def search_food_calories(name: str, *, db: Session | None = None) -> FoodNutrition | None:
    """يبحث عن سعرات أكلة مش موجودة محليًا (OpenFoodFacts ثم Gemini-grounding). None لو فشل."""
    if not settings.FOOD_LOOKUP_ENABLED:
        return None
    q = (name or "").strip()
    if len(q) < 2:
        return None
    # Gemini أولاً (أدق وأشمل لأي أكلة)، وإلا OpenFoodFacts (مجاني، للمنتجات المعبّأة).
    result = _ask_gemini(q) or _search_openfoodfacts(q)
    if result is not None and db is not None:
        _remember(db, q, result)
    return result
