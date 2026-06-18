"""مساعد صحي بالذكاء الاصطناعي عبر Google Gemini (الباقة المجانية).

يضيف طبقة محادثة ودّية فوق المحلّل المحلي:
- حساب السعرات يفضل **محسوبًا محليًا من قاعدة بياناتنا** (مش من الـ LLM) — أدق وأأمن.
- Gemini بيدّي ردّ محادثة ودّي ويجاوب أسئلة صحية عامة.
يتعطّل بهدوء لو المفتاح مش مضبوط أو حصل خطأ (نرجع للرد المحلي).
"""
import logging

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


def _generate(prompt: str, *, max_tokens: int = 320, temperature: float = 0.4) -> str | None:
    if not settings.ai_enabled:
        return None
    url = _URL.format(model=settings.GEMINI_MODEL)
    try:
        resp = httpx.post(
            url,
            params={"key": settings.GEMINI_API_KEY},
            json={
                "system_instruction": {"parts": [{"text": _SYSTEM}]},
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
