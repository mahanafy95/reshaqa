"""مساعد صحي بالذكاء الاصطناعي عبر مزوّدات مجانية (Gemini أو OpenRouter).

يضيف طبقة محادثة ودّية فوق المحلّل المحلي:
- حساب السعرات يفضل **محسوبًا محليًا من قاعدة بياناتنا** (مش من الـ LLM) — أدق وأأمن.
- الـ LLM بيدّي ردّ محادثة ودّي ويجاوب أسئلة صحية عامة، ولو لزم يقدّر سعرات صنف غير معروف.

ترتيب المزوّدات (أول نص غير فارغ يفوز):
  1) Gemini مباشرة (GEMINI_API_KEY + GEMINI_MODEL).
  2) OpenRouter (OPENROUTER_API_KEY) — يجرّب كل موديل مجاني في القائمة بالترتيب.

يتعطّل بهدوء (يرجّع None) لو المفاتيح مش مضبوطة أو حصل أي خطأ — والراوتر يرجع للرد المحلي.
كل المسارات لا ترفع استثناء أبداً لمسار الطلب.
"""
import json
import logging
import re

import httpx

from ..config import settings

logger = logging.getLogger("reshaqa.ai")

_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_SYSTEM = (
    "إنت مساعد تغذية وصحة ودود لتطبيق 'رشاقة'، بتتكلم بالعامية المصرية وباختصار. "
    "بتساعد المستخدم في أكله ووزنه وعاداته الصحية بنبرة مشجّعة وغير حاكمة. "
    "ماتديش تشخيص أو علاج طبي — لو سأل عن حاجة طبية انصحه يستشير مختص. "
    "خلّي ردّك قصير (جملتين-تلاتة)."
)


# ---------- مزوّد Gemini المباشر ----------
def _gemini_complete(
    prompt: str, system: str | None, *, max_tokens: int, temperature: float
) -> str | None:
    if not settings.GEMINI_API_KEY.strip():
        return None
    url = _GEMINI_URL.format(model=settings.GEMINI_MODEL)
    try:
        resp = httpx.post(
            url,
            params={"key": settings.GEMINI_API_KEY},
            json={
                "system_instruction": {"parts": [{"text": system or _SYSTEM}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
            },
            timeout=25.0,
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


# ---------- مزوّد OpenRouter (متوافق مع OpenAI) ----------
def _openrouter_complete(
    prompt: str, system: str | None, *, max_tokens: int, temperature: float
) -> str | None:
    api_key = settings.OPENROUTER_API_KEY.strip()
    if not api_key:
        return None
    messages = [
        {"role": "system", "content": system or _SYSTEM},
        {"role": "user", "content": prompt},
    ]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://reshaqa.app",
        "X-Title": "Reshaqa",
    }
    # نجرّب كل موديل مجاني بالترتيب؛ لو رجّع خطأ أو نص فارغ ننتقل للي بعده.
    for model in settings.openrouter_models_list:
        try:
            resp = httpx.post(
                _OPENROUTER_URL,
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=25.0,
            )
            if resp.status_code != 200:
                logger.warning(
                    "OpenRouter (%s) رجّع %s: %s", model, resp.status_code, resp.text[:200]
                )
                continue
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                continue
            message = choices[0].get("message") or {}
            text = (message.get("content") or "").strip()
            if text:
                return text
        except Exception:
            logger.exception("فشل نداء OpenRouter (%s)", model)
            continue
    return None


def ai_complete(
    prompt: str,
    system: str | None = None,
    *,
    max_tokens: int = 512,
    temperature: float = 0.3,
) -> str | None:
    """يجرّب المزوّدات بالترتيب ويرجّع أول نص غير فارغ، وإلا None.

    الترتيب: Gemini المباشر ثم OpenRouter (كل موديل مجاني بالترتيب).
    لا يرفع استثناء أبداً — كل مزوّد يتعطّل بهدوء.
    """
    if not settings.ai_enabled:
        return None
    text = _gemini_complete(prompt, system, max_tokens=max_tokens, temperature=temperature)
    if text:
        return text
    return _openrouter_complete(prompt, system, max_tokens=max_tokens, temperature=temperature)


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
    return ai_complete(prompt, max_tokens=320, temperature=0.4)


def general_reply(user_text: str) -> str | None:
    """ردّ على سؤال صحي/تغذوي عام (مش تسجيل وجبة)."""
    return ai_complete(
        f"المستخدم سأل: «{user_text}»\nجاوبه باختصار ونبرة مشجّعة.",
        max_tokens=320,
        temperature=0.4,
    )


# ---------- أدوات JSON ----------
def _strip_json_fences(text: str) -> str:
    t = text.strip()
    # شيل ```json ... ``` لو موجودة (سطر أول/أخير أو inline)
    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


def _coerce_number(value, *, min_value: float | None = None) -> float | None:
    """يحوّل قيمة لرقم موجب آمن، أو None لو مش رقم صالح (يرفض bool)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    num = float(value)
    if min_value is not None and num < min_value:
        return None
    return num


# ---------- استخراج الوجبة بالذكاء الاصطناعي (الأسماء + الجرامات + تقدير السعرات/100جم) ----------
_PARSE_SYSTEM = (
    "إنت محلّل وجبات لتطبيق تغذية مصري. مهمتك تستخرج الأكلات اللي قال المستخدم إنه أكلها "
    "من كلام بالعامية المصرية، وتقدّر وزن كل صنف بالجرام بشكل واقعي، "
    "وتقدّر السعرات الحرارية لكل 100 جرام من الصنف بشكل واقعي. "
    "لو النص سؤال أو طلب (مش تسجيل أكل فعلي)، حُطّ is_question=true وخلّي items فاضية. "
    "رُدّ بـ JSON فقط بدون أي شرح، بالشكل ده بالظبط: "
    '{"is_question": false, "items": [{"name_ar": "اسم الأكلة بالعربي", "grams": رقم, '
    '"kcal_per_100": رقم}]}'
)


def parse_meal_ai(text: str) -> dict | None:
    """يطلب من الـ LLM استخراج {is_question, items:[{name_ar, grams, kcal_per_100}]}.

    - kcal_per_100 = تقدير الـ AI الواقعي للسعرات لكل 100 جرام من الصنف.
    - is_question=true مع items فاضية للأسئلة/الطلبات.
    - يرجّع None عند أي خطأ أو لو الـ AI متعطّل (الراوتر يرجع للـ heuristic).
    """
    if not settings.ai_enabled:
        return None
    raw = ai_complete(
        f"النص: «{text}»\n"
        "استخرج الأكلات والجرامات وقدّر السعرات لكل 100 جرام، أو علّمه كسؤال. رُدّ بـ JSON فقط.",
        system=_PARSE_SYSTEM,
        max_tokens=600,
        temperature=0.1,
    )
    if not raw:
        return None
    try:
        data = json.loads(_strip_json_fences(raw))
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
            if not isinstance(name, str) or not name.strip():
                continue
            grams = _coerce_number(it.get("grams"), min_value=None)
            if grams is None or grams <= 0:
                continue
            kcal = _coerce_number(it.get("kcal_per_100"), min_value=0)
            if kcal is None:
                kcal = 0.0
            items.append(
                {"name_ar": name.strip(), "grams": grams, "kcal_per_100": kcal}
            )
        return {"is_question": is_question, "items": items}
    except Exception:
        logger.exception("فشل تحليل رد الـ AI كـ JSON")
        return None


# ---------- تقدير سعرات صنف غير معروف (لكل 100 جرام) ----------
_ESTIMATE_SYSTEM = (
    "إنت خبير تغذية. قدّر القيم الغذائية الواقعية لكل 100 جرام من الأكلة المذكورة. "
    "رُدّ بـ JSON فقط بدون أي شرح، بالشكل ده بالظبط: "
    '{"kcal_per_100": رقم, "protein": رقم, "carbs": رقم, "fat": رقم} '
    "(القيم لكل 100 جرام: السعرات بالكيلوكالوري، والبروتين والكارب والدهون بالجرام)."
)


def estimate_calories_ai(name_ar: str, grams: float) -> dict | None:
    """يقدّر القيم الغذائية لكل 100 جرام لصنف غير معروف.

    يرجّع {"kcal_per_100", "protein", "carbs", "fat"} (أرقام لكل 100 جرام)، أو None عند أي فشل.
    """
    if not settings.ai_enabled:
        return None
    raw = ai_complete(
        f"الأكلة: «{name_ar}» (الكمية المسجَّلة {grams} جرام). "
        "قدّر القيم الغذائية لكل 100 جرام. رُدّ بـ JSON فقط.",
        system=_ESTIMATE_SYSTEM,
        max_tokens=200,
        temperature=0.1,
    )
    if not raw:
        return None
    try:
        data = json.loads(_strip_json_fences(raw))
        if not isinstance(data, dict):
            return None
        kcal = _coerce_number(data.get("kcal_per_100"), min_value=0)
        if kcal is None:
            return None
        protein = _coerce_number(data.get("protein"), min_value=0) or 0.0
        carbs = _coerce_number(data.get("carbs"), min_value=0) or 0.0
        fat = _coerce_number(data.get("fat"), min_value=0) or 0.0
        return {
            "kcal_per_100": kcal,
            "protein": protein,
            "carbs": carbs,
            "fat": fat,
        }
    except Exception:
        logger.exception("فشل تحليل رد تقدير السعرات كـ JSON")
        return None
