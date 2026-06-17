"""اختبارات تسجيل الأكل والمكتبة والتقدير والاقتراحات."""
from app.models.food import FoodLibrary
from tests.conftest import auth_headers

TODAY = "2026-06-17"


def _seed_lib(db):
    db.add_all([
        FoodLibrary(name_ar="رز أبيض مطبوخ", calories_per_100=130, protein=2.7, carbs=28, fat=0.3, region="generic"),
        FoodLibrary(name_ar="صدر دجاج مشوي", calories_per_100=165, protein=31, carbs=0, fat=3.6, region="generic"),
        FoodLibrary(name_ar="كشري", calories_per_100=150, protein=5, carbs=28, fat=2.5, region="eg"),
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
