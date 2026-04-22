import smtplib
from email.message import EmailMessage

from app.core.config import settings


class EmailProvider:
    def send(self, to: str, subject: str, body: str, attachments: list[tuple[str, bytes, str]] | None = None) -> dict:
        if not settings.email_enabled:
            return {"sent": False, "provider": "disabled", "to": to, "subject": subject}
        message = EmailMessage()
        message["From"] = settings.email_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        for filename, content, mime_type in attachments or []:
            maintype, subtype = mime_type.split("/", 1)
            message.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
        return {"sent": True, "provider": "smtp", "to": to, "subject": subject}


email_provider = EmailProvider()
