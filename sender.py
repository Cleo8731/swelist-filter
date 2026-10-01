### sends the digest email that Claude wrote into today's output folder

import re
import smtplib
from email.mime.text import MIMEText

from config import (OUTPUT_DIR, DATE, SMTP_HOST, SMTP_PORT,
                    SMTP_USER, SMTP_PASSWORD, RECIPIENT)

SUBJECT_PATTERN = re.compile(r'<!--\s*SUBJECT:\s*(.+?)\s*-->')


def read_digest(path=None):
    if path is None:
        path = OUTPUT_DIR / 'digest.html'
    # utf-8 because the digest is full of em dashes and middots that
    # Windows' default cp1252 can't decode
    return path.read_text(encoding='utf-8')


def extract_subject(html):
    match = SUBJECT_PATTERN.search(html)
    if match:
        return match.group(1)
    return f"Internship digest - {DATE.isoformat()}"


def build_message(html, subject):
    msg = MIMEText(html, 'html', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = RECIPIENT
    return msg


def send_digest():
    html = read_digest()
    msg = build_message(html, extract_subject(html))
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
    print("Sent:", msg['Subject'])


def send_notice(subject, text):
    """A short, plain notice (e.g. 'No digest today'), so a failed run is not silent."""
    safe = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = ('<div style="max-width:640px;font-family:-apple-system,\'Segoe UI\','
            'Roboto,Helvetica,Arial,sans-serif;font-size:14px;line-height:1.5;'
            'color:#1f2328;background-color:#ffffff;padding:16px;">'
            '<div style="font-size:16px;font-weight:700;margin:0 0 6px;">%s</div>'
            '<div style="color:#5f6b73;">%s</div></div>' % (subject, safe))
    msg = build_message(html, subject)
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
    print("Sent notice:", subject)


if __name__ == "__main__":
    send_digest()