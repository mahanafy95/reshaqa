"""اختبارات محرك السعرات — تركّز على قواعد الأمان الصحي."""
import pytest

from app.models.enums import ActivityLevel, Sex, TargetMode
from app.services import body_metrics as BM
from app.services import calories as C


# ---------- BMR / TDEE ----------
def test_bmr_male_known_value():
    # 10*80 + 6.25*180 - 5*30 + 5 = 1780
    assert C.bmr_mifflin(Sex.male, 80, 180, 30) == pytest.approx(1780.0)


def test_bmr_female_known_value():
    # 10*65 + 6.25*165 - 5*30 - 161 = 1370.25
    assert C.bmr_mifflin(Sex.female, 65, 165, 30) == pytest.approx(1370.25)


def test_tdee_activity_factors():
    assert C.tdee(1780, ActivityLevel.sedentary) == pytest.approx(2136.0)
    assert C.tdee(1780, ActivityLevel.active) == pytest.approx(1780 * 1.725)


# ---------- العجز ----------
def test_deficit_capped_at_500():
    # 20% من 3000 = 600 > 500 => العجز = 500
    assert C.loss_deficit(3000) == pytest.approx(500.0)


def test_deficit_uses_percentage_when_below_500():
    # 20% من 2000 = 400 < 500 => العجز = 400
    assert C.loss_deficit(2000) == pytest.approx(400.0)


def test_deficit_respects_gentle_rate():
    # معدل بطيء جداً 0.25 كجم/أسبوع => عجز ~275 سعرة (أقل من 400/500)
    d = C.loss_deficit(2000, goal_rate_kg_week=0.25)
    assert d == pytest.approx(0.25 * 7700 / 7)  # ≈ 275
    assert d < 400


def test_deficit_rate_cannot_exceed_safety_cap():
    # حتى لو طلب معدل عالٍ، لا يتجاوز العجز 500 ولا 20%
    d = C.loss_deficit(2000, goal_rate_kg_week=2.0)
    assert d <= 400.0 + 1e-9


# ---------- الحد الأدنى الآمن ----------
def test_floor_for_women_1200():
    r = C.compute_targets(
        sex=Sex.female, age=70, height_cm=150, weight_kg=45,
        activity_level=ActivityLevel.sedentary,
    )
    assert r.target_calories == 1200
    assert r.floored_to_safe_min is True


def test_floor_for_men_1500():
    r = C.compute_targets(
        sex=Sex.male, age=75, height_cm=160, weight_kg=55,
        activity_level=ActivityLevel.sedentary,
    )
    assert r.target_calories == 1500
    assert r.floored_to_safe_min is True


def test_normal_case_not_floored():
    r = C.compute_targets(
        sex=Sex.male, age=30, height_cm=180, weight_kg=90,
        activity_level=ActivityLevel.moderate, goal_weight_kg=78,
    )
    assert r.floored_to_safe_min is False
    assert r.mode == TargetMode.loss
    assert r.target_calories > 1500


# ---------- التحقق من الوزن المستهدف ----------
def test_goal_below_healthy_blocked_with_suggestion():
    v = C.validate_goal_weight(goal_weight_kg=48, height_cm=170)
    assert v.is_valid is False
    assert v.suggested_goal_kg == v.healthy_min_kg
    assert v.healthy_min_kg == pytest.approx(53.5, abs=0.2)


def test_goal_within_healthy_ok():
    v = C.validate_goal_weight(goal_weight_kg=65, height_cm=170)
    assert v.is_valid is True


# ---------- اختيار البرنامج (وضع الهدف) ----------
def test_mode_by_goal_direction():
    # أطوال طبيعية الوزن حتى لا تتدخّل بوابات حالة الجسم
    assert C.determine_mode(72, 175, 72) == TargetMode.maintain   # عند الهدف
    assert C.determine_mode(75, 175, 72) == TargetMode.loss        # فوق الهدف → تخسيس
    assert C.determine_mode(70, 175, 72) == TargetMode.gain        # تحت الهدف → زيادة


def test_mode_auto_from_bmi_when_no_goal():
    # بدون هدف: نشتقّ البرنامج من حالة الوزن
    assert C.determine_mode(45, 165, None) == TargetMode.gain      # BMI ≈ 16.5 تحت
    assert C.determine_mode(64, 170, None) == TargetMode.maintain  # BMI ≈ 22 ضمن
    assert C.determine_mode(95, 175, None) == TargetMode.loss      # BMI ≈ 31 فوق


def test_maintain_uses_full_tdee_no_deficit():
    r = C.compute_targets(
        sex=Sex.male, age=30, height_cm=180, weight_kg=72,
        activity_level=ActivityLevel.moderate, goal_weight_kg=72,
    )
    assert r.mode == TargetMode.maintain
    assert r.deficit_applied == 0
    assert r.target_calories == round(r.tdee)


# ---------- الماكروز ----------
def test_macros_protein_within_range_and_nonnegative():
    m = C.split_macros(1708, weight_kg=80, protein_per_kg=1.8)
    assert m.protein_g == pytest.approx(144, abs=1)   # 1.8 * 80
    assert m.carbs_g >= 0
    assert m.fat_g >= 0


def test_macros_clamped_protein_per_kg():
    # طلب 3.0 جم/كجم يُقصّ إلى 2.0 كحد أقصى
    m = C.split_macros(2000, weight_kg=80, protein_per_kg=3.0)
    assert m.protein_g == pytest.approx(160, abs=1)   # 2.0 * 80


def test_macros_low_calorie_no_negative_carbs():
    # شخص ثقيل وسعرات منخفضة => لا نشويات سالبة
    m = C.split_macros(1200, weight_kg=150, protein_per_kg=1.8)
    assert m.carbs_g >= 0
    assert m.protein_g > 0
    assert m.fat_g > 0


def test_macros_calories_field_matches_target():
    m = C.split_macros(1750, weight_kg=70)
    assert m.calories == 1750


# ---------- التكامل ----------
# ---------- برنامج زيادة الوزن للأشخاص تحت النطاق الصحي ----------
def test_underweight_gets_gain_program_with_surplus():
    # امرأة 45 كجم، 165 سم => BMI ≈ 16.5 (تحت 18.5) وبدون هدف => زيادة
    r = C.compute_targets(
        sex=Sex.female, age=30, height_cm=165, weight_kg=45,
        activity_level=ActivityLevel.light, goal_weight_kg=None,
    )
    assert r.mode == TargetMode.gain
    assert r.deficit_applied < 0                 # فائض (سالب)
    assert r.target_calories > round(r.tdee)     # أعلى من سعرات المحافظة
    assert r.weight_status == "underweight"
    assert r.recommended_goal_weight_kg is not None
    assert any("تحت النطاق الصحي" in m for m in r.messages_ar)


def test_underweight_never_put_on_deficit_even_with_low_goal():
    # وزن حالي تحت الصحي؛ حتى لو دخل هدف منخفض، البوابة تمنع التخسيس وتحوّله لزيادة
    r = C.compute_targets(
        sex=Sex.male, age=25, height_cm=180, weight_kg=58,  # BMI ≈ 17.9
        activity_level=ActivityLevel.moderate, goal_weight_kg=55,
    )
    assert r.mode == TargetMode.gain
    assert r.deficit_applied <= 0  # مفيش عجز إطلاقاً


# ---------- نسبة الدهون (N3) ----------
def test_deurenberg_capped_at_plausible_max():
    bf = BM.body_fat_deurenberg(bmi_value=60, age=80, sex=Sex.female)
    assert bf <= 70.0


def test_compute_targets_full_shape():
    r = C.compute_targets(
        sex=Sex.female, age=28, height_cm=165, weight_kg=80,
        activity_level=ActivityLevel.light, goal_weight_kg=62,
        goal_rate_kg_week=0.5,
    )
    assert r.mode == TargetMode.loss
    assert r.target_calories >= 1200
    assert r.macros.protein_g > 0
    assert r.bmi == pytest.approx(80 / (1.65 ** 2), abs=0.1)
