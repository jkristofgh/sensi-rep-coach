#!/usr/bin/env python3
"""Routing adapters — the production seam.

The scoring core never talks to Slack/HubSpot directly; it calls these narrow interfaces. In the
prototype the Mock* implementations write to data/routing_log.json (so the demo can *show* the loop
routing). In production the same interfaces are implemented by SlackNotifier / HubSpotCRM — the
core doesn't change. This is the exact seam that becomes "HubSpot as the single surface" (Phase 3).
"""
import datetime
import json
from pathlib import Path
from typing import Protocol

HERE = Path(__file__).resolve().parent
LOG = HERE / "data" / "routing_log.json"


class Notifier(Protocol):
    def send_nudge(self, ctx: dict, content: str) -> None: ...


class CRM(Protocol):
    def create_task(self, ctx: dict, content: str) -> str: ...
    def attach_scorecard(self, ctx: dict, content: str) -> None: ...


# `ctx` is the call attribution every activity is tagged with:
#   {rep_id, rep_name, product, account, call_id}
# so the Activity view can show one line per activity with full context.

def _append(endpoint: str, action: str, ctx: dict, content: str):
    entry = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "endpoint": endpoint, "action": action,
        "rep_id": ctx.get("rep_id"), "rep_name": ctx.get("rep_name"),
        "product": ctx.get("product"), "account": ctx.get("account"),
        "call_id": ctx.get("call_id"), "content": content,
    }
    data = json.loads(LOG.read_text()) if LOG.exists() and LOG.read_text().strip() else []
    data.append(entry)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(data, indent=2))
    return entry


class MockNotifier:
    channel = "#sales-coaching"

    def send_nudge(self, ctx, content):
        return _append("slack", "nudge", ctx, content)


class MockCRM:
    def create_task(self, ctx, content):
        _append("hubspot", "task", ctx, content)
        return f"task_{len(load_log())}"

    def attach_scorecard(self, ctx, content):
        return _append("hubspot", "scorecard", ctx, content)


def seed_from_evals(evals):
    """Populate the routing log with the activities each SCORED call would have routed (Slack
    nudge + HubSpot scorecard + coaching task), backdated to the call date — so the Activity views
    are populated by default. No-op if a log already exists (live-processed calls append to it).
    Deterministic; matches the content the app's route_slack/route_hubspot produce at runtime."""
    if LOG.exists() and LOG.read_text().strip():
        return
    log = []
    for ev in sorted(evals, key=lambda e: (e.get("date", ""), e["call_id"])):
        focus = sorted(ev["dimensions"], key=lambda d: d["score"])[:2]
        ct = ev["call_type"].replace("_", " ")
        base = {"rep_id": ev["rep_id"], "rep_name": ev.get("rep_name"), "product": ev["product"],
                "account": ev.get("account"), "call_id": ev["call_id"]}
        date = ev.get("date", "")
        log += [
            {"ts": f"{date}T09:00:00", "endpoint": "slack", "action": "nudge", **base,
             "content": f"{ct} call scored {ev['overall']}/100 — top fix: {focus[0]['label']}."},
            {"ts": f"{date}T09:00:01", "endpoint": "hubspot", "action": "scorecard", **base,
             "content": f"Scorecard {ev['overall']}/100 attached to the call record"},
            {"ts": f"{date}T09:00:02", "endpoint": "hubspot", "action": "task", **base,
             "content": f"Coaching: {focus[0]['label']} — due in 3 days"},
        ]
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(log, indent=2))


def load_log():
    if LOG.exists() and LOG.read_text().strip():
        return json.loads(LOG.read_text())
    return []


def clear_log():
    if LOG.exists():
        LOG.unlink()


# ---- production stubs (documented; not wired in the prototype) ---------------
#
# class SlackNotifier:      # uses the Slack Web API; nudge deep-links to the HubSpot record
#     def send_nudge(self, rep_id, message, link): ...
#
# class HubSpotCRM:         # UI-Extension card on the call record + Workflows-routed tasks
#     def create_task(self, owner, title, due, related_to): ...
#     def attach_scorecard(self, call_id, evaluation): ...
