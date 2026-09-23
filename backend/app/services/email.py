import logging
import smtplib
import ssl
from email.message import EmailMessage

from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


def masked_email(email: str) -> str:
    local, domain = email.split("@", 1)
    return f"{local[:1]}***@{domain}"


class EmailProvider:
    """Email delivery boundary with a development console provider and SMTP."""

    def send_verification_code(self, recipient: str, code: str) -> None:
        if settings.email_provider == "console":
            if settings.app_env == "production":
                raise HTTPException(status_code=503, detail="生产环境禁止使用测试邮件服务")
            logger.info("Development email to %s: %s", masked_email(recipient), code)
            return
        if settings.email_provider != "smtp":
            raise HTTPException(status_code=503, detail="邮件服务尚未配置")
        if not settings.smtp_host or not settings.smtp_from:
            raise HTTPException(status_code=503, detail="SMTP 配置不完整")

        message = EmailMessage()
        message["Subject"] = "海大互助邮箱绑定验证码"
        message["From"] = settings.smtp_from
        message["To"] = recipient
        message.set_content(
            f"你的邮箱绑定验证码是：{code}\n\n"
            f"验证码 {settings.email_code_expire_seconds // 60} 分钟内有效。"
            "如非本人操作，请忽略本邮件。"
        )
        try:
            if settings.smtp_security == "ssl":
                client = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
            else:
                client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
            with client:
                if settings.smtp_security == "starttls":
                    client.starttls(context=ssl.create_default_context())
                if settings.smtp_username:
                    client.login(settings.smtp_username, settings.smtp_password)
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            logger.warning("Email delivery failed for %s: %s", masked_email(recipient), exc)
            raise HTTPException(status_code=503, detail="邮件发送失败，请稍后重试") from exc


email_provider = EmailProvider()
