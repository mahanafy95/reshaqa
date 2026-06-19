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
import base64
import json
import logging
import re
import time

import httpx

from ..config import settings

logger = logging.getLogger("reshaqa.ai")

_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

# ترتيب تفضيل موديلات المحادثة العامة القوية من بين المجانية المتاحة.
_OPENROUTER_PREFER = (
    "llama", "qwen", "deepseek", "gpt-oss", "glm", "mistral", "gemma", "hermes",
)
# موديلات متخصّصة (مش مساعد محادثة عام) نتجاهلها عند الاكتشاف التلقائي.
_OPENROUTER_SKIP = (
    "rerank", "embed", "content-safety", "guard", "moderation", "safety",
    "transcribe", "voice", "tts", "whisper", "ocr", "image", "-vl", "vision", "code",
)
# قائمة احتياطية محدّثة (تُستخدم فقط لو تعذّر جلب القائمة الحيّة من OpenRouter).
_OPENROUTER_FALLBACK = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "openai/gpt-oss-120b:free",
    "google/gemma-4-31b-it:free",
]
_OPENROUTER_MODELS_TTL = 3600.0  # ساعة — نكاشّ القائمة الحيّة عشان منرهقش الـ API.
_openrouter_models_cache: "tuple[float, list[str]] | None" = None


def _discover_free_models() -> list[str]:
    """اجلب الموديلات المجانية المتاحة لحظياً من OpenRouter ورتّبها بالأقوى.

    ده بيخلّي البرنامج 'يتداوى' بنفسه لو OpenRouter غيّر أسماء الموديلات المجانية
    (زي ما حصل: deepseek-v3/qwen-2.5/glm-4.5/gemini-flash-exp اختفوا). كاش لمدة ساعة.
    """
    global _openrouter_models_cache
    now = time.time()
    if _openrouter_models_cache and now - _openrouter_models_cache[0] < _OPENROUTER_MODELS_TTL:
        return _openrouter_models_cache[1]
    try:
        resp = httpx.get(_OPENROUTER_MODELS_URL, timeout=15.0)
        if resp.status_code != 200:
            raise RuntimeError(f"models list {resp.status_code}")
        free: list[str] = []
        for m in resp.json().get("data", []):
            mid = str(m.get("id", ""))
            if not mid.endswith(":free"):
                continue
            low = mid.lower()
            if any(s in low for s in _OPENROUTER_SKIP):
                continue
            arch = m.get("architecture") or {}
            out_mods = arch.get("output_modalities")
            if out_mods and "text" not in out_mods:
                continue
            free.append(mid)

        def _score(mid: str) -> int:
            low = mid.lower()
            for i, p in enumerate(_OPENROUTER_PREFER):
                if p in low:
                    return i
            return len(_OPENROUTER_PREFER)

        free.sort(key=_score)
        result = free[:6] or list(_OPENROUTER_FALLBACK)
        _openrouter_models_cache = (now, result)
        logger.info("موديلات OpenRouter المجانية المكتشَفة: %s", result)
        return result
    except Exception:
        logger.warning("تعذّر جلب موديلات OpenRouter المجانية — استخدام القائمة الاحتياطية", exc_info=True)
        _openrouter_models_cache = (now, list(_OPENROUTER_FALLBACK))
        return list(_OPENROUTER_FALLBACK)


def _openrouter_models() -> list[str]:
    """الموديلات المستخدَمة: قائمة صريحة من البيئة لو موجودة، وإلا اكتشاف تلقائي."""
    explicit = settings.openrouter_models_list
    if explicit:
        return explicit
    return _discover_free_models()

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
    for model in _openrouter_models():
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


# ---------- المساعد الذكي المحادثي (متعدد الأدوار) ----------
# شخصية المساعد الصحي الذكي — محادثة حرة متعددة الأدوار (منفصلة عن تسجيل الوجبات).
_CHAT_SYSTEM = (
    "إنت المساعد الصحي الذكي لتطبيق رشاقة. بتتكلم بالعامية المصرية، ودود ومحفّز "
    "ومختصر-لكن-مفيد. بتساعد المستخدم في الأكل الصحي، التخسيس/الزيادة/التثبيت، الرياضة، "
    "الوصفات، العادات الصحية، وتحفيزه. ممكن تساعده يفهم سعراته. ماتديش تشخيص أو علاج طبي "
    "— لو سأل عن حاجة طبية انصحه يستشير دكتور. لو سأل عن أكلة، اديه سعراتها التقريبية ونصيحة."
)


def _build_chat_system(system_extra: str | None) -> str:
    """يدمج شخصية المساعد مع سياق ملف المستخدم (لو موجود) لتخصيص الرد."""
    base = _CHAT_SYSTEM
    if system_extra and system_extra.strip():
        base = f"{base}\n\nمعلومات عن المستخدم (استعملها لتخصيص ردّك):\n{system_extra.strip()}"
    return base


def _normalize_chat_messages(messages: list[dict]) -> list[dict]:
    """يطبّع المحادثة لقائمة {role, content} نظيفة (الأدوار user/assistant فقط، نص غير فارغ)."""
    out: list[dict] = []
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = m.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        text = content.strip()
        if not text:
            continue
        out.append({"role": role, "content": text})
    return out


def _gemini_chat(
    messages: list[dict], system: str, *, max_tokens: int, temperature: float
) -> str | None:
    """نداء Gemini generateContent متعدد الأدوار (contents[] + system_instruction)."""
    if not settings.GEMINI_API_KEY.strip():
        return None
    url = _GEMINI_URL.format(model=settings.GEMINI_MODEL)
    # نحوّل كل رسالة لشكل Gemini: assistant -> model، user -> user
    contents = [
        {
            "role": "model" if m["role"] == "assistant" else "user",
            "parts": [{"text": m["content"]}],
        }
        for m in messages
    ]
    try:
        resp = httpx.post(
            url,
            params={"key": settings.GEMINI_API_KEY},
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": contents,
                "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
            },
            timeout=25.0,
        )
        if resp.status_code != 200:
            logger.warning("Gemini chat رجّع %s: %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
        return text or None
    except Exception:
        logger.exception("فشل نداء Gemini chat")
        return None


def _openrouter_chat(
    messages: list[dict], system: str, *, max_tokens: int, temperature: float
) -> str | None:
    """نداء OpenRouter chat/completions متعدد الأدوار (system + نفس المحادثة)."""
    api_key = settings.OPENROUTER_API_KEY.strip()
    if not api_key:
        return None
    chat_messages = [{"role": "system", "content": system}]
    chat_messages.extend({"role": m["role"], "content": m["content"]} for m in messages)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://reshaqa.app",
        "X-Title": "Reshaqa",
    }
    for model in _openrouter_models():
        try:
            resp = httpx.post(
                _OPENROUTER_URL,
                headers=headers,
                json={
                    "model": model,
                    "messages": chat_messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=25.0,
            )
            if resp.status_code != 200:
                logger.warning(
                    "OpenRouter chat (%s) رجّع %s: %s", model, resp.status_code, resp.text[:200]
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
            logger.exception("فشل نداء OpenRouter chat (%s)", model)
            continue
    return None


def chat_reply(messages: list[dict], system_extra: str | None = None) -> str | None:
    """ردّ محادثة حرّة متعددة الأدوار للمساعد الصحي الذكي.

    `messages` = آخر أدوار المحادثة [{role: 'user'|'assistant', content: str}, ...]
    وآخر عنصر هو رسالة المستخدم الجديدة. `system_extra` سياق اختياري لتخصيص الرد
    من ملف المستخدم (الهدف/الوزن/...).

    يجرّب Gemini متعدد الأدوار أولاً، وعند فشله/None يرجع لـ OpenRouter بنفس المحادثة.
    يرجّع None لو المساعد متعطّل أو فشل كل المزوّدات (الراوتر يرجع لرد ودّي ثابت).
    لا يرفع استثناء أبداً.
    """
    if not settings.ai_enabled:
        return None
    norm = _normalize_chat_messages(messages)
    if not norm:
        return None
    system = _build_chat_system(system_extra)
    text = _gemini_chat(norm, system, max_tokens=500, temperature=0.6)
    if text:
        return text
    return _openrouter_chat(norm, system, max_tokens=500, temperature=0.6)


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


# ---------- قراءة صورة ملصق التغذية بالرؤية الذكية (Gemini vision) ----------
_LABEL_IMAGE_PROMPT = (
    "You are reading a packaged-food NUTRITION LABEL photo (Arabic or English). "
    'Return ONLY JSON {"calories":num,"protein":num,"carbs":num,"fat":num} as per-100g '
    "values; if a value is missing use 0."
)


def _gemini_read_label_image(image_bytes: bytes, mime: str) -> str | None:
    """ينادي Gemini generateContent بجزء صورة inline (base64) ويرجّع نص الرد الخام، أو None."""
    if not settings.GEMINI_API_KEY.strip():
        return None
    url = _GEMINI_URL.format(model=settings.GEMINI_MODEL)
    try:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        resp = httpx.post(
            url,
            params={"key": settings.GEMINI_API_KEY},
            json={
                "contents": [
                    {
                        "parts": [
                            {"text": _LABEL_IMAGE_PROMPT},
                            {"inline_data": {"mime_type": mime, "data": b64}},
                        ]
                    }
                ],
                "generationConfig": {"temperature": 0.0, "maxOutputTokens": 200},
            },
            timeout=30.0,
        )
        if resp.status_code != 200:
            logger.warning("Gemini vision رجّع %s: %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
        return text or None
    except Exception:
        logger.exception("فشل نداء Gemini vision لقراءة الملصق")
        return None


def read_label_image_ai(image_bytes: bytes, mime: str = "image/jpeg") -> dict | None:
    """يقرأ صورة ملصق تغذية بالرؤية الذكية ويرجّع القيم لكل 100 جرام.

    يرجّع {"calories", "protein", "carbs", "fat"} (أرقام لكل 100 جرام)، أو None لو
    المساعد الذكي متعطّل أو فشل النداء/التحليل. لا يرفع استثناء أبداً لمسار الطلب.
    """
    if not settings.ai_enabled:
        return None
    raw = _gemini_read_label_image(image_bytes, mime)
    if not raw:
        return None
    try:
        data = json.loads(_strip_json_fences(raw))
        if not isinstance(data, dict):
            return None
        return {
            "calories": _coerce_number(data.get("calories"), min_value=0) or 0.0,
            "protein": _coerce_number(data.get("protein"), min_value=0) or 0.0,
            "carbs": _coerce_number(data.get("carbs"), min_value=0) or 0.0,
            "fat": _coerce_number(data.get("fat"), min_value=0) or 0.0,
        }
    except Exception:
        logger.exception("فشل تحليل رد قراءة الملصق كـ JSON")
        return None
