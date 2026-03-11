"""
Email configuration.
"""
import os
from pydantic import BaseModel


class EmailConfig(BaseModel):
    """Email server configuration."""

    server: str = os.getenv("MAIL_SERVER", "mail.severindevelopment.ru")
    port: int = int(os.getenv("MAIL_PORT", "49587"))
    use_tls: bool = os.getenv("MAIL_USE_TLS", "false").lower() == "true"
    use_ssl: bool = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    username: str = os.getenv("MAIL_USERNAME", "severin-ai-noreply@svrd.ru")
    password: str = os.getenv("MAIL_PASSWORD", "")
    default_sender: str = os.getenv("MAIL_DEFAULT_SENDER", "severin-ai-noreply@svrd.ru")

    # Optional server info for email links
    server_name: str = os.getenv("SERVER_NAME", "localhost:8000")
    url_scheme: str = os.getenv("URL_SCHEME", "http")

    # Admin alert recipients (comma-separated emails)
    admin_emails: str = os.getenv("ADMIN_ALERT_EMAILS", "")


# Global config instance
email_config = EmailConfig()
