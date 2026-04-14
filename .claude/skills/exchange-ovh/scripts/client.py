"""EWS client wrapper for OVH-hosted Exchange.

OVH Exchange supports EWS (SOAP) but usually NOT Autodiscover via the user's
domain — the endpoint must be set explicitly. Default server is ex.mail.ovh.net;
some tenants land on ex3.mail.ovh.net or mail.ovh.net.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from exchangelib import (
    Account,
    Configuration,
    Credentials,
    DELEGATE,
    EWSDateTime,
    EWSTimeZone,
)
from exchangelib.protocol import BaseProtocol, NoVerifyHTTPAdapter

# Load .env from skill root (parent of scripts/)
SKILL_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(SKILL_ROOT / ".env")

# OVH Exchange has a valid cert chain; keep verification ON by default. If a
# particular OVH plan ships a self-signed intermediate, toggle this via env.
if os.getenv("OVH_SKIP_TLS_VERIFY", "").lower() in ("1", "true", "yes"):
    BaseProtocol.HTTP_ADAPTER_CLS = NoVerifyHTTPAdapter


def _resolve_timezone(tz_name: str) -> EWSTimeZone:
    try:
        return EWSTimeZone(tz_name)
    except Exception:
        # Fallback to UTC if the IANA name can't be resolved on this host.
        return EWSTimeZone("UTC")


def get_account() -> Account:
    """Return an authenticated Account bound to the user's OVH mailbox."""
    email = os.getenv("OVH_EMAIL")
    password = os.getenv("OVH_PASSWORD")
    server = os.getenv("OVH_EWS_SERVER", "ex.mail.ovh.net")
    tz_name = os.getenv("OVH_TIMEZONE", "Europe/Paris")

    if not email or not password:
        raise SystemExit(
            "Missing OVH_EMAIL or OVH_PASSWORD in environment. "
            f"Populate {SKILL_ROOT / '.env'} or export the vars."
        )

    creds = Credentials(username=email, password=password)
    config = Configuration(server=server, credentials=creds)
    return Account(
        primary_smtp_address=email,
        config=config,
        autodiscover=False,
        access_type=DELEGATE,
        default_timezone=_resolve_timezone(tz_name),
    )


# ---------- helpers used by every other script ----------

def parse_window(spec: str) -> datetime:
    """Parse a shorthand like '24h', '7d', 'today', '30m' into a UTC datetime."""
    now = datetime.now(timezone.utc)
    spec = (spec or "").strip().lower()
    if not spec:
        return now - timedelta(days=1)
    if spec == "today":
        local = datetime.now().astimezone()
        midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight.astimezone(timezone.utc)
    if spec == "yesterday":
        local = datetime.now().astimezone()
        midnight = local.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        return midnight.astimezone(timezone.utc)
    unit = spec[-1]
    try:
        value = int(spec[:-1])
    except ValueError:
        raise SystemExit(f"Cannot parse time window: {spec!r}")
    if unit == "m":
        return now - timedelta(minutes=value)
    if unit == "h":
        return now - timedelta(hours=value)
    if unit == "d":
        return now - timedelta(days=value)
    raise SystemExit(f"Unknown unit in window: {spec!r} (use m/h/d)")


def to_ews_dt(dt: datetime, account: Account) -> EWSDateTime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return EWSDateTime.from_datetime(dt.astimezone(timezone.utc))


def emit(obj, as_json: bool) -> None:
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, default=str, indent=2))
    else:
        if isinstance(obj, (dict, list)):
            print(json.dumps(obj, ensure_ascii=False, default=str, indent=2))
        else:
            print(obj)


def resolve_folder(account: Account, path: Optional[str]):
    """Resolve a slash-separated folder path like 'Inbox/Factures'."""
    if not path or path.lower() == "inbox":
        return account.inbox
    parts = [p for p in path.split("/") if p]
    # Try the common case first: relative to Inbox
    try:
        inbox_try = account.inbox
        for p in parts:
            inbox_try = inbox_try / p
        _ = inbox_try.total_count  # trigger resolution
        return inbox_try
    except Exception:
        pass
    # Fallback: relative to msg root
    current = account.root / "Top of Information Store"
    for p in parts:
        current = current / p
    return current


def fetch_item(account: Account, item_id: str):
    """Fetch a Message (or generic Item) by ID across the whole mailbox.

    Works regardless of which folder currently holds it. Returns a refreshed item.
    """
    from exchangelib import Message as _Message  # local import to avoid cycles

    item = _Message(account=account, id=item_id)
    item.refresh()
    return item


# ---------- CLI entrypoint for quick health check ----------

def _cli() -> int:
    parser = argparse.ArgumentParser(description="OVH Exchange EWS client helper")
    parser.add_argument("--test", action="store_true", help="Test connection and print mailbox summary")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.test:
        account = get_account()
        info = {
            "email": account.primary_smtp_address,
            "server": account.protocol.service_endpoint,
            "inbox_total": account.inbox.total_count,
            "inbox_unread": account.inbox.unread_count,
            "folders_top_level": [f.name for f in account.inbox.parent.children],
        }
        emit(info, args.json or True)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
