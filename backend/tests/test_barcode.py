"""اختبارات الباركود — المكتبة المحلية أولاً + حفظ منتج جديد (مساهمة)."""
from app.models.food import FoodLibrary
from tests.conftest import auth_headers, make_premium


def test_barcode_local_hit_no_network(client, db_session):
    h = auth_headers(client, "bc1")
    make_premium(db_session, "bc1")
    db_session.add(FoodLibrary(
        name_ar="ريد بُل", barcode="9002490100070",
        calories_per_100=45, protein=0, carbs=11, fat=0,
    ))
    db_session.commit()
    r = client.get("/foods/barcode/9002490100070", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name_ar"] == "ريد بُل"
    assert body["calories_per_100"] == 45
    assert body["source"] == "local"


def test_barcode_save_then_found(client, db_session):
    h = auth_headers(client, "bc2")
    make_premium(db_session, "bc2")
    save = client.post(
        "/foods/barcode",
        json={"barcode": "6221234567890", "name_ar": "مشروب طاقة محلي", "calories_per_100": 50, "carbs": 13},
        headers=h,
    )
    assert save.status_code == 201, save.text
    assert save.json()["source"] == "contributed"
    # المسح التاني يلاقيه محلياً
    r = client.get("/foods/barcode/6221234567890", headers=h).json()
    assert r["name_ar"] == "مشروب طاقة محلي"
    assert r["source"] == "local"


def test_barcode_save_is_upsert(client, db_session):
    h = auth_headers(client, "bc3")
    make_premium(db_session, "bc3")
    client.post("/foods/barcode",
                json={"barcode": "6221000000001", "name_ar": "قديم", "calories_per_100": 10}, headers=h)
    client.post("/foods/barcode",
                json={"barcode": "6221000000001", "name_ar": "محدّث", "calories_per_100": 99}, headers=h)
    r = client.get("/foods/barcode/6221000000001", headers=h).json()
    assert r["name_ar"] == "محدّث" and r["calories_per_100"] == 99


def test_barcode_save_requires_premium(client):
    h = auth_headers(client, "bcfree2")
    r = client.post("/foods/barcode",
                    json={"barcode": "6221000000002", "name_ar": "x", "calories_per_100": 10}, headers=h)
    assert r.status_code == 402


def test_barcode_invalid_code_422(client, db_session):
    h = auth_headers(client, "bc4")
    make_premium(db_session, "bc4")
    assert client.get("/foods/barcode/abc", headers=h).status_code == 422
