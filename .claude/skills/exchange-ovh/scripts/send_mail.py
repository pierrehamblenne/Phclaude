"""Send, reply, forward via OVH Exchange EWS."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from exchangelib import FileAttachment, HTMLBody, Mailbox, Message

from .client import emit, fetch_item, get_account


def _recipients(addresses):
    if not addresses:
        return []
    return [Mailbox(email_address=a) for a in addresses]


def _attach(msg: Message, paths):
    for p in paths or []:
        path = Path(p).expanduser().resolve()
        with open(path, "rb") as fh:
            msg.attach(FileAttachment(name=path.name, content=fh.read()))


def cmd_send(args) -> int:
    account = get_account()
    body = HTMLBody(args.body) if args.html else args.body
    msg = Message(
        account=account,
        subject=args.subject,
        body=body,
        to_recipients=_recipients(args.to),
        cc_recipients=_recipients(args.cc),
        bcc_recipients=_recipients(args.bcc),
    )
    _attach(msg, args.attach)
    if args.draft:
        msg.save()
        emit({"status": "draft_saved", "id": msg.id}, args.json)
    else:
        msg.send_and_save()
        emit({"status": "sent", "id": msg.id}, args.json)
    return 0


def cmd_reply(args) -> int:
    account = get_account()
    original = fetch_item(account, args.id)
    body = HTMLBody(args.body) if args.html else args.body
    if args.all:
        original.reply_all(subject=f"Re: {original.subject}", body=body)
    else:
        original.reply(subject=f"Re: {original.subject}", body=body)
    emit({"status": "replied", "original_id": args.id, "reply_all": args.all}, args.json)
    return 0


def cmd_forward(args) -> int:
    account = get_account()
    original = fetch_item(account, args.id)
    body = HTMLBody(args.body) if args.html else args.body
    original.forward(
        subject=f"Fwd: {original.subject}",
        body=body,
        to_recipients=_recipients(args.to),
    )
    emit({"status": "forwarded", "original_id": args.id, "to": args.to}, args.json)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="send_mail")
    parser.add_argument("--json", action="store_true", default=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("send")
    p.add_argument("--to", nargs="+", required=True)
    p.add_argument("--cc", nargs="*", default=[])
    p.add_argument("--bcc", nargs="*", default=[])
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--html", action="store_true")
    p.add_argument("--attach", nargs="*", default=[], help="File paths to attach")
    p.add_argument("--draft", action="store_true", help="Save as draft instead of sending")
    p.set_defaults(func=cmd_send)

    p = sub.add_parser("reply")
    p.add_argument("--id", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--html", action="store_true")
    p.add_argument("--all", action="store_true", help="Reply all")
    p.set_defaults(func=cmd_reply)

    p = sub.add_parser("forward")
    p.add_argument("--id", required=True)
    p.add_argument("--to", nargs="+", required=True)
    p.add_argument("--body", default="")
    p.add_argument("--html", action="store_true")
    p.set_defaults(func=cmd_forward)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
