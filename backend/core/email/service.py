"""
Email sending service.
"""
import smtplib
import socket
import logging
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional, Tuple

from .config import email_config

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


class EmailError(Exception):
    """Base exception for email errors."""
    pass


class EmailConfigError(EmailError):
    """Email configuration error (non-retryable)."""
    pass


class EmailConnectionError(EmailError):
    """Connection error (retryable)."""
    pass


class EmailAuthError(EmailError):
    """Authentication error (non-retryable)."""
    pass


class EmailRecipientError(EmailError):
    """Recipient rejected (non-retryable for specific recipients)."""
    pass


class EmailService:
    """Service for sending email notifications."""

    def __init__(self):
        self.config = email_config

    def send_report_notification(
        self,
        recipients: List[str],
        job_id: str,
        project_name: Optional[str] = None,
        output_files: Optional[dict] = None,
    ) -> bool:
        """
        Send email notification with report files attached.

        Args:
            recipients: List of email addresses
            job_id: Transcription job ID
            project_name: Optional project name for subject
            output_files: Dict of file_type -> file_path

        Returns:
            True if sent successfully, False otherwise
        """
        if not recipients:
            return False

        if not self.config.password:
            logger.warning("Email password not configured, skipping notification")
            return False

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.default_sender
            msg['To'] = ', '.join(recipients)

            # Subject
            subject = "Отчёт готов"
            if project_name:
                subject = f"Отчёт готов: {project_name}"
            msg['Subject'] = subject

            # Body
            body = self._create_email_body(job_id, project_name, output_files)
            msg.attach(MIMEText(body, 'html', 'utf-8'))

            # Attach files
            if output_files:
                for file_type, file_path in output_files.items():
                    self._attach_file(msg, file_path, file_type)

            # Send with retry logic
            success, error = self._send_email_with_retry(msg, recipients)
            if success:
                logger.info(f"Email notification sent to {recipients} for job {job_id}")
                return True
            else:
                logger.error(f"Failed to send email after retries: {error}")
                return False

        except EmailConfigError as e:
            logger.error(f"Email configuration error (non-retryable): {e}")
            return False
        except EmailAuthError as e:
            logger.error(f"Email authentication failed (check credentials): {e}")
            return False
        except EmailRecipientError as e:
            logger.error(f"Email recipient rejected: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error sending email notification: {e}")
            return False

    def _create_email_body(
        self,
        job_id: str,
        project_name: Optional[str],
        output_files: Optional[dict],
    ) -> str:
        """Create HTML email body."""
        base_url = f"{self.config.url_scheme}://{self.config.server_name}"

        files_list = ""
        if output_files:
            files_list = "<ul>"
            for file_type, file_path in output_files.items():
                file_name = Path(file_path).name if file_path else file_type
                files_list += f"<li>{file_name}</li>"
            files_list += "</ul>"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #10b981;">SeverinAutoprotocol</h2>

                <p>Обработка завершена{f' для проекта <strong>{project_name}</strong>' if project_name else ''}.</p>

                {f'<p><strong>Сгенерированные файлы:</strong></p>{files_list}' if files_list else ''}

                <p>Файлы прикреплены к этому письму.</p>

                <p style="margin-top: 30px;">
                    <a href="{base_url}/job/{job_id}"
                       style="background-color: #10b981; color: white; padding: 10px 20px;
                              text-decoration: none; border-radius: 5px;">
                        Открыть результаты
                    </a>
                </p>

                <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
                <p style="color: #888; font-size: 12px;">
                    Это автоматическое уведомление от SeverinAutoprotocol.
                </p>
            </div>
        </body>
        </html>
        """

    def _attach_file(self, msg: MIMEMultipart, file_path: str, file_type: str) -> None:
        """Attach a file to the email."""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File not found for attachment: {file_path}")
                return

            with open(path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())

            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{path.name}"'
            )
            msg.attach(part)

        except Exception as e:
            logger.error(f"Failed to attach file {file_path}: {e}")

    def _send_email_with_retry(
        self,
        msg: MIMEMultipart,
        recipients: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        Send email with retry logic for transient errors.

        Args:
            msg: Email message to send.
            recipients: List of recipient email addresses.

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._send_email(msg, recipients)
                return True, None

            except smtplib.SMTPAuthenticationError as e:
                # Authentication errors are not retryable
                raise EmailAuthError(f"SMTP authentication failed: {e}")

            except smtplib.SMTPRecipientsRefused as e:
                # Recipient errors are not retryable
                raise EmailRecipientError(f"Recipients refused: {e}")

            except smtplib.SMTPSenderRefused as e:
                # Sender errors are not retryable
                raise EmailConfigError(f"Sender refused: {e}")

            except (
                smtplib.SMTPConnectError,
                smtplib.SMTPServerDisconnected,
                socket.timeout,
                socket.error,
                ConnectionError,
            ) as e:
                # Connection errors are retryable
                last_error = str(e)
                if attempt < MAX_RETRIES:
                    logger.warning(
                        f"Email send attempt {attempt}/{MAX_RETRIES} failed "
                        f"(will retry in {RETRY_DELAY_SECONDS}s): {e}"
                    )
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    logger.error(f"Email send failed after {MAX_RETRIES} attempts: {e}")

            except smtplib.SMTPException as e:
                # Other SMTP errors - retry once
                last_error = str(e)
                if attempt < MAX_RETRIES:
                    logger.warning(f"SMTP error on attempt {attempt}, retrying: {e}")
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    logger.error(f"SMTP error after {MAX_RETRIES} attempts: {e}")

        return False, last_error

    def _send_email(self, msg: MIMEMultipart, recipients: List[str]) -> None:
        """Send the email via SMTP (single attempt)."""
        server = None
        try:
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(
                    self.config.server,
                    self.config.port,
                    timeout=30
                )
            else:
                server = smtplib.SMTP(
                    self.config.server,
                    self.config.port,
                    timeout=30
                )

            if self.config.use_tls:
                server.starttls()

            server.login(self.config.username, self.config.password)
            server.sendmail(
                self.config.default_sender,
                recipients,
                msg.as_string()
            )
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass  # Ignore errors during cleanup


# Global service instance
email_service = EmailService()


def send_report_email(
    recipients: List[str],
    job_id: str,
    project_name: Optional[str] = None,
    output_files: Optional[dict] = None,
) -> bool:
    """Convenience function to send report notification."""
    return email_service.send_report_notification(
        recipients=recipients,
        job_id=job_id,
        project_name=project_name,
        output_files=output_files,
    )
