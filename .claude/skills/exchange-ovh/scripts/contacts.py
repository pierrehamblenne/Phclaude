"""Contacts: list / search / create."""
from __future__ import annotations

import argparse
import sys

from exchangelib import Contact, EmailAddress, Q

from .client import emit, get_account


def _serialize(c: Contact) -> dict:
    return {
        "id": c.id,
        "display_name": c.display_name,
        "given_name": c.given_name,
        "surname": c.surname,
        "company_name": c.company_name,
        "email_addresses": [
            {"label": str(e.label), "email": e.email}
            for e in (c.email_addresses or [])
        ],
        "phone_numbers": [
            {"label": str(p.label), "phone": p.phone_number}
            for p in (c.phone_numbers or [])
        ],
    }


def cmd_list(args) -> int:
    account = get_account()
    qs = account.contacts.all().order_by("display_name")[: args.limit]
    emit([_serialize(c) for c in qs], args.json)
    return 0


def cmd_search(args) -> int:
    account = get_account()
    q = (
        Q(display_name__icontains=args.query)
        | Q(given_name__icontains=args.query)
        | Q(surname__icontains=args.query)
        | Q(company_name__icontains=args.query)
    )
    qs = account.contacts.filter(q)[: args.limit]
    emit([_serialize(c) for c in qs], args.json)
    return 0


def cmd_create(args) -> int:
    account = get_account()
    given, _, surname = args.name.partition(" ")
    contact = Contact(
        account=account,
        folder=account.contacts,
        given_name=given,
        surname=surname,
        display_name=args.name,
        company_name=args.company,
        email_addresses=[EmailAddress(email=args.email, label="EmailAddress1")] if args.email else None,
    )
    contact.save()
    emit({"status": "created", "id": contact.id, "name": args.name}, args.json)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="contacts")
    parser.add_argument("--json", action="store_true", default=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("search")
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("create")
    p.add_argument("--name", required=True, help="Full name 'Prénom Nom'")
    p.add_argument("--email", default=None)
    p.add_argument("--company", default=None)
    p.set_defaults(func=cmd_create)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
