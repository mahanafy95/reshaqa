"""اختبار اشتقاق مفتاح تحديد المعدّل — لازم يقاوم تزوير X-Forwarded-For."""
from app.core.ratelimit import _client_key


class _Req:
    def __init__(self, headers):
        self.headers = headers


def test_uses_last_xff_hop_not_spoofable_first():
    # المهاجم يقدر يحط أي قيمة في أول X-Forwarded-For؛ بروكسي Render بيضيف العنوان
    # الحقيقي في الآخر. لازم ناخد الأخير (الموثوق) مش الأول (المزوّر).
    assert _client_key(_Req({"x-forwarded-for": "1.2.3.4, 9.9.9.9"})) == "9.9.9.9"
    assert _client_key(_Req({"x-forwarded-for": "evil, 203.0.113.7"})) == "203.0.113.7"
    assert _client_key(_Req({"x-forwarded-for": "203.0.113.7"})) == "203.0.113.7"
