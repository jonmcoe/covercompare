"""email_delivery.py — send combined covers as an inline HTML email via SMTP.

Required environment variables:
    SMTP_HOST         — e.g. smtp-relay.brevo.com
    SMTP_USER         — SMTP login (Brevo account email)
    SMTP_PASSWORD     — SMTP API key / password
    SMTP_FROM_EMAIL   — verified sender address
    SMTP_PORT         — optional, defaults to 587
    SMTP_FROM_NAME    — optional sender display name, defaults to 'CoverCompare'
    COVERCOMPARE_BASE_URL — base URL for unsubscribe links, e.g. https://covercompare.io
"""

import os
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _smtp_config():
    return {
        'host': os.environ['SMTP_HOST'],
        'port': int(os.environ.get('SMTP_PORT', '587')),
        'user': os.environ['SMTP_USER'],
        'password': os.environ['SMTP_PASSWORD'],
        'from_email': os.environ['SMTP_FROM_EMAIL'],
        'from_name': os.environ.get('SMTP_FROM_NAME', 'CoverCompare'),
    }


def _format_date(d):
    """Format date as 'Friday, February 28 2026'."""
    return d.strftime('%A, %B %-d %Y')


def send(path, date, to_email, label, sub_id, extra_note=''):
    """Send the combined cover image as an inline HTML email.

    Args:
        path: filesystem path to the combined JPEG image
        date: datetime.date for the edition
        to_email: recipient email address
        label: optional string used to customize the subject line
        sub_id: integer subscription ID (used in unsubscribe link)
        extra_note: optional plain-text warning prepended to the body (e.g. missed papers)

    Raises:
        RuntimeError or smtplib exception on failure.
    """
    cfg = _smtp_config()
    base_url = os.environ.get('COVERCOMPARE_BASE_URL', 'https://covercompare.io')
    unsubscribe_url = f'{base_url}/unsubscribe?id={sub_id}'

    formatted_date = _format_date(date)
    if label:
        subject = f'CoverCompare \u2014 {label} \u00b7 {formatted_date}'
    else:
        subject = f'CoverCompare \u2014 {formatted_date}'

    plain_body = (
        f"{extra_note}"
        f"Today's newspaper covers: {formatted_date}\n\n"
        f"Unsubscribe: {unsubscribe_url}"
    )

    extra_html = f'<p style="margin:0 0 16px;font-size:13px;color:#e07;">{extra_note.strip()}</p>\n  ' if extra_note else ''
    html_body = f"""\
<!DOCTYPE html>
<html>
<body style="margin:0;padding:20px;background:#111;font-family:sans-serif;color:#eee;">
  {extra_html}<p style="margin:0 0 16px;font-size:14px;color:#aaa;">{formatted_date}</p>
  <img src="cid:cover_image" style="max-width:100%;display:block;border:0;" alt="Today's newspaper covers">
  <p style="margin:24px 0 0;font-size:12px;color:#666;">
    <a href="{unsubscribe_url}" style="color:#888;">Unsubscribe</a>
  </p>
</body>
</html>"""

    with open(path, 'rb') as f:
        image_data = f.read()

    reply_to = os.environ.get('SMTP_REPLY_TO')

    msg = MIMEMultipart('related')
    msg['Subject'] = subject
    msg['From'] = f'{cfg["from_name"]} <{cfg["from_email"]}>'
    msg['To'] = to_email
    if reply_to:
        msg['Reply-To'] = reply_to

    alt = MIMEMultipart('alternative')
    alt.attach(MIMEText(plain_body, 'plain'))
    alt.attach(MIMEText(html_body, 'html'))
    msg.attach(alt)

    img = MIMEImage(image_data, 'jpeg')
    img.add_header('Content-ID', '<cover_image>')
    img.add_header('Content-Disposition', 'inline', filename='covers.jpg')
    msg.attach(img)

    with smtplib.SMTP(cfg['host'], cfg['port']) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(cfg['user'], cfg['password'])
        smtp.sendmail(cfg['from_email'], to_email, msg.as_string())
