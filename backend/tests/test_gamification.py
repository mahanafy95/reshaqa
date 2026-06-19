"""اختبارات التحفيز — سلسلة أيام التسجيل المتتالية والإنجازات (GET /streak)."""
from datetime import date, timedelta

from app.services import gamification
from tests.conftest import auth_headers


def _iso(d: date) -> str:
    return d.isoformat()


def _log(client, headers, on: date, name="بيض", cals=100):
    r = client.post(
        "/foods",
        json={"date": _iso(on), "meal": "snack", "name_ar": name, "amount": 100, "calories": cals},
        headers=headers,
    )
    assert r.status_code in (200, 201), r.text


# ---------- خدمة الحساب (بدون شبكة/قاعدة) ----------
def test_current_streak_counts_consecutive_ending_today():
    today = date(2026, 6, 19)
    s = {today, today - timedelta(days=1), today - timedelta(days=2)}
    assert gamification._current_streak(s, today) == 3


def test_current_streak_allows_yesterday_when_today_not_logged():
    today = date(2026, 6, 19)
    s = {today - timedelta(days=1), today - timedelta(days=2)}
    assert gamification._current_streak(s, today) == 2  # لسه ماسجّلش النهاردة، بس السلسلة مكسرتش


def test_current_streak_zero_when_gap():
    today = date(2026, 6, 19)
    s = {today - timedelta(days=3), today - timedelta(days=4)}
    assert gamification._current_streak(s, today) == 0


def test_longest_streak_picks_max_run():
    base = date(2026, 6, 1)
    dates = [base, base + timedelta(days=1), base + timedelta(days=2),  # run of 3
             base + timedelta(days=5), base + timedelta(days=6)]        # run of 2
    assert gamification._longest_streak(dates) == 3


# ---------- نقطة النهاية GET /streak ----------
def test_streak_empty_for_new_user(client):
    h = auth_headers(client, "streak_new")
    r = client.get("/streak", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["current_streak"] == 0
    assert body["total_days_logged"] == 0
    first = next(a for a in body["achievements"] if a["key"] == "first_log")
    assert first["unlocked"] is False


def test_streak_three_consecutive_days(client):
    h = auth_headers(client, "streak3")
    today = date.today()
    for i in range(3):
        _log(client, h, today - timedelta(days=i))
    r = client.get("/streak", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["current_streak"] == 3
    assert body["longest_streak"] == 3
    assert body["total_days_logged"] == 3
    unlocked = {a["key"] for a in body["achievements"] if a["unlocked"]}
    assert "first_log" in unlocked
    assert "streak_3" in unlocked
    assert "streak_7" not in unlocked


def test_streak_breaks_on_gap(client):
    h = auth_headers(client, "streak_gap")
    today = date.today()
    # سجّل النهاردة وإمبارح، وفجوة، ثم 3 أيام أقدم
    _log(client, h, today)
    _log(client, h, today - timedelta(days=1))
    for i in (4, 5, 6):
        _log(client, h, today - timedelta(days=i))
    r = client.get("/streak", headers=h).json()
    assert r["current_streak"] == 2          # النهاردة + إمبارح
    assert r["longest_streak"] == 3          # الـ3 أيام الأقدم
    assert r["total_days_logged"] == 5
