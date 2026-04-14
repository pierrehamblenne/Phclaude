"""Read / search / sort the OVH Exchange mailbox."""
from __future__ import annotations

import argparse
import sys
from typing import Iterable

from exchangelib import Q

from .client import emit, fetch_item, get_account, parse_window, resolve_folder, to_ews_dt


FIELDS = (
    "id", "datetime_received", "subject", "sender", "is_read",
    "importance", "has_attachments", "categories",
)


def _serialize_item(item) -> dict:
    sender = None
    if getattr(item, "sender", None):
        sender = {"name": item.sender.name, "email": item.sender.email_address}
    return {
        "id": item.id,
        "received": item.datetime_received.isoformat() if item.datetime_received else None,
        "subject": item.subject,
        "sender": sender,
        "is_read": item.is_read,
        "importance": str(item.importance) if item.importance else None,
        "has_attachments": item.has_attachments,
        "categories": list(item.categories) if item.categories else [],
    }


def _collect(qs: Iterable, limit: int) -> list[dict]:
    out = []
    for item in qs.only(*FIELDS).order_by("-datetime_received")[:limit]:
        out.append(_serialize_item(item))
    return out


def cmd_inbox(args) -> int:
    account = get_account()
    folder = resolve_folder(account, args.folder)
    emit(_collect(folder.all(), args.limit), args.json)
    return 0


def cmd_unread(args) -> int:
    account = get_account()
    folder = resolve_folder(account, args.folder)
    emit(_collect(folder.filter(is_read=False), args.limit), args.json)
    return 0


def cmd_search(args) -> int:
    account = get_account()
    folder = resolve_folder(account, args.folder)
    q = None
    if args.query:
        q = Q(subject__icontains=args.query) | Q(body__icontains=args.query)
    if args.from_:
        fq = Q(sender__email_address__icontains=args.from_)
        q = fq if q is None else q & fq
    if args.since:
        since_dt = to_ews_dt(parse_window(args.since), account)
        sq = Q(datetime_received__gte=since_dt)
        q = sq if q is None else q & sq
    if args.unread_only:
        uq = Q(is_read=False)
        q = uq if q is None else q & uq
    qs = folder.filter(q) if q is not None else folder.all()
    emit(_collect(qs, args.limit), args.json)
    return 0


def cmd_show(args) -> int:
    account = get_account()
    item = fetch_item(account, args.id)
    data = _serialize_item(item)
    data["body"] = item.text_body or (item.body and str(item.body)) or ""
    data["to_recipients"] = [
        {"name": r.name, "email": r.email_address} for r in (item.to_recipients or [])
    ]
    data["cc_recipients"] = [
        {"name": r.name, "email": r.email_address} for r in (item.cc_recipients or [])
    ]
    if item.has_attachments:
        data["attachments"] = [
            {"name": a.name, "size": a.size, "content_type": getattr(a, "content_type", None)}
            for a in item.attachments
        ]
    emit(data, args.json)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="read_mail", description="Read/search OVH Exchange mailbox")
    parser.add_argument("--json", action="store_true", default=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("inbox", help="List most recent messages in a folder")
    p.add_argument("--folder", default="inbox")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_inbox)

    p = sub.add_parser("unread", help="List unread messages")
    p.add_argument("--folder", default="inbox")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_unread)

    p = sub.add_parser("search", help="Search messages")
    p.add_argument("--folder", default="inbox")
    p.add_argument("--query")
    p.add_argument("--from", dest="from_", help="Sender email contains")
    p.add_argument("--since", help="Time window: 24h, 7d, today...")
    p.add_argument("--unread-only", action="store_true")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("show", help="Show full message by id")
    p.add_argument("--id", required=True)
    p.add_argument("--folder", default="inbox")
    p.set_defaults(func=cmd_show)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
