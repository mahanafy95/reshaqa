"""اختبارات برنامج زيادة الوزن + التصنيف التلقائي حسب الوزن + بوابات الأمان.

يغطّي طلب المستخدم: تحت الطبيعي → زيادة، فوق الطبيعي → تخسيس، ضمن الطبيعي → تثبيت.
"""
import pytest

from app.models.enums import ActivityLevel, Sex, TargetMode
from app.services import body_metrics as BM
from app.services import calories as C
from tests.conftest import auth_headers


# ---------- التصنيف حسب الوزن ----------
def test_weight_status_buckets():
    assert BM.weight_status(16.0) == "underweight"
    assert BM.weight_status(22.0) == "normal"
    assert BM.weight_status(18.5) == "normal"   # الحد الأدنى الصحي
    assert BM.weight_status(24.9) == "normal"
    assert BM.weight_status(25.0) == "overweight"
    assert BM.weight_status(31.0) == "overweight"


def test_weight_at_bmi_and_recommended_goal():
    # طول 170 سم: وزن عند BMI 20 = 20 * 1.7^2 = 57.8
    assert BM.weight_at_bmi(20.0, 170) == pytest.approx(57.8, abs=0.1)
    # تحت الطبيعي → يقترح وزناً مريحاً داخل الطبيعي (BMI 20)
    g_under = BM.recommended_goal_weight(48, 170)
    assert g_under == pytest.approx(57.8, abs=0.2)
    # فوق الطبيعي → يقترح BMI 24
    g_over = BM.recommended_goal_weight(95, 170)
    assert g_over == pytest.approx(24.0 * 1.7 * 1.7, abs=0.2)
    # ضمن الطبيعي → بدون اقتراح (التثبيت)
    assert BM.recommended_goal_weight(64, 170) is None


# ---------- حساب الفائض ----------
def test_gain_surplus_default_pct_capped():
    # 12% من 2500 = 300 (أقل من 500)
    assert C.gain_surplus(2500) == pytest.approx(300.0)
    # 12% من 5000 = 600 > 500 => يُقصّ إلى 500
    assert C.gain_surplus(5000) == pytest.approx(500.0)


def test_gain_surplus_from_rate_and_capped():
    # معدل 0.25 كجم/أسبوع => ~275 سعرة
    assert C.gain_surplus(2500, goal_rate_kg_week=0.25) == pytest.approx(0.25 * 7700 / 7, abs=0.5)
    # معدل عالٍ يُقصّ بمعدل الزيادة الأقصى (0.5) ثم بسقف 500
    assert C.gain_surplus(2500, goal_rate_kg_week=2.0) <= 500.0 + 1e-9


# ---------- وضع الزيادة في المحرك ----------
def test_gain_mode_adds_surplus_and_high_protein():
    r = C.compute_targets(
        sex=Sex.male, age=25, height_cm=180, weight_kg=58,  # BMI ≈ 17.9 تحت
        activity_level=ActivityLevel.moderate,
    )
    assert r.mode == TargetMode.gain
    assert r.target_calories > round(r.tdee)
    assert r.deficit_applied < 0  # فائض
    assert r.floored_to_safe_min is False
    assert r.weight_status == "underweight"
    assert r.macros.protein_g > 0


def test_normal_weight_no_goal_maintains():
    r = C.compute_targets(
        sex=Sex.female, age=30, height_cm=170, weight_kg=64,  # BMI ≈ 22 ضمن
        activity_level=ActivityLevel.light,
    )
    assert r.mode == TargetMode.maintain
    assert r.deficit_applied == 0
    assert r.target_calories == round(r.tdee)
    assert r.weight_status == "normal"
    assert r.recommended_goal_weight_kg is None


def test_overweight_no_goal_loses():
    r = C.compute_targets(
        sex=Sex.male, age=40, height_cm=175, weight_kg=95,  # BMI ≈ 31 فوق
        activity_level=ActivityLevel.sedentary,
    )
    assert r.mode == TargetMode.loss
    assert r.deficit_applied > 0
    assert r.weight_status == "overweight"
    assert r.recommended_goal_weight_kg is not None


# ---------- بوابة أمان: لا زيادة لشخص فوق النطاق الصحي ----------
def test_overweight_never_gains_even_with_higher_goal():
    # وزن فوق الصحي + هدف أعلى من الحالي => البوابة تمنع الزيادة وتحوّله لتخسيس
    r = C.compute_targets(
        sex=Sex.male, age=30, height_cm=175, weight_kg=95,  # BMI ≈ 31
        activity_level=ActivityLevel.moderate, goal_weight_kg=100,
    )
    assert r.mode == TargetMode.loss
    assert r.deficit_applied > 0


# ---------- اتّساق حدّ النطاق الصحي مع التصنيف (لا فجوة [24.9, 25.0)) ----------
def test_healthy_max_consistent_with_classification():
    # أي وزن مصنّف "طبيعي" لازم يكون داخل النطاق الصحي المعروض (لا أعلى من الحد الأقصى)
    lo, hi = BM.healthy_weight_range(170)
    # وزن BMI ≈ 24.95 (كان قبل الإصلاح يُصنَّف طبيعي رغم تجاوزه الحد الأقصى المعروض)
    w = 72.1
    assert BM.weight_status(BM.bmi(w, 170)) == "normal"
    assert w <= hi  # متّسق: طبيعي ⇐ داخل النطاق
    # عند/فوق 25.0 يُصنَّف فوق النطاق
    assert BM.weight_status(25.0) == "overweight"
    assert BM.weight_status(24.99) == "normal"


# ---------- ثبات معادلة الطاقة بعد الحد الأدنى الآمن ----------
def test_deficit_identity_holds_after_safe_floor():
    # امرأة صغيرة فوق الوزن الصحي لكن TDEE تحت 1200 => تخسيس + تثبيت عند الحد الأدنى
    r = C.compute_targets(
        sex=Sex.female, age=75, height_cm=150, weight_kg=58,  # BMI ≈ 25.8 فوق
        activity_level=ActivityLevel.sedentary,
    )
    assert r.mode == TargetMode.loss
    assert r.floored_to_safe_min is True
    assert r.target_calories == 1200
    # المعادلة target == tdee - deficit_applied تبقى صحيحة (deficit_applied سالب هنا)
    assert abs(r.target_calories - (r.tdee - r.deficit_applied)) <= 1.0
    assert r.deficit_applied < 0  # فعلياً فائض بسيط فرضه الحد الأدنى الآمن


# ---------- التحقق من الوزن المستهدف فوق النطاق الصحي (جديد) ----------
def test_goal_above_healthy_blocked_with_suggestion():
    v = C.validate_goal_weight(goal_weight_kg=80, height_cm=170)
    assert v.is_valid is False
    assert v.suggested_goal_kg == v.healthy_max_kg


# ---------- اختبارات على مستوى الـ API ----------
def test_api_underweight_profile_and_targets_gain(client):
    h = auth_headers(client, "thin_user")
    prof = {
        "age": 28, "sex": "female", "height_cm": 170, "weight_kg": 48,  # BMI ≈ 16.6
        "activity_level": "light",
    }
    r = client.put("/profile", json=prof, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["weight_status"] == "underweight"
    assert body["recommended_goal_weight_kg"] is not None

    t = client.get("/targets", headers=h).json()
    assert t["mode"] == "gain"
    assert t["weight_status"] == "underweight"
    assert t["deficit_applied"] < 0
    assert t["target_calories"] > t["tdee"]


def test_api_save_today_target_gain_persists(client):
    h = auth_headers(client, "thin_user2")
    prof = {
        "age": 22, "sex": "male", "height_cm": 180, "weight_kg": 56,  # BMI ≈ 17.3
        "activity_level": "moderate",
    }
    client.put("/profile", json=prof, headers=h)
    r = client.post("/targets/today", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "gain"


def test_monthly_summary_is_mode_aware():
    from app.services.reports import _monthly_summary
    # مستخدم هدفه زيادة لكنه نزل وزن => ممنوع نهنّيه على النزول
    g = _monthly_summary("gain", -1.2, 5, 20)
    assert "نزلت" not in g
    assert "زيادة" in g or "زوّد" in g
    # هدفه زيادة وزاد فعلاً => تهنئة بالزيادة
    assert "زدت" in _monthly_summary("gain", 1.0, 5, 20)
    # هدفه تخسيس ونزل => تهنئة بالنزول
    assert "نزلت" in _monthly_summary("loss", -1.0, 5, 20)


def test_daily_calories_status_mode_aware():
    from app.models.enums import TargetMode
    from app.services.summary_service import _status_calories
    # زيادة + تحت الهدف => نشجّع على أكل أكتر (مش "زوّدت")
    s, msg = _status_calories(2000, 1500, TargetMode.gain)
    assert s == "قليل" and ("كمّل" in msg or "الزيادة" in msg)
    # تخسيس + فوق الهدف
    s2, _ = _status_calories(1500, 1800, TargetMode.loss)
    assert s2 == "كتير"


def test_admin_detail_exposes_program(client, db_session):
    from sqlalchemy import select
    from app.models.user import User

    th = auth_headers(client, "thin_target", "pass1234")
    ah = auth_headers(client, "boss_prog", "bosspass1")
    u = db_session.scalar(select(User).where(User.username == "boss_prog"))
    u.is_admin = True
    db_session.commit()

    # ملف تحت الوزن الصحي => البرنامج زيادة
    client.put(
        "/profile",
        json={"age": 25, "sex": "female", "height_cm": 170, "weight_kg": 48, "activity_level": "light"},
        headers=th,
    )
    tid = next(x["id"] for x in client.get("/admin/users", headers=ah).json() if x["username"] == "thin_target")
    detail = client.get(f"/admin/users/{tid}", headers=ah).json()
    assert detail["mode"] == "gain"
    assert detail["weight_status"] == "underweight"


def test_api_goal_above_healthy_rejected(client):
    h = auth_headers(client, "over_goal_user")
    bad = {
        "age": 30, "sex": "male", "height_cm": 170, "weight_kg": 65,
        "activity_level": "moderate", "goal_weight_kg": 85,  # فوق النطاق الصحي
    }
    r = client.put("/profile", json=bad, headers=h)
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["suggested_goal_kg"] == detail["healthy_max_kg"]
