"""اختبارات المفضّلة — إنشاء، تسجيل سريع، وعزل."""
from app.models.food import FoodLibrary
from tests.conftest import auth_headers

TODAY = "2026-06-17"


def test_custom_favorite_create_log_delete(client):
    h = auth_headers(client, "fav1")
    fav = {"ref_type": "custom", "name_ar": "قهوتي بسكر", "default_amount": 200,
           "calories": 60, "protein": 1, "carbs": 14, "fat": 0}
    r = client.post("/favorites", json=fav, headers=h)
    assert r.status_code == 201, r.text
    fid = r.json()["id"]

    r = client.get("/favorites", headers=h)
    assert len(r.json()) == 1

    # تسجيل سريع
    r = client.post(f"/favorites/{fid}/log", json={"date": TODAY, "meal": "snack"}, headers=h)
    assert r.status_code == 201
    assert r.json()["calories"] == 60

    r = client.delete(f"/favorites/{fid}", headers=h)
    assert r.status_code == 204


def test_favorite_from_library(client, db_session):
    db_session.add(FoodLibrary(name_ar="تمر", calories_per_100=282, protein=2.5, carbs=75, fat=0.4, region="generic"))
    db_session.commit()
    lib = db_session.query(FoodLibrary).filter_by(name_ar="تمر").first()
    h = auth_headers(client, "fav2")
    r = client.post("/favorites", json={"ref_type": "library", "library_id": lib.id, "default_amount": 24}, headers=h)
    assert r.status_code == 201, r.text
    # 24 جم تمر ≈ 68 سعرة
    assert abs(r.json()["calories"] - round(282 * 0.24)) <= 1


def test_favorite_isolation(client):
    ha = auth_headers(client, "fav3")
    hb = auth_headers(client, "fav4")
    fav = {"ref_type": "custom", "name_ar": "X", "default_amount": 100, "calories": 50}
    fid = client.post("/favorites", json=fav, headers=ha).json()["id"]
    # bob يحاول حذف مفضّلة alice
    r = client.delete(f"/favorites/{fid}", headers=hb)
    assert r.status_code == 404
    # bob قائمته فاضية
    assert client.get("/favorites", headers=hb).json() == []
