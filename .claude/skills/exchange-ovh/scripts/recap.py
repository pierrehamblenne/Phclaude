"""Produce a recap of recent inbox activity and push it to WhatsApp/Telegram/email.

Meant to run 3x/day via GitHub Actions cron (see .github/workflows/exchange-recap.yml)
or any other scheduler. The state file tracks the last run so we only summarize
messages received since the previous recap.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from exchangelib import EWSDateTime, Q

from .client import SKILL_ROOT, emit, get_account, parse_window
from .notifier import notify

STATE_PATH = SKILL_ROOT / ".state" / "last_recap.json"

URGENT_KEYWORDS = (
    "urgent", "asap", "immediat", "relance", "impayé", "impaye",
    "résiliation", "resiliation", "rdv", "rendez-vous", "facture",
    "paiement", "password", "mot de passe", "action required",
)


def _priority(subject: str, body_preview: str) -> str:
    haystack = f"{subject} {body_preview}".lower()
    if any(k in haystack for k in URGENT_KEYWORDS):
        return "HIGH"
    return "NORMAL"


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, default=str, indent=2))


def _window_start(args, state: dict) -> datetime:
    if args.window == "since-last-recap":
        last = state.get("last_run_utc")
        if last:
            return datetime.fromisoformat(last)
        # First run: default to last 8h
        return datetime.now(timezone.utc) - timedelta(hours=8)
    return parse_window(args.window)


def _preview(item) -> str:
    raw = item.text_body or (str(item.body) if item.body else "") or ""
    # Strip consecutive whitespace and cap length
    compact = " ".join(raw.split())
    return compact[:140]


def build_recap(args) -> dict:
    account = get_account()
    state = _load_state()
    start = _window_start(args, state)
    since_ews = EWSDateTime.from_datetime(start.astimezone(timezone.utc))

    qs = account.inbox.filter(Q(datetime_received__gte=since_ews)).only(
        "id", "subject", "sender", "datetime_received", "is_read", "importance", "body", "text_body"
    ).order_by("-datetime_received")[: args.limit]

    items = []
    for msg in qs:
        sender_name = msg.sender.name if msg.sender else "(inconnu)"
        sender_email = msg.sender.email_address if msg.sender else ""
        preview = _preview(msg)
        items.append({
            "id": msg.id,
            "received": msg.datetime_received.isoformat() if msg.datetime_received else None,
            "sender": f"{sender_name} <{sender_email}>".strip(),
            "subject": msg.subject or "(sans objet)",
            "preview": preview,
            "is_read": msg.is_read,
            "priority": _priority(msg.subject or "", preview),
        })

    high = [i for i in items if i["priority"] == "HIGH"]
    unread = [i for i in items if not i["is_read"]]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_start": start.isoformat(),
        "total_new": len(items),
        "unread_count": len(unread),
        "high_priority_count": len(high),
        "items": items,
        "state": state,
    }


def format_message(recap: dict) -> str:
    header = (
        f"*Récap Exchange* — {recap['total_new']} nouveaux mail(s) "
        f"({recap['unread_count']} non lus, {recap['high_priority_count']} prioritaires)"
    )
    if recap["total_new"] == 0:
        return header + "\n\nRien depuis le dernier récap."

    lines = [header, ""]
    # Prioritized first, then others
    ordered = sorted(recap["items"], key=lambda i: (i["priority"] != "HIGH", i["received"]), reverse=False)
    ordered.sort(key=lambda i: (i["priority"] != "HIGH", -(datetime.fromisoformat(i["received"]).timestamp() if i["received"] else 0)))
    for i in ordered[:15]:
        prio = "🔴" if i["priority"] == "HIGH" else ("🟢" if i["is_read"] else "🟡")
        lines.append(f"{prio} *{i['subject'][:70]}*")
        lines.append(f"   de {i['sender'][:60]}")
        if i["preview"]:
            lines.append(f"   _{i['preview'][:100]}_")
        lines.append("")
    if len(ordered) > 15:
        lines.append(f"… et {len(ordered) - 15} autres.")
    return "\n".join(lines).strip()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="recap")
    parser.add_argument("--window", default="since-last-recap",
                        help="since-last-recap | 8h | 24h | today")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--notify", default="auto",
                        choices=["auto", "whatsapp", "telegram", "email", "none"])
    parser.add_argument("--dry-run", action="store_true",
                        help="Build the recap but do not send, do not advance state")
    parser.add_argument("--json", action="store_true", default=True)
    args = parser.parse_args(argv)

    recap = build_recap(args)
    message = format_message(recap)

    result = {"recap": recap, "message": message}

    if args.notify != "none" and not args.dry_run:
        result["notification"] = notify(message, channel=args.notify)

    if not args.dry_run:
        _save_state({"last_run_utc": recap["generated_at"]})

    # Always emit the message to stdout for log visibility
    if not os.getenv("EXCHANGE_SKILL_QUIET"):
        print(message)
        print("---")
    emit(result, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
