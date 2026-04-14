"""Dispatcher used by the on-demand GitHub Actions workflow.

Reads an ACTION + PARAMS_JSON from the environment (set by the workflow),
runs the corresponding skill command, writes the JSON result to
`.dispatch/result.json` so Claude can read it back via the GitHub API,
and notifies the user over their configured channel.
"""
from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

from .client import SKILL_ROOT
from . import read_mail, send_mail, organize, calendar as cal, contacts, recap
from .notifier import notify

ACTIONS = {
    # read
    "inbox":     lambda p: read_mail.main(["inbox"] + _kv(p, ("folder", "limit"))),
    "unread":    lambda p: read_mail.main(["unread"] + _kv(p, ("folder", "limit"))),
    "search":    lambda p: read_mail.main(["search"] + _kv(p, ("folder", "query", "from", "since", "unread-only", "limit"))),
    "show":      lambda p: read_mail.main(["show"] + _kv(p, ("id", "folder"))),
    # send
    "send":      lambda p: send_mail.main(["send"] + _kv(p, ("to", "cc", "bcc", "subject", "body", "html", "attach", "draft"))),
    "reply":     lambda p: send_mail.main(["reply"] + _kv(p, ("id", "body", "html", "all"))),
    "forward":   lambda p: send_mail.main(["forward"] + _kv(p, ("id", "to", "body", "html"))),
    # organize
    "folders":   lambda p: organize.main(["folders"]),
    "mkdir":     lambda p: organize.main(["mkdir"] + _kv(p, ("name", "parent"))),
    "move":      lambda p: organize.main(["move"] + _kv(p, ("id", "to"))),
    "mark":      lambda p: organize.main(["mark"] + _kv(p, ("id", "read", "unread"))),
    "categorize": lambda p: organize.main(["categorize"] + _kv(p, ("id", "categories", "append"))),
    "delete":    lambda p: organize.main(["delete"] + _kv(p, ("id", "hard"))),
    # calendar / contacts
    "calendar":         lambda p: cal.main(["list"] + _kv(p, ("since", "days"))),
    "calendar_create":  lambda p: cal.main(["create"] + _kv(p, ("subject", "start", "duration", "location", "body", "attendees"))),
    "contacts":         lambda p: contacts.main(["list"] + _kv(p, ("limit",))),
    "contact_search":   lambda p: contacts.main(["search"] + _kv(p, ("query", "limit"))),
    "contact_create":   lambda p: contacts.main(["create"] + _kv(p, ("name", "email", "company"))),
    # recap
    "recap":     lambda p: recap.main(_kv(p, ("window", "limit", "notify", "dry-run"))),
}


def _kv(params: dict, allowed: tuple[str, ...]) -> list[str]:
    """Convert a params dict to argv flags, filtering to allowed keys."""
    argv: list[str] = []
    for key in allowed:
        if key not in params:
            continue
        value = params[key]
        flag = f"--{key}"
        if isinstance(value, bool):
            if value:
                argv.append(flag)
        elif isinstance(value, list):
            argv.append(flag)
            argv.extend(str(v) for v in value)
        else:
            argv.extend([flag, str(value)])
    return argv


def main() -> int:
    action = os.getenv("ACTION", "recap").strip()
    params_raw = os.getenv("PARAMS_JSON", "{}") or "{}"
    try:
        params = json.loads(params_raw)
    except json.JSONDecodeError as e:
        params = {}
        parse_error = str(e)
    else:
        parse_error = None

    if action not in ACTIONS:
        _write_result({
            "status": "error",
            "reason": f"unknown action {action!r}",
            "available": sorted(ACTIONS),
        })
        # Don't fail the workflow — still notify
        notify(f"*Exchange skill* — action inconnue: `{action}`", channel="auto")
        return 0

    # Capture the script's JSON stdout so we can persist it + show a summary
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            rc = ACTIONS[action](params)
    except SystemExit as e:
        rc = int(e.code) if isinstance(e.code, int) else 1
    except Exception as e:
        _write_result({"status": "error", "action": action, "exception": repr(e)})
        notify(f"*Exchange skill* — erreur `{action}`: `{e!r}`", channel="auto")
        return 0

    output = buf.getvalue().strip()
    result = {
        "status": "ok" if rc == 0 else "failed",
        "action": action,
        "params": params,
        "parse_error": parse_error,
        "rc": rc,
        "output": _maybe_json(output),
    }
    _write_result(result)

    # Short human summary for the notification channel (not every action needs a recap)
    if action != "recap":
        summary = _summarize(action, result)
        if summary:
            try:
                notify(summary, channel="auto")
            except Exception as e:
                # Notifier failure shouldn't kill the workflow
                print(f"notifier error: {e!r}", file=sys.stderr)
    return 0


def _maybe_json(text: str):
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _summarize(action: str, result: dict) -> str | None:
    out = result.get("output")
    if result["status"] != "ok":
        return f"*Exchange skill* — `{action}` a échoué (rc={result['rc']})"
    if isinstance(out, list):
        return f"*Exchange skill* — `{action}` : {len(out)} résultat(s)."
    if isinstance(out, dict) and "status" in out:
        return f"*Exchange skill* — `{action}` : {out.get('status')}"
    return None


def _write_result(obj: dict) -> None:
    path = SKILL_ROOT / ".dispatch" / "result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    sys.exit(main())
