"""Pluggable notification senders for the recap job.

Priority if --notify is 'auto' (default):
  1. Twilio WhatsApp  (if TWILIO_* vars set)
  2. Telegram bot     (if TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID set)
  3. Email fallback   (if NOTIFY_EMAIL_TO set — uses the EWS account itself)
"""
from __future__ import annotations

import os
from typing import Callable

import requests


def _has(*names) -> bool:
    return all(os.getenv(n) for n in names)


# -------- WhatsApp (Twilio) --------

def send_whatsapp(message: str) -> dict:
    sid = os.environ["TWILIO_ACCOUNT_SID"]
    token = os.environ["TWILIO_AUTH_TOKEN"]
    from_ = os.environ["TWILIO_WHATSAPP_FROM"]  # e.g. whatsapp:+14155238886
    to = os.environ["NOTIFY_WHATSAPP_TO"]       # e.g. whatsapp:+33612345678
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    resp = requests.post(
        url,
        data={"From": from_, "To": to, "Body": message},
        auth=(sid, token),
        timeout=30,
    )
    resp.raise_for_status()
    return {"channel": "whatsapp", "provider_sid": resp.json().get("sid")}


# -------- Telegram --------

def send_telegram(message: str) -> dict:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
        timeout=30,
    )
    resp.raise_for_status()
    return {"channel": "telegram", "message_id": resp.json().get("result", {}).get("message_id")}


# -------- Email fallback (via the Exchange account itself) --------

def send_email(message: str, subject: str = "Exchange recap") -> dict:
    from exchangelib import Mailbox, Message as ExMessage

    from .client import get_account

    to = os.environ["NOTIFY_EMAIL_TO"]
    account = get_account()
    msg = ExMessage(
        account=account,
        subject=subject,
        body=message,
        to_recipients=[Mailbox(email_address=to)],
    )
    msg.send_and_save()
    return {"channel": "email", "id": msg.id}


# -------- dispatcher --------

CHANNELS: dict[str, Callable[[str], dict]] = {
    "whatsapp": send_whatsapp,
    "telegram": send_telegram,
    "email": send_email,
}


def auto_channel() -> str | None:
    if _has("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM", "NOTIFY_WHATSAPP_TO"):
        return "whatsapp"
    if _has("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        return "telegram"
    if _has("NOTIFY_EMAIL_TO"):
        return "email"
    return None


def notify(message: str, channel: str = "auto") -> dict:
    if channel == "auto":
        resolved = auto_channel()
        if resolved is None:
            return {"channel": "none", "reason": "no notifier configured", "preview": message[:400]}
        channel = resolved
    if channel not in CHANNELS:
        raise SystemExit(f"Unknown notify channel: {channel}")
    return CHANNELS[channel](message)
