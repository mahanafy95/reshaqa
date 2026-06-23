"""اختبارات المجتمع — الأصدقاء والرسائل والتشجيع."""
from tests.conftest import auth_headers


def _uid(client, headers) -> int:
    return client.get("/auth/me", headers=headers).json()["id"]


def test_friend_request_accept_and_message_flow(client):
    ha = auth_headers(client, "amal")
    hb = auth_headers(client, "basma")
    bid = _uid(client, hb)
    aid = _uid(client, ha)

    # amal تبحث عن basma وتبعت طلب
    s = client.get("/social/search?q=basma", headers=ha).json()
    assert any(u["username"] == "basma" and u["relation"] == "none" for u in s)
    r = client.post(f"/social/friends/request/{bid}", headers=ha)
    assert r.status_code == 200
    assert any(f["user_id"] == bid for f in r.json()["outgoing"])

    # basma تشوف الطلب الوارد وتقبله
    fl = client.get("/social/friends", headers=hb).json()
    assert any(f["user_id"] == aid for f in fl["incoming"])
    r = client.post(f"/social/friends/{aid}/accept", headers=hb)
    assert r.status_code == 200
    assert any(f["user_id"] == aid for f in r.json()["friends"])

    # رسالة من amal لـ basma
    m = client.post("/social/messages", json={"to_user_id": bid, "body": "إزيك يا بسمة"}, headers=ha)
    assert m.status_code == 201, m.text

    # basma عندها رسالة غير مقروءة
    assert client.get("/social/unread", headers=hb).json()["total"] == 1
    # تفتح المحادثة → تتعلّم مقروءة
    conv = client.get(f"/social/messages/{aid}", headers=hb).json()
    assert len(conv) == 1 and conv[0]["body"] == "إزيك يا بسمة" and conv[0]["mine"] is False
    assert client.get("/social/unread", headers=hb).json()["total"] == 0


def test_cannot_message_non_friend(client):
    ha = auth_headers(client, "carla")
    hb = auth_headers(client, "dalia")
    bid = _uid(client, hb)
    r = client.post("/social/messages", json={"to_user_id": bid, "body": "هاي"}, headers=ha)
    assert r.status_code == 403


def test_whitespace_only_message_rejected(client):
    # مسافات بس بتعدّي min_length لكنها فاضية بعد strip → لازم 422 (مش رسالة فاضية مخزّنة)
    ha = auth_headers(client, "ghada")
    hb = auth_headers(client, "hala")
    bid = _uid(client, hb)
    r = client.post("/social/messages", json={"to_user_id": bid, "body": "   "}, headers=ha)
    assert r.status_code == 422, r.text


def test_mutual_request_auto_accepts(client):
    ha = auth_headers(client, "eman")
    hb = auth_headers(client, "farida")
    aid = _uid(client, ha)
    bid = _uid(client, hb)
    client.post(f"/social/friends/request/{bid}", headers=ha)   # eman → farida
    # farida تبعت طلب لـ eman → يتقبل تلقائيًا
    r = client.post(f"/social/friends/request/{aid}", headers=hb)
    assert r.status_code == 200
    assert any(f["user_id"] == aid for f in r.json()["friends"])


def test_cheer_sends_encouragement(client):
    ha = auth_headers(client, "gamal")
    hb = auth_headers(client, "hoda")
    aid = _uid(client, ha)
    bid = _uid(client, hb)
    client.post(f"/social/friends/request/{bid}", headers=ha)
    client.post(f"/social/friends/{aid}/accept", headers=hb)
    r = client.post(f"/social/cheer/{bid}", headers=ha)
    assert r.status_code == 201
    assert r.json()["kind"] == "cheer" and r.json()["body"]


def test_polling_after_id_returns_only_new(client):
    ha = auth_headers(client, "iman")
    hb = auth_headers(client, "jana")
    aid = _uid(client, ha)
    bid = _uid(client, hb)
    client.post(f"/social/friends/request/{bid}", headers=ha)
    client.post(f"/social/friends/{aid}/accept", headers=hb)
    m1 = client.post("/social/messages", json={"to_user_id": bid, "body": "رسالة ١"}, headers=ha).json()
    client.post("/social/messages", json={"to_user_id": bid, "body": "رسالة ٢"}, headers=ha)
    # استطلاع: هات اللي بعد أول رسالة
    newer = client.get(f"/social/messages/{aid}?after_id={m1['id']}", headers=hb).json()
    assert len(newer) == 1 and newer[0]["body"] == "رسالة ٢"


def test_cannot_friend_self(client):
    ha = auth_headers(client, "khaled")
    aid = _uid(client, ha)
    assert client.post(f"/social/friends/request/{aid}", headers=ha).status_code == 400


def test_remove_friend(client):
    ha = auth_headers(client, "lina")
    hb = auth_headers(client, "mona2")
    aid = _uid(client, ha)
    bid = _uid(client, hb)
    client.post(f"/social/friends/request/{bid}", headers=ha)
    client.post(f"/social/friends/{aid}/accept", headers=hb)
    # lina تشيل الصداقة
    r = client.delete(f"/social/friends/{bid}", headers=ha)
    assert r.status_code == 200
    assert not r.json()["friends"]
    # بعد الإزالة مينفعش رسائل
    assert client.post("/social/messages", json={"to_user_id": bid, "body": "x"}, headers=ha).status_code == 403


def test_social_requires_auth(client):
    assert client.get("/social/friends").status_code == 401
    assert client.get("/social/search?q=a").status_code == 401
