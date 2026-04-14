"""Calendar access over EWS: list events and create invites."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

from exchangelib import CalendarItem, EWSDateTime, Mailbox
from exchangelib.items import SEND_TO_ALL_AND_SAVE_COPY

from .client import emit, get_account, parse_window


def _iso(dt) -> str | None:
    if dt is None:
        return None
    return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)


def cmd_list(args) -> int:
    account = get_account()
    start = parse_window(args.since) if args.since else datetime.now(timezone.utc)
    # parse_window gives a past time for 'since'; for 'until' add days forward
    until = datetime.now(timezone.utc) + timedelta(days=int(args.days))
    view = account.calendar.view(
        start=EWSDateTime.from_datetime(start),
        end=EWSDateTime.from_datetime(until),
    )
    items = []
    for ev in view:
        items.append({
            "id": ev.id,
            "subject": ev.subject,
            "start": _iso(ev.start),
            "end": _iso(ev.end),
            "location": ev.location,
            "organizer": (ev.organizer.email_address if ev.organizer else None),
            "required_attendees": [
                a.mailbox.email_address for a in (ev.required_attendees or [])
            ],
            "is_cancelled": ev.is_cancelled,
            "is_all_day": ev.is_all_day,
        })
    emit(items, args.json)
    return 0


def cmd_create(args) -> int:
    account = get_account()
    start = datetime.fromisoformat(args.start)
    if start.tzinfo is None:
        start = start.astimezone()
    end = start + timedelta(minutes=int(args.duration))
    attendees = [Mailbox(email_address=a) for a in (args.attendees or [])]
    item = CalendarItem(
        account=account,
        folder=account.calendar,
        subject=args.subject,
        start=EWSDateTime.from_datetime(start.astimezone(timezone.utc)),
        end=EWSDateTime.from_datetime(end.astimezone(timezone.utc)),
        location=args.location,
        body=args.body or "",
        required_attendees=attendees,
    )
    item.save(send_meeting_invitations=SEND_TO_ALL_AND_SAVE_COPY)
    emit({"status": "created", "id": item.id, "subject": args.subject}, args.json)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="calendar")
    parser.add_argument("--json", action="store_true", default=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list")
    p.add_argument("--since", default="today", help="Window start (today, 1d, 24h...)")
    p.add_argument("--days", default="7", help="How many days forward to include")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("create")
    p.add_argument("--subject", required=True)
    p.add_argument("--start", required=True, help="ISO datetime, e.g. 2026-04-15T10:00")
    p.add_argument("--duration", default="30", help="Minutes")
    p.add_argument("--location", default=None)
    p.add_argument("--body", default=None)
    p.add_argument("--attendees", nargs="*", default=[])
    p.set_defaults(func=cmd_create)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
