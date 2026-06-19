"""اختبارات تسجيل الأكل والمكتبة والتقدير والاقتراحات."""
from datetime import date

import app.routers.foods as foods_router
from app.config import settings
from app.models.food import FoodLibrary
from app.routers.foods import _match_library
from tests.conftest import auth_headers

TODAY = "2026-06-17"


def _seed_lib(db):
    db.add_all([
        FoodLibrary(name_ar="رز أبيض مطبوخ", calories_per_100=130, protein=2.7, carbs=28, fat=0.3, region="generic"),
        FoodLibrary(name_ar="صدر دجاج مشوي", calories_per_100=165, protein=31, carbs=0, fat=3.6, region="generic"),
        FoodLibrary(name_ar="كشري", calories_per_100=150, protein=5, carbs=28, fat=2.5, region="eg"),
        # العطل القديم: «نص رغيف عيش» كان بيتطابق مع ساندويتش فلافل بالعيش (اسم أطول بكتير)
        FoodLibrary(name_ar="ساندويتش فلافل بالعيش", calories_per_100=290, protein=8, carbs=35, fat=12, region="eg"),
        FoodLibrary(name_ar="عيش بلدي", calories_per_100=250, protein=8, carbs=50, fat=1.5, region="eg"),
    ])
    db.commit()


def test_add_list_update_delete_food(client):
    h = auth_headers(client, "fu1")
    payload = {
        "date": TODAY, "meal": "lunch", "name_ar": "رز", "amount": 200,
        "calories": 260, "protein": 5.4, "carbs": 56, "fat": 0.6, "source": "manual",
    }
    r = client.post("/foods", json=payload, headers=h)
    assert r.status_code == 201, r.text
    fid = r.json()["id"]

    r = client.get(f"/foods?on={TODAY}", headers=h)
    assert r.status_code == 200 and len(r.json()) == 1

    # تعديل الرقم يدوياً
    r = client.put(f"/foods/{fid}", json={"calories": 300}, headers=h)
    assert r.status_code == 200 and r.json()["calories"] == 300

    r = client.delete(f"/foods/{fid}", headers=h)
    assert r.status_code == 204
    r = client.get(f"/foods?on={TODAY}", headers=h)
    assert len(r.json()) == 0


def test_library_search(client, db_session):
    _seed_lib(db_session)
    h = auth_headers(client, "fu2")
    r = client.get("/foods/library/search?q=دجاج", headers=h)
    assert r.status_code == 200
    names = [x["name_ar"] for x in r.json()]
    assert any("دجاج" in n for n in names)


def test_estimate_uses_library_when_match(client, db_session):
    _seed_lib(db_session)
    h = auth_headers(client, "fu3")
    r = client.get("/foods/estimate?name=كشري&amount=350", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "library"
    assert body["calories"] == round(150 * 3.5)


def test_estimate_falls_back_to_heuristic(client, db_session):
    _seed_lib(db_session)
    h = auth_headers(client, "fu4")
    r = client.get("/foods/estimate?name=وجبة غريبة جدا&amount=100", headers=h)
    assert r.status_code == 200
    assert r.json()["source"] == "estimated"
    assert r.json()["calories"] > 0


def test_suggest_returns_library(client, db_session):
    _seed_lib(db_session)
    h = auth_headers(client, "fu5")
    r = client.get("/foods/suggest?q=رز", headers=h)
    assert r.status_code == 200
    assert any(s["kind"] == "library" for s in r.json())


def test_label_parse_endpoint(client):
    h = auth_headers(client, "fu6")
    text = "لكل 100 جرام\nسعرات حرارية 200\nبروتين 10\nكربوهيدرات 25\nدهون 6"
    r = client.post("/foods/label", data={"text": text}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["calories"] == 200


def test_foods_require_auth(client):
    r = client.get("/foods")
    assert r.status_code == 401


def test_parse_meal_understands_and_splits_meals(client, db_session):
    _seed_lib(db_session)
    h = auth_headers(client, "fp1")
    r = client.post("/foods/parse", json={"text": "بيضتين وكوباية لبن وعلى الغدا طبق رز"}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) >= 2
    meals = {i["meal"] for i in body["items"]}
    assert "lunch" in meals  # "رز" اتحط على الغدا
    assert body["logged"] is False
    assert body["total_calories"] > 0
    assert body["reply_ar"]


def test_parse_meal_confirm_logs_to_day(client, db_session):
    _seed_lib(db_session)
    h = auth_headers(client, "fp2")
    today = date.today().isoformat()
    r = client.post(
        "/foods/parse",
        json={"text": "طبق رز", "date": today, "default_meal": "lunch", "confirm": True},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["logged"] is True
    assert len(r.json()["logged_ids"]) >= 1
    logs = client.get(f"/foods?on={today}", headers=h).json()
    assert any("رز" in l["name_ar"] for l in logs)


def test_parse_meal_requires_auth(client):
    assert client.post("/foods/parse", json={"text": "تفاحة"}).status_code == 401


# ---------- مطابقة المكتبة المحكمة (إصلاح التطابق الجزئي الخاطئ) ----------
def test_match_library_short_query_does_not_match_longer_unrelated(db_session):
    """«نص رغيف عيش» المفروض ما يتطابقش مع «ساندويتش فلافل بالعيش» (أطول بكتير)."""
    _seed_lib(db_session)
    match = _match_library(db_session, "نص رغيف عيش")
    if match is not None:
        assert "فلافل" not in match.name_ar


def test_match_library_prefers_exact_then_prefix(db_session):
    _seed_lib(db_session)
    # تطابق تام
    assert _match_library(db_session, "كشري").name_ar == "كشري"
    # «عيش» القصيرة تفضّل «عيش بلدي» (تبدأ بالاستعلام) على ساندويتش الفلافل الأطول
    m = _match_library(db_session, "عيش")
    assert m is not None and m.name_ar == "عيش بلدي"


def test_match_library_none_for_unknown(db_session):
    _seed_lib(db_session)
    assert _match_library(db_session, "كافيار بلوجا فاخر") is None


def test_estimate_short_query_not_matched_to_long_falafel(client, db_session):
    """عبر الـ API: «نص رغيف عيش» ما يطلّعش سعرات ساندويتش الفلافل."""
    _seed_lib(db_session)
    h = auth_headers(client, "fmatch1")
    r = client.get("/foods/estimate?name=نص رغيف عيش&amount=45", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    # لو طابق المكتبة لازم ما يكونش الفلافل؛ لو ما طابقش بيرجع تقدير
    assert "فلافل" not in body["name_ar"]


def test_estimate_cucumber_not_160(client, db_session):
    """عبر الـ API بدون AI: «خيارة» مش بتطلّع ~160 سعرة زي العطل القديم."""
    _seed_lib(db_session)
    h = auth_headers(client, "fmatch2")
    r = client.get("/foods/estimate?name=خيارة&amount=100", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "estimated"
    assert body["calories"] < 60


def test_parse_uses_ai_kcal_per_100_when_no_library_match(client, db_session, monkeypatch):
    """صنف من الـ AI بدون تطابق مكتبة → نسعّره بـ kcal_per_100 من الـ AI مش بالمقدّر الغبي."""
    _seed_lib(db_session)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        foods_router.ai_assistant,
        "parse_meal_ai",
        lambda text: {
            "is_question": False,
            "items": [{"name_ar": "خيار", "grams": 100, "kcal_per_100": 15}],
        },
    )
    monkeypatch.setattr(foods_router.ai_assistant, "meal_reply", lambda *a, **k: None)
    h = auth_headers(client, "faikcal")
    r = client.post("/foods/parse", json={"text": "اكلت خيار"}, headers=h)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 1
    # 15 سعرة/100جم * 100جم = 15 (مش 120 الافتراضي ولا 160 القديم)
    assert items[0]["calories"] == 15


def test_parse_ai_item_prefers_confident_library_over_ai_kcal(client, db_session, monkeypatch):
    """لو فيه تطابق مكتبة واثق نستخدم سعرات المكتبة حتى لو الـ AI بعت kcal_per_100."""
    _seed_lib(db_session)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        foods_router.ai_assistant,
        "parse_meal_ai",
        lambda text: {
            "is_question": False,
            "items": [{"name_ar": "كشري", "grams": 100, "kcal_per_100": 999}],
        },
    )
    monkeypatch.setattr(foods_router.ai_assistant, "meal_reply", lambda *a, **k: None)
    h = auth_headers(client, "failib")
    r = client.post("/foods/parse", json={"text": "اكلت كشري"}, headers=h)
    assert r.status_code == 200, r.text
    item = r.json()["items"][0]
    assert item["source"] == "library"
    assert item["calories"] == 150  # من المكتبة مش 999 من الـ AI
