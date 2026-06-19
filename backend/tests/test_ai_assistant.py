"""اختبارات طبقة المساعد الذكي (Gemini) فوق محلّل الوجبات — مع محاكاة (بدون شبكة)."""
import app.routers.foods as foods_router
from app.config import settings
from app.services.meal_parser import looks_like_question
from tests.conftest import auth_headers


# ---------- كشف الأسئلة (heuristic، بدون شبكة) ----------
def test_looks_like_question_true_for_questions():
    assert looks_like_question("عايز اعرف اكل ايه عشان ازيد وزني؟") is True
    assert looks_like_question("ازاي اخس؟") is True


def test_looks_like_question_false_for_real_meal():
    assert looks_like_question("اكلت بيضتين وعيش بلدي") is False


def test_looks_like_question_question_mark_only():
    assert looks_like_question("كشري") is False
    assert looks_like_question("كشري؟") is True


# ---------- كشف نيّة التسجيل wants_to_log (heuristic، بدون شبكة) ----------
def test_wants_to_log_true_for_add_commands():
    from app.services.meal_parser import wants_to_log

    assert wants_to_log("ضيفهم") is True
    assert wants_to_log("ايوه ضيف كله") is True
    assert wants_to_log("سجّلهم في الغدا") is True   # مع تشكيل
    assert wants_to_log("اكتبهم عندي") is True
    assert wants_to_log("أضفهم لليوم") is True


def test_wants_to_log_false_for_normal_chat():
    from app.services.meal_parser import wants_to_log

    assert wants_to_log("ايه أحسن أكل للعشا؟") is False
    assert wants_to_log("نفسي اخس ٥ كيلو") is False
    assert wants_to_log("كشري وفراخ") is False
    assert wants_to_log("") is False


# ---------- المسار بدون AI (الافتراضي في الاختبارات) ----------
def test_parse_question_returns_empty_items_and_reply_no_ai(client):
    """سؤال بدون AI → لا أصناف ملفّقة، ورد ودّي غير فارغ."""
    h = auth_headers(client, "q_no_ai")
    r = client.post(
        "/foods/parse",
        json={"text": "ازاي اخس؟", "default_meal": "snack", "confirm": False},
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items"] == []
    assert body["total_calories"] == 0
    assert body["logged"] is False
    assert body["reply_ar"]  # غير فارغ


def test_parse_real_meal_still_returns_items_no_ai(client):
    """وجبة حقيقية بدون AI → أصناف وسعرات زي الأول."""
    h = auth_headers(client, "meal_no_ai")
    r = client.post(
        "/foods/parse",
        json={"text": "اكلت بيضتين وعيش بلدي", "default_meal": "breakfast", "confirm": False},
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) >= 1
    assert body["total_calories"] > 0


# ---------- المسار مع AI مفعّل (مع محاكاة parse_meal_ai — بدون شبكة) ----------
def test_parse_uses_ai_items_and_reply_when_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")  # ai_enabled = True
    monkeypatch.setattr(
        foods_router.ai_assistant,
        "parse_meal_ai",
        lambda text: {"is_question": False, "items": [{"name_ar": "بيض", "grams": 100}]},
    )
    h = auth_headers(client, "aiuser")
    r = client.post(
        "/foods/parse",
        json={"text": "النهاردة فطرت بيضتين", "default_meal": "breakfast", "confirm": False},
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # ردّ ملخّص محلي (وفّرنا نداء AI الإضافي) — يحتوي على الصنف المُحلَّل
    assert body["reply_ar"] and "بيض" in body["reply_ar"]
    # السعرات لسه محسوبة محليًا (مش من الـ LLM)
    assert len(body["items"]) >= 1
    assert body["total_calories"] > 0


def test_parse_ai_question_returns_general_reply(client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        foods_router.ai_assistant,
        "parse_meal_ai",
        lambda text: {"is_question": True, "items": []},
    )
    monkeypatch.setattr(foods_router.ai_assistant, "general_reply", lambda t: "اشرب مية كفاية 💧")
    h = auth_headers(client, "aiuser_q")
    r = client.post(
        "/foods/parse",
        json={"text": "ازاي ازيد وزني؟", "default_meal": "snack", "confirm": False},
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items"] == []
    assert body["total_calories"] == 0
    assert body["reply_ar"] == "اشرب مية كفاية 💧"


def test_parse_ai_failure_falls_back_to_heuristic(client, monkeypatch):
    """لو الـ AI رجّع None → نرجع للـ heuristic ونطلّع أصناف."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(foods_router.ai_assistant, "parse_meal_ai", lambda text: None)
    monkeypatch.setattr(foods_router.ai_assistant, "meal_reply", lambda *a, **k: None)
    h = auth_headers(client, "aiuser_fb")
    r = client.post(
        "/foods/parse",
        json={"text": "بيضتين وعيش بلدي", "default_meal": "breakfast", "confirm": False},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) >= 1


def test_parse_falls_back_to_heuristic_without_key(client):
    # الافتراضي: مفيش مفتاح → رد محلي عادي (السلوك القديم)
    h = auth_headers(client, "aiuser2")
    r = client.post(
        "/foods/parse",
        json={"text": "النهاردة فطرت بيضتين", "default_meal": "breakfast", "confirm": False},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["reply_ar"] and r.json()["reply_ar"] != "جامد! 💪"
