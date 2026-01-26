"""
Test email sending script - автоматически пробует разные конфигурации.

Usage:
    python scripts/test_email.py
"""
import sys
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env
from dotenv import load_dotenv
load_dotenv()


def test_and_send(server, port, use_tls, use_ssl, username, password, sender, recipient):
    """Test connection and send email if successful."""
    label = f"port={port}, TLS={use_tls}, SSL={use_ssl}"
    print(f"\n[TEST] {label}")

    try:
        if use_ssl:
            smtp = smtplib.SMTP_SSL(server, port, timeout=15)
        else:
            smtp = smtplib.SMTP(server, port, timeout=15)

        smtp.ehlo()

        if use_tls and not use_ssl:
            smtp.starttls()
            smtp.ehlo()

        smtp.login(username, password)
        print(f"  ✓ Connection & auth OK")

        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = 'Тестовое письмо от SeverinAutoprotocol'

        body = """
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #10b981;">Тестовое письмо</h2>
            <p>Это тестовое письмо от системы SeverinAutoprotocol.</p>
            <p>Если вы получили это письмо — email работает корректно!</p>
            <hr>
            <p style="color: #888; font-size: 12px;">
                Config: {label}
            </p>
        </body>
        </html>
        """.replace("{label}", label)
        msg.attach(MIMEText(body, 'html', 'utf-8'))

        smtp.sendmail(sender, [recipient], msg.as_string())
        smtp.quit()

        print(f"  ✓ EMAIL SENT TO {recipient}!")
        print(f"\n{'='*50}")
        print("WORKING CONFIG:")
        print(f"{'='*50}")
        print(f"MAIL_PORT={port}")
        print(f"MAIL_USE_TLS={'true' if use_tls else 'false'}")
        print(f"MAIL_USE_SSL={'true' if use_ssl else 'false'}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"  ✗ Auth error: {e}")
    except smtplib.SMTPConnectError as e:
        print(f"  ✗ Connect error: {e}")
    except smtplib.SMTPServerDisconnected as e:
        print(f"  ✗ Disconnected: {e}")
    except TimeoutError:
        print(f"  ✗ Timeout")
    except ConnectionRefusedError:
        print(f"  ✗ Connection refused")
    except Exception as e:
        print(f"  ✗ {type(e).__name__}: {e}")

    return False


def main():
    # Config from .env
    server = os.getenv("MAIL_SERVER", "mail.severindevelopment.ru")
    port = int(os.getenv("MAIL_PORT", "49587"))
    username = os.getenv("MAIL_USERNAME", "severin-ai-noreply@svrd.ru")
    password = os.getenv("MAIL_PASSWORD", "")
    sender = os.getenv("MAIL_DEFAULT_SENDER", username)

    recipient = "n.khromenok@svrd.ru"

    print("=" * 50)
    print("EMAIL TEST - AUTOMATIC CONFIG DETECTION")
    print("=" * 50)
    print(f"Server:    {server}")
    print(f"Username:  {username}")
    print(f"Recipient: {recipient}")

    if not password:
        print("\nERROR: MAIL_PASSWORD not set!")
        return

    # Configurations to try (ordered by likelihood)
    configs = [
        # Current config from .env
        (port, False, False, "Current .env config"),
        (port, True, False, "Current port + STARTTLS"),
        (port, False, True, "Current port + SSL"),
        # Standard ports
        (587, True, False, "Port 587 + STARTTLS (submission)"),
        (465, False, True, "Port 465 + SSL (smtps)"),
        (25, False, False, "Port 25 plain (relay)"),
        (25, True, False, "Port 25 + STARTTLS"),
    ]

    for p, tls, ssl, desc in configs:
        print(f"\n--- Trying: {desc} ---")
        if test_and_send(server, p, tls, ssl, username, password, sender, recipient):
            return  # Success!

    print("\n" + "=" * 50)
    print("ALL CONFIGS FAILED")
    print("=" * 50)
    print("Check:")
    print("  1. MAIL_SERVER is correct")
    print("  2. MAIL_USERNAME / MAIL_PASSWORD are valid")
    print("  3. Firewall allows outbound SMTP")
    print("  4. The mail server is reachable from this network")


if __name__ == "__main__":
    main()
