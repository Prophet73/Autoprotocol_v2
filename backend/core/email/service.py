"""
Email sending service.

Supports:
- Report notifications with attachments
- Role-based filtering (risk briefs only for manager+)
- Auto-sending critical risk briefs to project managers
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
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime

from .config import email_config

logger = logging.getLogger(__name__)

# Roles that can receive risk briefs (manager and above)
RISK_BRIEF_ALLOWED_ROLES = {"manager", "admin", "superuser"}

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
    """Service for sending email notifications with role-based filtering."""

    def __init__(self):
        self.config = email_config

    def _get_user_roles_by_emails(self, emails: List[str]) -> Dict[str, Optional[str]]:
        """
        Fetch user roles from database by email addresses.
        
        Args:
            emails: List of email addresses to lookup
            
        Returns:
            Dict mapping email -> role (or None if user not found)
        """
        import asyncio
        from sqlalchemy import select
        from backend.shared.database import get_celery_session_factory
        from backend.shared.models import User

        async def _fetch():
            result = {}
            session_factory = get_celery_session_factory()
            async with session_factory() as db:
                for email in emails:
                    query = select(User).where(User.email == email, User.is_active == True)
                    db_result = await db.execute(query)
                    user = db_result.scalar_one_or_none()
                    result[email] = user.role if user else None
            return result

        try:
            return asyncio.run(_fetch())
        except RuntimeError:
            # Already in event loop - run in thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _fetch())
                return future.result()

    def _filter_recipients_for_risk_brief(
        self, 
        recipients: List[str],
        output_files: Optional[dict]
    ) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
        """
        Filter recipients based on their roles and separate files accordingly.
        
        Risk brief is only sent to users with role >= manager.
        Users not in system or with lower roles get other files only.
        
        Args:
            recipients: All recipient emails
            output_files: Dict of file_type -> file_path
            
        Returns:
            Tuple of:
            - Dict mapping recipient email -> list of allowed file types
            - Dict of user roles for logging
        """
        if not recipients:
            return {}, {}
            
        # Fetch roles from DB
        user_roles = self._get_user_roles_by_emails(recipients)
        
        recipient_files = {}
        for email in recipients:
            role = user_roles.get(email)
            
            # Determine which files this recipient can receive
            if role and role in RISK_BRIEF_ALLOWED_ROLES:
                # Manager+ gets everything
                allowed_types = list(output_files.keys()) if output_files else []
            else:
                # Viewer/User/Unknown gets everything EXCEPT risk_brief
                allowed_types = [
                    ft for ft in (output_files.keys() if output_files else [])
                    if ft != "risk_brief"
                ]
            
            recipient_files[email] = allowed_types
            
            # Log the filtering
            if role is None:
                logger.info(f"Email {email}: user not in system, treating as viewer (no risk_brief)")
            elif role not in RISK_BRIEF_ALLOWED_ROLES:
                logger.info(f"Email {email}: role={role}, excluding risk_brief")
            else:
                logger.info(f"Email {email}: role={role}, full access including risk_brief")
        
        return recipient_files, user_roles

    def send_report_notification(
        self,
        recipients: List[str],
        job_id: str,
        project_name: Optional[str] = None,
        output_files: Optional[dict] = None,
    ) -> bool:
        """
        Send email notification with report files attached.
        
        Risk brief is filtered based on recipient roles:
        - manager, admin, superuser: receive all files including risk_brief
        - viewer, user, unknown: receive all files EXCEPT risk_brief

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
            # Filter recipients by role
            recipient_files, user_roles = self._filter_recipients_for_risk_brief(
                recipients, output_files
            )
            
            # Group recipients by their allowed file sets for efficient sending
            # (recipients with same file set get one email)
            file_sets: Dict[tuple, List[str]] = {}
            for email, allowed_files in recipient_files.items():
                key = tuple(sorted(allowed_files))
                if key not in file_sets:
                    file_sets[key] = []
                file_sets[key].append(email)
            
            success_count = 0
            for file_types, emails in file_sets.items():
                if not file_types and not output_files:
                    # No files to attach, skip
                    continue
                    
                # Build filtered output_files for this group
                filtered_files = {
                    ft: fp for ft, fp in (output_files or {}).items()
                    if ft in file_types
                } if file_types else {}
                
                # Create message for this group
                msg = MIMEMultipart()
                msg['From'] = self.config.default_sender
                msg['To'] = ', '.join(emails)

                # Subject
                subject = "Отчёт готов"
                if project_name:
                    subject = f"Отчёт готов: {project_name}"
                msg['Subject'] = subject

                # Body
                body = self._create_email_body(job_id, project_name, filtered_files)
                msg.attach(MIMEText(body, 'html', 'utf-8'))

                # Attach filtered files
                for file_type, file_path in filtered_files.items():
                    self._attach_file(msg, file_path, file_type)

                # Send with retry logic
                success, error = self._send_email_with_retry(msg, emails)
                if success:
                    logger.info(f"Email sent to {emails} for job {job_id} (files: {list(file_types)})")
                    success_count += 1
                else:
                    logger.error(f"Failed to send email to {emails}: {error}")
            
            return success_count > 0

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

    def send_critical_risk_brief_to_managers(
        self,
        project_id: int,
        job_id: str,
        project_name: Optional[str] = None,
        risk_brief_status: str = "critical",
        dashboard_url: Optional[str] = None,
    ) -> bool:
        """
        Send critical risk brief notification to project managers.
        
        Called automatically when risk_brief.overall_status == "critical".
        
        Args:
            project_id: Construction project ID
            job_id: Transcription job ID
            project_name: Project name for email
            risk_brief_status: Status level (critical, attention, stable)
            dashboard_url: Optional direct link to dashboard
            
        Returns:
            True if at least one email was sent successfully
        """
        import asyncio
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from backend.shared.database import get_celery_session_factory
        from backend.domains.construction.models import ConstructionProject
        from backend.shared.models import User, user_project_access
        
        logger.info(
            f"[CRITICAL_EMAIL_START] project_id={project_id}, job_id={job_id}, "
            f"project_name={project_name}, status={risk_brief_status}"
        )
        
        async def _fetch_managers():
            """Async function to fetch managers from database."""
            session_factory = get_celery_session_factory()
            async with session_factory() as db:
                result = await db.execute(
                    select(ConstructionProject)
                    .options(
                        selectinload(ConstructionProject.manager),
                        selectinload(ConstructionProject.managers)
                    )
                    .where(ConstructionProject.id == project_id)
                )
                project = result.scalar_one_or_none()
                
                if not project:
                    logger.warning(f"[CRITICAL_EMAIL_NO_PROJECT] Project {project_id} not found for critical brief notification")
                    return None, []
                
                logger.info(
                    f"[CRITICAL_EMAIL_PROJECT_FOUND] Project found: id={project.id}, name={project.name}, "
                    f"manager_id={project.manager_id}, manager={project.manager}, "
                    f"managers_count={len(project.managers) if project.managers else 0}"
                )
                
                manager_emails = []
                db_project_name = project.name
                
                # Main manager (from manager_id field)
                if project.manager and project.manager.is_active:
                    logger.info(
                        f"[CRITICAL_EMAIL_MAIN_MANAGER] Manager: id={project.manager.id}, "
                        f"email={project.manager.email}, role={project.manager.role}, is_active={project.manager.is_active}"
                    )
                    if project.manager.role in RISK_BRIEF_ALLOWED_ROLES:
                        manager_emails.append(project.manager.email)
                        logger.info(f"[CRITICAL_EMAIL_ADDED] Added main manager: {project.manager.email}")
                    else:
                        logger.info(f"[CRITICAL_EMAIL_ROLE_SKIP] Main manager role '{project.manager.role}' not in allowed roles {RISK_BRIEF_ALLOWED_ROLES}")
                else:
                    logger.info(f"[CRITICAL_EMAIL_NO_MAIN_MANAGER] No active main manager for project {project_id}")
                
                # Additional managers from project_managers M2M table
                for mgr in project.managers:
                    logger.info(
                        f"[CRITICAL_EMAIL_M2M_MANAGER] Manager: id={mgr.id}, "
                        f"email={mgr.email}, role={mgr.role}, is_active={mgr.is_active}"
                    )
                    if mgr.is_active and mgr.role in RISK_BRIEF_ALLOWED_ROLES:
                        if mgr.email not in manager_emails:
                            manager_emails.append(mgr.email)
                            logger.info(f"[CRITICAL_EMAIL_ADDED] Added M2M manager: {mgr.email}")
                
                # ALSO check user_project_access table - users with access to project
                # who have manager/admin/superuser roles should receive notifications
                access_result = await db.execute(
                    select(User)
                    .join(user_project_access, User.id == user_project_access.c.user_id)
                    .where(user_project_access.c.project_id == project_id)
                    .where(User.is_active == True)
                    .where(User.role.in_(RISK_BRIEF_ALLOWED_ROLES))
                )
                access_users = access_result.scalars().all()
                
                for user in access_users:
                    logger.info(
                        f"[CRITICAL_EMAIL_ACCESS_USER] User with access: id={user.id}, "
                        f"email={user.email}, role={user.role}, is_active={user.is_active}"
                    )
                    if user.email not in manager_emails:
                        manager_emails.append(user.email)
                        logger.info(f"[CRITICAL_EMAIL_ADDED] Added user from access list: {user.email}")
                
                return db_project_name, manager_emails
        
        try:
            # Run async function in sync context
            try:
                db_project_name, manager_emails = asyncio.run(_fetch_managers())
            except RuntimeError:
                # Already in event loop - run in thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, _fetch_managers())
                    db_project_name, manager_emails = future.result()
            
            if db_project_name is None:
                return False
            
            if not manager_emails:
                logger.info(f"[CRITICAL_EMAIL_NO_MANAGERS] No managers to notify for project {project_id}")
                return False
            
            # Always use DB project name (from construction_projects table), 
            # fallback to AI-extracted name only if DB name is empty
            project_name = db_project_name or project_name
            
            # Build dashboard URL
            base_url = f"{self.config.url_scheme}://{self.config.server_name}"
            dashboard_link = dashboard_url or f"{base_url}/dashboard"
            
            # Create critical alert email
            msg = MIMEMultipart()
            msg['From'] = self.config.default_sender
            msg['To'] = ', '.join(manager_emails)
            msg['Subject'] = f"🔴 Критический риск-бриф: {project_name}"
            
            # Create critical alert body
            body = self._create_critical_alert_body(
                project_name=project_name,
                dashboard_link=dashboard_link,
                status=risk_brief_status,
            )
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            # Send
            success, error = self._send_email_with_retry(msg, manager_emails)
            if success:
                logger.info(
                    f"Critical risk brief alert sent to managers {manager_emails} "
                    f"for project {project_id}"
                )
                return True
            else:
                logger.error(f"Failed to send critical alert: {error}")
                return False
                
        except Exception as e:
            logger.exception(f"Error sending critical risk brief notification: {e}")
            return False

    def _create_email_body(
        self,
        job_id: str,
        project_name: Optional[str],
        output_files: Optional[dict],
    ) -> str:
        """Create HTML email body for report notification."""
        base_url = f"{self.config.url_scheme}://{self.config.server_name}"

        # Build file list
        files_list = ""
        if output_files:
            file_labels = {
                "transcript": "📄 Стенограмма (DOCX)",
                "tasks": "📋 Задачи (XLSX)", 
                "report": "📝 Отчёт (DOCX)",
                "risk_brief": "⚠️ Риск-бриф (PDF)",
                "analysis": "📊 Аналитика (DOCX)",
            }
            files_list = "<ul style='margin: 10px 0; padding-left: 20px;'>"
            for file_type, file_path in output_files.items():
                label = file_labels.get(file_type, file_type)
                file_name = Path(file_path).name if file_path else file_type
                files_list += f"<li style='margin: 5px 0;'>{label}</li>"
            files_list += "</ul>"

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 1.5; color: #333333; background-color: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 20px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden;">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #1a1a2e; padding: 20px 30px;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td>
                                        <span style="color: #ffffff; font-size: 20px; font-weight: bold;">Severin</span><span style="color: #e94560; font-size: 20px; font-weight: bold;">Autoprotocol</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 30px;">
                            <h2 style="margin: 0 0 20px 0; color: #1a1a2e; font-size: 18px;">Обработка завершена</h2>
                            
                            {f'<p style="margin: 0 0 15px 0;"><strong>Проект:</strong> {project_name}</p>' if project_name else ''}
                            
                            {f'<p style="margin: 0 0 10px 0;"><strong>Сгенерированные файлы:</strong></p>{files_list}' if files_list else ''}
                            
                            <p style="margin: 20px 0; color: #666666;">Файлы прикреплены к этому письму.</p>
                            
                            <!-- Button -->
                            <table cellpadding="0" cellspacing="0" style="margin: 25px 0;">
                                <tr>
                                    <td style="background-color: #e94560; border-radius: 6px;">
                                        <a href="{base_url}/job/{job_id}" style="display: inline-block; padding: 12px 24px; color: #ffffff; text-decoration: none; font-weight: bold;">
                                            Открыть результаты
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f8f8; padding: 20px 30px; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0; color: #999999; font-size: 12px;">
                                Это автоматическое уведомление от SeverinAutoprotocol.<br>
                                Если у вас есть вопросы, обратитесь к администратору системы.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    def _create_critical_alert_body(
        self,
        project_name: str,
        dashboard_link: str,
        status: str = "critical",
    ) -> str:
        """Create HTML email body for critical risk brief alert."""
        status_colors = {
            "critical": {"bg": "#dc3545", "label": "Критический"},
            "attention": {"bg": "#ffc107", "label": "Требует внимания"},
            "stable": {"bg": "#28a745", "label": "Стабильный"},
        }
        status_info = status_colors.get(status, status_colors["critical"])
        now = datetime.now().strftime("%d.%m.%Y %H:%M")

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 1.5; color: #333333; background-color: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 20px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden;">
                    <!-- Header with alert color -->
                    <tr>
                        <td style="background-color: {status_info['bg']}; padding: 20px 30px;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td>
                                        <span style="color: #ffffff; font-size: 20px; font-weight: bold;">⚠️ Критический риск-бриф</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 30px;">
                            <h2 style="margin: 0 0 20px 0; color: #1a1a2e; font-size: 18px;">Обнаружены критические риски</h2>
                            
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px;">
                                <tr>
                                    <td width="120" style="color: #666666;">Проект:</td>
                                    <td style="font-weight: bold;">{project_name}</td>
                                </tr>
                                <tr>
                                    <td width="120" style="color: #666666; padding-top: 10px;">Статус:</td>
                                    <td style="padding-top: 10px;">
                                        <span style="display: inline-block; background-color: {status_info['bg']}; color: #ffffff; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: bold;">
                                            {status_info['label']}
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td width="120" style="color: #666666; padding-top: 10px;">Дата:</td>
                                    <td style="padding-top: 10px;">{now}</td>
                                </tr>
                            </table>
                            
                            <p style="margin: 20px 0; padding: 15px; background-color: #fff3cd; border-left: 4px solid #ffc107; color: #856404;">
                                По результатам анализа совещания выявлены риски, требующие вашего внимания.
                                Пожалуйста, ознакомьтесь с подробностями в личном кабинете.
                            </p>
                            
                            <!-- Button -->
                            <table cellpadding="0" cellspacing="0" style="margin: 25px 0;">
                                <tr>
                                    <td style="background-color: #e94560; border-radius: 6px;">
                                        <a href="{dashboard_link}" style="display: inline-block; padding: 12px 24px; color: #ffffff; text-decoration: none; font-weight: bold;">
                                            Открыть дашборд
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f8f8; padding: 20px 30px; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0; color: #999999; font-size: 12px;">
                                <strong>SeverinAutoprotocol</strong> — система автоматической обработки протоколов совещаний.<br>
                                Это автоматическое уведомление. Если у вас есть вопросы, обратитесь к администратору.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

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


def send_critical_brief_to_managers(
    project_id: int,
    job_id: str,
    project_name: Optional[str] = None,
    risk_brief_status: str = "critical",
) -> bool:
    """
    Convenience function to send critical risk brief alert to project managers.
    
    Args:
        project_id: Construction project ID
        job_id: Transcription job ID  
        project_name: Project name for email
        risk_brief_status: Status level (critical, attention, stable)
        
    Returns:
        True if at least one email was sent successfully
    """
    return email_service.send_critical_risk_brief_to_managers(
        project_id=project_id,
        job_id=job_id,
        project_name=project_name,
        risk_brief_status=risk_brief_status,
    )
