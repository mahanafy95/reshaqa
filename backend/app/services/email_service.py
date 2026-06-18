"""إرسال البريد — مجاني تماماً، بدون أي SMS.

مزوّدان مدعومان (يُختاران من EMAIL_PROVIDER):
  - gmail: SMTP عبر Gmail بكلمة مرور تطبيق (المسار الافتراضي).
  - brevo: HTTPS API احتياطي (منفذ 443 لا يُحجب) لو حجب Render منافذ SMTP.

لو البريد غير مضبوط يتعطّل بهدوء (يسجّل تحذيراً ويُرجع False) — فلا يكسر التطبيق.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage

import httpx

from ..config import settings

logger = logging.getLogger("reshaqa.email")


def _send_gmail(to: str, subject: str, text: str, html: str) -> bool:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.email_from_address}>"
    msg["To"] = to
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    context = ssl.create_default_context()
    if settings.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15, context=context) as s:
            s.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            s.send_message(msg)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as s:
            s.starttls(context=context)
            s.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            s.send_message(msg)
    return True


def _send_brevo(to: str, subject: str, text: str, html: str) -> bool:
    resp = httpx.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": settings.BREVO_API_KEY, "content-type": "application/json"},
        json={
            "sender": {"name": settings.SMTP_FROM_NAME, "email": settings.email_from_address},
            "to": [{"email": to}],
            "subject": subject,
            "textContent": text,
            "htmlContent": html,
        },
        timeout=15.0,
    )
    if resp.status_code not in (200, 201):
        logger.error("فشل إرسال Brevo: %s %s", resp.status_code, resp.text[:200])
        return False
    return True


def send_email(to: str, subject: str, text: str, html: str) -> bool:
    """يرسل بريداً نصّياً + HTML. يُرجع True عند النجاح، وإلا False (بدون رفع استثناء)."""
    if not settings.email_enabled:
        logger.warning("البريد غير مضبوط (EMAIL_PROVIDER=%s) — تخطّي الإرسال إلى %s",
                       settings.EMAIL_PROVIDER, to)
        return False
    try:
        if settings.EMAIL_PROVIDER == "brevo":
            return _send_brevo(to, subject, text, html)
        return _send_gmail(to, subject, text, html)
    except Exception:
        logger.exception("فشل إرسال البريد إلى %s", to)
        return False


def send_password_reset_code(to: str, code: str) -> bool:
    """يرسل رمز إعادة تعيين كلمة السر (6 أرقام) للمستخدم."""
    mins = settings.OTP_TTL_MINUTES
    subject = "رمز إعادة تعيين كلمة السر — رشاقة"
    text = (
        f"رمز إعادة تعيين كلمة السر بتاعك هو: {code}\n\n"
        f"الرمز صالح لمدة {mins} دقيقة.\n"
        "لو مطلبتش إعادة تعيين كلمة السر، تجاهل الرسالة دي."
    )
    html = (
        '<div dir="rtl" style="font-family:Tahoma,Arial,sans-serif;text-align:right;'
        'max-width:480px;margin:auto">'
        '<h2 style="color:#0d9488;margin:0 0 8px">رشاقة 🥗</h2>'
        "<p>رمز إعادة تعيين كلمة السر بتاعك:</p>"
        f'<p style="font-size:34px;font-weight:bold;letter-spacing:8px;color:#0d9488;'
        f'background:#f0fdfa;border-radius:12px;padding:14px;text-align:center">{code}</p>'
        f"<p>الرمز صالح لمدة {mins} دقيقة.</p>"
        '<p style="color:#888;font-size:13px">لو مطلبتش إعادة تعيين كلمة السر، تجاهل الرسالة دي '
        "وكلمة سرّك هتفضل زي ما هي.</p>"
        "</div>"
    )
    return send_email(to, subject, text, html)
