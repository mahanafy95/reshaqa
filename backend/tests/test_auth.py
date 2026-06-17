"""اختبارات المصادقة وعزل المستخدمين الأساسي."""


def test_register_returns_token(client):
    r = client.post("/auth/register", json={"username": "sara", "password": "secret12"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_register_duplicate_username_rejected(client):
    client.post("/auth/register", json={"username": "ali", "password": "secret12"})
    r = client.post("/auth/register", json={"username": "ali", "password": "other123"})
    assert r.status_code == 409


def test_register_duplicate_case_insensitive(client):
    client.post("/auth/register", json={"username": "Mona", "password": "secret12"})
    r = client.post("/auth/register", json={"username": "mona", "password": "secret12"})
    assert r.status_code == 409


def test_login_success_and_me(client):
    client.post("/auth/register", json={"username": "khaled", "password": "secret12"})
    r = client.post("/auth/login", json={"username": "khaled", "password": "secret12"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "khaled"


def test_login_wrong_password_rejected(client):
    client.post("/auth/register", json={"username": "omar", "password": "secret12"})
    r = client.post("/auth/login", json={"username": "omar", "password": "wrongpass"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_me_rejects_invalid_token(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_short_password_rejected(client):
    r = client.post("/auth/register", json={"username": "newuser", "password": "12"})
    assert r.status_code == 422
