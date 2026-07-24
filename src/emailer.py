"""Sends the digest by email over SMTP.

Works with Gmail (use an App Password, not your normal password:
https://myaccount.google.com/apppasswords) or any other SMTP provider.
Needs SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS in the environment.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import markdown as md


def send_digest_email(subject, markdown_body, to_address, from_name, bcc=None, reply_to=None):
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{user}>"
    msg["To"] = to_address
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.attach(MIMEText(markdown_body, "plain"))
    msg.attach(MIMEText(md.markdown(markdown_body), "html"))

    # Bcc recipients get the mail too, but never appear in the headers
    # the primary recipient sees -- useful if you want a silent copy for
    # yourself to keep an eye on whether it's working.
    all_recipients = [to_address] + (bcc or [])

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(user, all_recipients, msg.as_string())
