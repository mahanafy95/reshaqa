"""اختبارات المحلّل الذكي (لغة عربية مصرية) — منطق خالص بدون قاعدة بيانات."""
from app.services.meal_parser import normalize, parse_text, resolve_grams, unit_grams


def names(text, meal="snack"):
    return [(i.name_ar, i.qty, i.unit_ar, i.meal) for i in parse_text(text, meal)]


# ---------- التطبيع ----------
def test_normalize_arabic_digits():
    assert normalize("٢ رغيف") == "2 رغيف"
    assert normalize("١٠٫٥") == "10.5"


# ---------- أمثلة أساسية ----------
def test_three_items_with_waw():
    items = parse_text("بيضتين وكوباية لبن ورغيف عيش")
    assert len(items) == 3
    assert items[0].qty == 2 and "بيض" in items[0].name_ar
    assert items[1].unit_ar in ("كوباية", "كوبايه") and items[1].qty == 1 and "لبن" in items[1].name_ar
    assert items[2].unit_ar == "رغيف"


def test_strips_filler_words():
    items = parse_text("النهاردة اكلت بيضتين")
    assert len(items) == 1
    assert items[0].qty == 2 and "بيض" in items[0].name_ar


def test_digit_plus_unit_food_is_the_unit():
    # "2 رغيف" = رغيفين عيش — الوحدة نفسها هي الصنف
    items = parse_text("٢ رغيف")
    assert len(items) == 1
    assert items[0].qty == 2 and items[0].unit_ar == "رغيف" and items[0].name_ar == "رغيف"


def test_fraction_number_word():
    items = parse_text("نص فرخة")
    assert len(items) == 1
    assert items[0].qty == 0.5 and "فرخة" in items[0].name_ar


def test_spoon_unit():
    items = parse_text("3 معلقة عسل")
    assert len(items) == 1
    assert items[0].qty == 3 and items[0].unit_ar in ("معلقة", "ملعقة") and "عسل" in items[0].name_ar


def test_dual_unit():
    items = parse_text("كوبايتين شاي")
    assert len(items) == 1
    assert items[0].qty == 2 and "شاي" in items[0].name_ar


def test_meal_switching():
    items = parse_text("بيض وعلى الغدا رز", "breakfast")
    assert len(items) == 2
    assert items[0].meal == "breakfast"
    assert items[1].meal == "lunch" and "رز" in items[1].name_ar


def test_meal_marker_at_start():
    items = parse_text("الفطار فول وطعمية", "snack")
    assert items[0].meal == "breakfast"
    assert any("فول" in i.name_ar for i in items)


def test_meal_verb_after_filler():
    # "النهاردة فطرت بيضتين" — لازم يفهم "فطرت" = فطار ويشيلها من الاسم
    items = parse_text("النهاردة فطرت بيضتين", "snack")
    assert len(items) == 1
    assert items[0].meal == "breakfast"
    assert items[0].qty == 2
    assert "فطرت" not in items[0].name_ar and "بيض" in items[0].name_ar


def test_commas_and_plus():
    items = parse_text("تفاحة، موزة + برتقالة")
    assert len(items) == 3


def test_empty_and_garbage():
    assert parse_text("") == []
    assert parse_text("   ") == []


def test_default_meal_applied():
    items = parse_text("تفاحة", "dinner")
    assert items[0].meal == "dinner"


# ---------- تحويل الجرامات ----------
def test_resolve_grams_liquid_unit():
    assert resolve_grams(2, "كوباية", None, None) == 480
    assert resolve_grams(1, "معلقة كبيرة", None, None) == 15


def test_resolve_grams_uses_library_portion():
    assert resolve_grams(1, None, "طبق", 350) == 350
    assert resolve_grams(2, None, "حبة", 50) == 100


def test_resolve_grams_default():
    assert resolve_grams(1, None, None, None) == 100
    assert resolve_grams(2, None, None, None) == 200


def test_unit_grams_lookup():
    assert unit_grams("كوب") == 240
    assert unit_grams("معلقة صغيرة") == 5
    assert unit_grams(None) is None
    assert unit_grams("حاجة غير معروفة") is None
