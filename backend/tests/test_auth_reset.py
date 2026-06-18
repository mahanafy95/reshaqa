"""اختبارات إعادة تعيين كلمة السر بالبريد (OTP) — مع محاكاة إرسال البريد (بدون SMTP)."""
import app.services.email_service as email_service
from app.config import settings


def _capture_codes(monkeypatch):
    """يلتقط رمز إعادة التعيين بدل إرساله فعلياً، ويُرجع قائمة الرموز."""
    sent = []

    def fake_send(to, code):
        sent.append((to, code))
        return True

    monkeypatch.setattr(email_service, "send_password_reset_code", fake_send)
    return sent


def _register(client, username, password, email):
    r = client.post(
        "/auth/register", json={"username": username, "password": password, "email": email}
    )
    assert r.status_code == 201, r.text
    return r


def test_full_reset_flow(client, monkeypatch):
    sent = _capture_codes(monkeypatch)
    _register(client, "rana", "oldpass1", "rana@gmail.com")

    r = client.post("/auth/forgot-password", json={"email": "rana@gmail.com"})
    assert r.status_code == 200
    assert len(sent) == 1
    code = sent[0][1]
    assert code.isdigit() and len(code) == 6

    r = client.post(
        "/auth/reset-password",
        json={"email": "rana@gmail.com", "code": code, "new_password": "newpass1"},
    )
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()

    # كلمة السر الجديدة تشتغل، القديمة لأ
    assert client.post("/auth/login", json={"username": "rana", "password": "newpass1"}).status_code == 200
    assert client.post("/auth/login", json={"username": "rana", "password": "oldpass1"}).status_code == 401


def test_forgot_unknown_email_is_silent(client, monkeypatch):
    sent = _capture_codes(monkeypatch)
    r = client.post("/auth/forgot-password", json={"email": "nobody@gmail.com"})
    assert r.status_code == 200  # نفس الرد — ما نكشفش وجود البريد
    assert len(sent) == 0  # ولا نرسل أي بريد


def test_wrong_code_rejected(client, monkeypatch):
    _capture_codes(monkeypatch)
    _register(client, "kareem", "oldpass1", "kareem@gmail.com")
    client.post("/auth/forgot-password", json={"email": "kareem@gmail.com"})
    r = client.post(
        "/auth/reset-password",
        json={"email": "kareem@gmail.com", "code": "000000", "new_password": "newpass1"},
    )
    assert r.status_code == 400
    # كلمة السر القديمة لسه شغالة
    assert client.post("/auth/login", json={"username": "kareem", "password": "oldpass1"}).status_code == 200


def test_code_used_once(client, monkeypatch):
    sent = _capture_codes(monkeypatch)
    _register(client, "hana", "oldpass1", "hana@gmail.com")
    client.post("/auth/forgot-password", json={"email": "hana@gmail.com"})
    code = sent[-1][1]
    assert client.post(
        "/auth/reset-password",
        json={"email": "hana@gmail.com", "code": code, "new_password": "newpass1"},
    ).status_code == 200
    # إعادة استخدام نفس الرمز تُرفض
    assert client.post(
        "/auth/reset-password",
        json={"email": "hana@gmail.com", "code": code, "new_password": "another1"},
    ).status_code == 400


def test_max_attempts_locks_code(client, monkeypatch):
    sent = _capture_codes(monkeypatch)
    _register(client, "tarek", "oldpass1", "tarek@gmail.com")
    client.post("/auth/forgot-password", json={"email": "tarek@gmail.com"})
    code = sent[-1][1]
    # نستهلك محاولات خاطئة بقدر الحد
    for _ in range(settings.OTP_MAX_ATTEMPTS):
        client.post(
            "/auth/reset-password",
            json={"email": "tarek@gmail.com", "code": "999999", "new_password": "newpass1"},
        )
    # حتى الرمز الصحيح يتقفل بعد تجاوز الحد
    r = client.post(
        "/auth/reset-password",
        json={"email": "tarek@gmail.com", "code": code, "new_password": "newpass1"},
    )
    assert r.status_code == 400


def test_set_email_and_duplicate(client):
    r = client.post("/auth/register", json={"username": "wael", "password": "pass1234"})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    # ضبط بريد
    res = client.post("/auth/email", json={"email": "wael@gmail.com"}, headers=h)
    assert res.status_code == 200
    assert res.json()["email"] == "wael@gmail.com"

    # مستخدم تاني يحاول ياخد نفس البريد -> 409
    r2 = client.post("/auth/register", json={"username": "wael2", "password": "pass1234"})
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    assert client.post("/auth/email", json={"email": "wael@gmail.com"}, headers=h2).status_code == 409


def test_register_duplicate_email_rejected(client):
    _register(client, "mostafa", "pass1234", "dup@gmail.com")
    r = client.post(
        "/auth/register", json={"username": "mostafa2", "password": "pass1234", "email": "dup@gmail.com"}
    )
    assert r.status_code == 409
