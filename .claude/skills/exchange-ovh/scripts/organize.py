"""Organize folders, move/mark/categorize messages."""
from __future__ import annotations

import argparse
import sys

from exchangelib import Folder

from .client import emit, fetch_item, get_account, resolve_folder


def cmd_folders(args) -> int:
    account = get_account()
    tree = []

    def walk(folder, depth=0):
        tree.append({
            "name": folder.name,
            "depth": depth,
            "total": folder.total_count,
            "unread": getattr(folder, "unread_count", None),
        })
        for child in folder.children:
            walk(child, depth + 1)

    walk(account.inbox.parent)
    emit(tree, args.json)
    return 0


def cmd_mkdir(args) -> int:
    account = get_account()
    parent = resolve_folder(account, args.parent)
    new = Folder(parent=parent, name=args.name)
    new.save()
    emit({"status": "created", "name": args.name, "parent": args.parent}, args.json)
    return 0


def cmd_move(args) -> int:
    account = get_account()
    target = resolve_folder(account, args.to)
    item = fetch_item(account, args.id)
    item.move(target)
    emit({"status": "moved", "id": args.id, "to": args.to}, args.json)
    return 0


def cmd_mark(args) -> int:
    account = get_account()
    item = fetch_item(account, args.id)
    if args.read and args.unread:
        raise SystemExit("Pick only one of --read / --unread")
    if not args.read and not args.unread:
        raise SystemExit("Pick one of --read / --unread")
    item.is_read = bool(args.read)
    item.save(update_fields=["is_read"])
    emit({"status": "marked", "id": args.id, "is_read": item.is_read}, args.json)
    return 0


def cmd_categorize(args) -> int:
    account = get_account()
    item = fetch_item(account, args.id)
    cats = [c.strip() for c in args.categories.split(",") if c.strip()]
    if args.append:
        existing = list(item.categories or [])
        cats = sorted(set(existing + cats))
    item.categories = cats
    item.save(update_fields=["categories"])
    emit({"status": "categorized", "id": args.id, "categories": cats}, args.json)
    return 0


def cmd_delete(args) -> int:
    account = get_account()
    item = fetch_item(account, args.id)
    if args.hard:
        item.delete()
        emit({"status": "hard_deleted", "id": args.id}, args.json)
    else:
        item.move_to_trash()
        emit({"status": "moved_to_trash", "id": args.id}, args.json)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="organize")
    parser.add_argument("--json", action="store_true", default=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("folders").set_defaults(func=cmd_folders)

    p = sub.add_parser("mkdir")
    p.add_argument("--name", required=True)
    p.add_argument("--parent", default="inbox")
    p.set_defaults(func=cmd_mkdir)

    p = sub.add_parser("move")
    p.add_argument("--id", required=True)
    p.add_argument("--to", required=True, help="Destination folder path")
    p.set_defaults(func=cmd_move)

    p = sub.add_parser("mark")
    p.add_argument("--id", required=True)
    p.add_argument("--read", action="store_true")
    p.add_argument("--unread", action="store_true")
    p.set_defaults(func=cmd_mark)

    p = sub.add_parser("categorize")
    p.add_argument("--id", required=True)
    p.add_argument("--categories", required=True, help="Comma-separated list")
    p.add_argument("--append", action="store_true", help="Append rather than replace")
    p.set_defaults(func=cmd_categorize)

    p = sub.add_parser("delete")
    p.add_argument("--id", required=True)
    p.add_argument("--hard", action="store_true", help="Permanent delete (skip trash)")
    p.set_defaults(func=cmd_delete)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
