import logging

from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


class SmsProvider:
    """Provider boundary. Replace the console branch with an approved SMS vendor in production."""

    def send_verification_code(self, phone: str, code: str) -> None:
        if settings.sms_provider != "console":
            raise HTTPException(status_code=503, detail="短信服务尚未配置")
        if settings.app_env == "production":
            raise HTTPException(status_code=503, detail="生产环境禁止使用测试短信服务")
        logger.info("Development SMS to *******%s: %s", phone[-4:], code)


sms_provider = SmsProvider()
