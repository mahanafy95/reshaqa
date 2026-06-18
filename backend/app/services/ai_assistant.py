"""مساعد صحي بالذكاء الاصطناعي عبر Google Gemini (الباقة المجانية).

يضيف طبقة محادثة ودّية فوق المحلّل المحلي:
- حساب السعرات يفضل **محسوبًا محليًا من قاعدة بياناتنا** (مش من الـ LLM) — أدق وأأمن.
- Gemini بيدّي ردّ محادثة ودّي ويجاوب أسئلة صحية عامة.
يتعطّل بهدوء لو المفتاح مش مضبوط أو حصل خطأ (نرجع للرد المحلي).
"""
import json
import logging
import re

import httpx

from ..config import settings

logger = logging.getLogger("reshaqa.ai")

_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_SYSTEM = (
    "إنت مساعد تغذية وصحة ودود لتطبيق 'رشاقة'، بتتكلم بالعامية المصرية وباختصار. "
    "بتساعد المستخدم في أكله ووزنه وعاداته الصحية بنبرة مشجّعة وغير حاكمة. "
    "ماتديش تشخيص أو علاج طبي — لو سأل عن حاجة طبية انصحه يستشير مختص. "
    "خلّي ردّك قصير (جملتين-تلاتة)."
)


def _generate(
    prompt: str, *, max_tokens: int = 320, temperature: float = 0.4, system: str | None = None
) -> str | None:
    if not settings.ai_enabled:
        return None
    url = _URL.format(model=settings.GEMINI_MODEL)
    try:
        resp = httpx.post(
            url,
            params={"key": settings.GEMINI_API_KEY},
            json={
                "system_instruction": {"parts": [{"text": system or _SYSTEM}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
            },
            timeout=20.0,
        )
        if resp.status_code != 200:
            logger.warning("Gemini رجّع %s: %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
        return text or None
    except Exception:
        logger.exception("فشل نداء Gemini")
        return None


def meal_reply(user_text: str, items_summary: str, total_calories: int, logged: bool) -> str | None:
    """ردّ محادثة ودّي على تسجيل وجبة (السعرات محسوبة محليًا ومُمرَّرة كحقيقة)."""
    action = "وسجّلتها له" if logged else "(لسه ماتسجّلتش، مستني تأكيده)"
    prompt = (
        f"المستخدم كتب: «{user_text}»\n"
        f"حسبت له الأصناف دي محليًا {action}:\n{items_summary}\n"
        f"الإجمالي: {total_calories} سعرة.\n"
        "ردّ عليه بجملة ودّية مشجّعة تؤكّد اللي اتسجّل وتدّيه نصيحة بسيطة لو ينفع. "
        "ماتغيّرش الأرقام."
    )
    return _generate(prompt)


def general_reply(user_text: str) -> str | None:
    """ردّ على سؤال صحي/تغذوي عام (مش تسجيل وجبة)."""
    return _generate(f"المستخدم سأل: «{user_text}»\nجاوبه باختصار ونبرة مشجّعة.")


# ---------- استخراج الوجبة بالذكاء الاصطناعي (الأسماء + الجرامات فقط — السعرات تُحسب محليًا) ----------
_PARSE_SYSTEM = (
    "إنت محلّل وجبات لتطبيق تغذية مصري. مهمتك تستخرج الأكلات اللي قال المستخدم إنه أكلها "
    "من كلام بالعامية المصرية، وتقدّر وزن كل صنف بالجرام بشكل واقعي. "
    "لو النص سؤال أو طلب (مش تسجيل أكل فعلي)، حُطّ is_question=true وخلّي items فاضية. "
    "رُدّ بـ JSON فقط بدون أي شرح، بالشكل ده بالظبط: "
    '{"is_question": false, "items": [{"name_ar": "اسم الأكلة بالعربي", "grams": رقم}]}'
)

def _strip_json_fences(text: str) -> str:
    t = text.strip()
    # شيل ```json ... ``` لو موجودة (سطر أول/أخير أو inline)
    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


def parse_meal_ai(text: str) -> dict | None:
    """يطلب من Gemini استخراج {is_question, items:[{name_ar, grams}]}.

    - لا يحسب أي سعرات (التسعير محليًا في الراوتر).
    - يرجّع None عند أي خطأ أو لو الـ AI متعطّل (الراوتر يرجع للـ heuristic).
    """
    if not settings.ai_enabled:
        return None
    raw = _generate(
        f"النص: «{text}»\nاستخرج الأكلات والجرامات أو علّمه كسؤال. رُدّ بـ JSON فقط.",
        max_tokens=600,
        temperature=0.1,
        system=_PARSE_SYSTEM,
    )
    if not raw:
        return None
    try:
        cleaned = _strip_json_fences(raw)
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            return None
        is_question = bool(data.get("is_question", False))
        raw_items = data.get("items") or []
        if not isinstance(raw_items, list):
            return None
        items: list[dict] = []
        for it in raw_items:
            if not isinstance(it, dict):
                return None
            name = it.get("name_ar")
            grams = it.get("grams")
            if not isinstance(name, str) or not name.strip():
                continue
            if not isinstance(grams, (int, float)) or isinstance(grams, bool):
                continue
            grams = float(grams)
            if grams <= 0:
                continue
            items.append({"name_ar": name.strip(), "grams": grams})
        return {"is_question": is_question, "items": items}
    except Exception:
        logger.exception("فشل تحليل رد Gemini كـ JSON")
        return None
