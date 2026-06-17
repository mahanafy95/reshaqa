"""اختبارات الوصفات — الحساب، نصيب الفرد، تسجيل النصيب، والعزل."""
from app.models.food import FoodLibrary
from tests.conftest import auth_headers

TODAY = "2026-06-17"

RECIPE = {
    "name_ar": "أرز بالزيت",
    "servings": 2,
    "ingredients": [
        {"name_ar": "رز", "amount_g": 200, "per100_calories": 130, "per100_protein": 2.7,
         "per100_carbs": 28, "per100_fat": 0.3},
        {"name_ar": "زيت", "amount_g": 14, "is_oil": True, "per100_calories": 884,
         "per100_protein": 0, "per100_carbs": 0, "per100_fat": 100},
    ],
}


def test_create_recipe_totals_and_per_serving(client):
    h = auth_headers(client, "ru1")
    r = client.post("/recipes", json=RECIPE, headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    # رز: 260 سعرة، زيت: ~123.8 => الإجمالي ~383.8
    assert abs(body["total_calories"] - 383.8) < 1.0
    assert body["per_serving_calories"] == round(body["total_calories"] / 2)
    # خانة الزيت محفوظة
    oil = [i for i in body["ingredients"] if i["is_oil"]]
    assert len(oil) == 1


def test_recipe_from_library_ingredient(client, db_session):
    db_session.add(FoodLibrary(name_ar="عدس", calories_per_100=115, protein=9, carbs=20, fat=0.4, region="generic"))
    db_session.commit()
    lib = db_session.query(FoodLibrary).filter_by(name_ar="عدس").first()
    h = auth_headers(client, "ru2")
    payload = {"name_ar": "شوربة عدس", "servings": 3,
               "ingredients": [{"library_id": lib.id, "amount_g": 300}]}
    r = client.post("/recipes", json=payload, headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["total_calories"] == round(115 * 3, 1)


def test_log_recipe_portion_scales(client):
    h = auth_headers(client, "ru3")
    rid = client.post("/recipes", json=RECIPE, headers=h).json()["id"]
    # تسجيل نصيب واحد (نصف الحلة لأن servings=2)
    r = client.post(f"/recipes/{rid}/log", json={"date": TODAY, "meal": "dinner", "servings": 1}, headers=h)
    assert r.status_code == 201, r.text
    logged = r.json()
    assert logged["source"] == "recipe"
    # نصيب واحد ≈ نصف الإجمالي ≈ 192
    assert abs(logged["calories"] - 192) <= 2


def test_recipe_isolation(client):
    ha = auth_headers(client, "ru4")
    hb = auth_headers(client, "ru5")
    rid = client.post("/recipes", json=RECIPE, headers=ha).json()["id"]
    r = client.get(f"/recipes/{rid}", headers=hb)
    assert r.status_code == 404  # bob لا يرى وصفة alice
