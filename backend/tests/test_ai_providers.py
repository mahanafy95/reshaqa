"""اختبارات طبقة المزوّدات (Gemini + OpenRouter) ودوال العقد — كلها بمحاكاة httpx (بدون شبكة)."""
import json

import httpx

import app.services.ai_assistant as ai
from app.config import settings


class _Resp:
    """ردّ httpx مزيّف بسيط."""

    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or json.dumps(self._payload)

    def json(self):
        return self._payload


def _gemini_ok(text: str) -> _Resp:
    return _Resp(200, {"candidates": [{"content": {"parts": [{"text": text}]}}]})


def _openrouter_ok(text: str) -> _Resp:
    return _Resp(200, {"choices": [{"message": {"content": text}}]})


# ---------- ai_enabled / config ----------
def test_ai_enabled_with_only_openrouter(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    assert settings.ai_enabled is True


def test_ai_enabled_false_when_both_empty(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    assert settings.ai_enabled is False


def test_openrouter_models_list_trims_and_drops_empty(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_MODELS", " a/model:free , , b/model:free ,")
    assert settings.openrouter_models_list == ["a/model:free", "b/model:free"]


def test_default_openrouter_models_empty_means_autodiscover():
    """الافتراضي فاضي = نكتشف الموديلات المجانية المتاحة لحظياً (يتداوى ذاتياً)."""
    assert settings.openrouter_models_list == []


def test_openrouter_models_uses_explicit_list_when_set(monkeypatch):
    """لو البيئة عيّنت موديلات صراحةً نستخدمها بدل الاكتشاف التلقائي."""
    monkeypatch.setattr(settings, "OPENROUTER_MODELS", "x/m:free,y/m:free")
    assert ai._openrouter_models() == ["x/m:free", "y/m:free"]


def test_discover_free_models_ranks_and_filters(monkeypatch):
    """الاكتشاف يفلتر :free ويستبعد المتخصّص ويرتّب موديلات المحادثة القوية أولاً."""
    ai._openrouter_models_cache = None
    payload = {
        "data": [
            {"id": "openai/gpt-4o"},                                   # مش :free
            {"id": "nvidia/nemotron-content-safety:free"},             # متخصّص → يُستبعد
            {"id": "some/image-gen:free", "architecture": {"output_modalities": ["image"]}},
            {"id": "qwen/qwen3-coder:free"},                           # code → يُستبعد
            {"id": "meta-llama/llama-3.3-70b-instruct:free"},
            {"id": "google/gemma-4-31b-it:free"},
        ]
    }
    monkeypatch.setattr(ai.httpx, "get", lambda *a, **k: _Resp(200, payload))
    out = ai._discover_free_models()
    assert out == ["meta-llama/llama-3.3-70b-instruct:free", "google/gemma-4-31b-it:free"]


def test_discover_free_models_falls_back_on_network_error(monkeypatch):
    """لو تعذّر جلب القائمة الحيّة → نرجع للقائمة الاحتياطية المحدّثة (مش فاضية)."""
    ai._openrouter_models_cache = None

    def boom(*a, **k):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(ai.httpx, "get", boom)
    out = ai._discover_free_models()
    assert out == ai._OPENROUTER_FALLBACK
    assert out and all(m.endswith(":free") for m in out)


# ---------- ai_complete: ترتيب المزوّدات ----------
def test_ai_complete_returns_none_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    assert ai.ai_complete("اهلا") is None


def test_ai_complete_prefers_gemini(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "g-key")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")

    def fake_post(url, **kwargs):
        assert "generativelanguage" in url  # ما نوصلش لـ OpenRouter أصلاً
        return _gemini_ok("رد من Gemini")

    monkeypatch.setattr(httpx, "post", fake_post)
    assert ai.ai_complete("سؤال") == "رد من Gemini"


def test_ai_complete_falls_back_to_openrouter(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "g-key")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    monkeypatch.setattr(settings, "OPENROUTER_MODELS", "a/m:free")  # تخطّي الاكتشاف (بلا شبكة)

    def fake_post(url, **kwargs):
        if "generativelanguage" in url:
            return _Resp(500, text="gemini down")
        return _openrouter_ok("رد من OpenRouter")

    monkeypatch.setattr(httpx, "post", fake_post)
    assert ai.ai_complete("سؤال") == "رد من OpenRouter"


def test_ai_complete_openrouter_tries_next_model_on_error(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    monkeypatch.setattr(settings, "OPENROUTER_MODELS", "first/model:free,second/model:free")
    seen: list[str] = []

    def fake_post(url, **kwargs):
        model = kwargs["json"]["model"]
        seen.append(model)
        if model == "first/model:free":
            return _Resp(429, text="rate limited")  # الموديل الأول فشل
        return _openrouter_ok("نجح التاني")

    monkeypatch.setattr(httpx, "post", fake_post)
    assert ai.ai_complete("سؤال") == "نجح التاني"
    assert seen == ["first/model:free", "second/model:free"]


def test_ai_complete_returns_none_when_all_fail(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "g-key")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    monkeypatch.setattr(settings, "OPENROUTER_MODELS", "a/m:free")

    def fake_post(url, **kwargs):
        return _Resp(500, text="boom")

    monkeypatch.setattr(httpx, "post", fake_post)
    assert ai.ai_complete("سؤال") is None


def test_ai_complete_never_raises_on_network_error(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "g-key")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    monkeypatch.setattr(settings, "OPENROUTER_MODELS", "a/m:free")

    def boom(url, **kwargs):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(httpx, "post", boom)
    assert ai.ai_complete("سؤال") is None  # تتعطّل بهدوء


def test_openrouter_sends_bearer_and_messages(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "secret-key")
    monkeypatch.setattr(settings, "OPENROUTER_MODELS", "a/m:free")
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["body"] = kwargs["json"]
        return _openrouter_ok("ok")

    monkeypatch.setattr(httpx, "post", fake_post)
    ai.ai_complete("مرحبا", system="نظام", max_tokens=99, temperature=0.7)
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer secret-key"
    body = captured["body"]
    assert body["model"] == "a/m:free"
    assert body["max_tokens"] == 99
    assert body["temperature"] == 0.7
    assert body["messages"][0] == {"role": "system", "content": "نظام"}
    assert body["messages"][1] == {"role": "user", "content": "مرحبا"}


# ---------- meal_reply / general_reply يمرّوا عبر ai_complete ----------
def test_meal_reply_routes_through_ai_complete(monkeypatch):
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: "تمام يا بطل 💪")
    assert ai.meal_reply("بيضتين", "بيض 100جم", 150, True) == "تمام يا بطل 💪"


def test_general_reply_routes_through_ai_complete(monkeypatch):
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: "اشرب مية 💧")
    assert ai.general_reply("ازاي اخس؟") == "اشرب مية 💧"


# ---------- parse_meal_ai ----------
def test_parse_meal_ai_none_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    assert ai.parse_meal_ai("بيضتين") is None


def test_parse_meal_ai_extracts_items_with_kcal(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    payload = {
        "is_question": False,
        "items": [{"name_ar": "بيض", "grams": 100, "kcal_per_100": 155}],
    }
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: json.dumps(payload))
    out = ai.parse_meal_ai("اكلت بيضتين")
    assert out == {
        "is_question": False,
        "items": [{"name_ar": "بيض", "grams": 100.0, "kcal_per_100": 155.0}],
    }


def test_parse_meal_ai_strips_code_fences(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    fenced = '```json\n{"is_question": true, "items": []}\n```'
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: fenced)
    out = ai.parse_meal_ai("ازاي اخس؟")
    assert out == {"is_question": True, "items": []}


def test_parse_meal_ai_skips_invalid_items(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    payload = {
        "is_question": False,
        "items": [
            {"name_ar": "", "grams": 100, "kcal_per_100": 50},          # اسم فاضي
            {"name_ar": "رز", "grams": 0, "kcal_per_100": 130},          # جرامات صفر
            {"name_ar": "فراخ", "grams": True, "kcal_per_100": 200},     # bool مش رقم
            {"name_ar": "موز", "grams": 120, "kcal_per_100": 89},        # صالح
        ],
    }
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: json.dumps(payload))
    out = ai.parse_meal_ai("اكل")
    assert out["items"] == [{"name_ar": "موز", "grams": 120.0, "kcal_per_100": 89.0}]


def test_parse_meal_ai_defaults_kcal_to_zero_when_missing(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    payload = {"is_question": False, "items": [{"name_ar": "حاجة", "grams": 100}]}
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: json.dumps(payload))
    out = ai.parse_meal_ai("اكل")
    assert out["items"] == [{"name_ar": "حاجة", "grams": 100.0, "kcal_per_100": 0.0}]


def test_parse_meal_ai_none_on_bad_json(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: "مش JSON خالص")
    assert ai.parse_meal_ai("اكل") is None


def test_parse_meal_ai_none_when_ai_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: None)
    assert ai.parse_meal_ai("اكل") is None


# ---------- estimate_calories_ai ----------
def test_estimate_calories_ai_none_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    assert ai.estimate_calories_ai("منسف", 300) is None


def test_estimate_calories_ai_parses_macros(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    payload = {"kcal_per_100": 180, "protein": 9, "carbs": 20, "fat": 7}
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: json.dumps(payload))
    out = ai.estimate_calories_ai("منسف", 300)
    assert out == {"kcal_per_100": 180.0, "protein": 9.0, "carbs": 20.0, "fat": 7.0}


def test_estimate_calories_ai_defaults_missing_macros_to_zero(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    payload = {"kcal_per_100": 200}
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: json.dumps(payload))
    out = ai.estimate_calories_ai("صنف", 100)
    assert out == {"kcal_per_100": 200.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}


def test_estimate_calories_ai_none_without_kcal(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    payload = {"protein": 9, "carbs": 20, "fat": 7}  # مفيش kcal_per_100
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: json.dumps(payload))
    assert ai.estimate_calories_ai("صنف", 100) is None


def test_estimate_calories_ai_none_on_bad_json(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: "لا شيء")
    assert ai.estimate_calories_ai("صنف", 100) is None
