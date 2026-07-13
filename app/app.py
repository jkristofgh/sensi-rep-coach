#!/usr/bin/env python3
"""Rep Coach — Streamlit UI.

A call list → call detail workflow driven by a user picker (no sidebar):
  pick a rep     — My Calls (own calls → scorecard detail) · Trends
  pick a manager — Calls (all reps) · Team (rollup + escalation + coaching) · Trends · Measurement

Each call opens (via a per-row Details / Process button) a detail page: the visual scorecard,
overall summary, Coach's next steps, and the per-call integration activity. An unscored call's
Process button runs the whole pipeline live (the manual stand-in for production's automated
post-call trigger) and auto-routes to Slack + HubSpot. Live-processed results live in session
state — the committed dataset stays reproducible.

Prototype: synthetic data, CRM/Slack mocked. Run:  streamlit run app.py
"""
import html
import json
import os
import warnings
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

import adapters
import scoring

# Harmless forward-compat noise from altair (used by st.line_chart) passing a narwhals frame.
warnings.filterwarnings("ignore", message=r"You passed a `narwhals", category=UserWarning)

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

st.set_page_config(page_title="Rep Coach", page_icon="🎯", layout="wide")

# Collapse the (now-empty) fixed toolbar, pull content up, and enlarge the nav tab labels.
st.markdown(
    "<style>"
    "[data-testid='stHeader']{height:0;}"
    ".block-container{padding-top:1.5rem;}"
    ".stTabs [data-baseweb='tab-list'] button p{font-size:1.12rem;font-weight:600;}"
    ".stTabs [data-baseweb='tab-list'] button{padding-top:6px;padding-bottom:6px;}"
    "</style>", unsafe_allow_html=True)


# ---- data -------------------------------------------------------------------

@st.cache_data
def load_all():
    rubric = yaml.safe_load((HERE / "rubric.yaml").read_text())
    personas = yaml.safe_load((HERE / "personas.yaml").read_text())
    evals = [json.loads(p.read_text()) for p in sorted((DATA / "evaluations").glob("*.json"))]
    history = json.loads((DATA / "history.json").read_text())
    dim_order = [d["key"] for d in rubric["dimensions"]]
    dim_label = {d["key"]: d["label"] for d in rubric["dimensions"]}
    reps = {r["id"]: r for r in personas["reps"]}
    return rubric, personas, evals, history, dim_order, dim_label, reps


RUBRIC, PERSONAS_CFG, EVALS, HISTORY, DIM_ORDER, DIM_LABEL, REPS = load_all()
CORE_DIMS = ["motion_adherence", "discovery_quality", "proof_fidelity", "buying_signal", "next_step"]
ENDPOINT_LABEL = {"slack": "Slack", "hubspot": "HubSpot"}


def ctx_of(e):
    """Attribution tagged onto every routed activity."""
    return {"rep_id": e["rep_id"], "rep_name": e.get("rep_name") or REPS[e["rep_id"]]["name"],
            "product": e["product"], "account": e.get("account", "—"), "call_id": e["call_id"]}


def score_color(s):
    return "#2e7d32" if s >= 4 else "#e8a33d" if s >= 2.5 else "#c62828"


def band(overall):
    return "#2e7d32" if overall >= 70 else "#e8a33d" if overall >= 45 else "#c62828"


def band_label(overall):
    """(label, color) for an overall 0–100 score."""
    if overall >= 70:
        return "Strong", "#3aa657"
    if overall >= 45:
        return "Solid", "#e8a33d"
    return "Needs work", "#e5645a"


def dim_row(d):
    """One framed dimension cell: label + colored score chip + evidence quote(s) + tip."""
    c = score_color(d["score"])
    chip = (f'<span style="background:{c}22;color:{c};font-weight:700;font-size:0.82rem;'
            f'padding:2px 10px;border-radius:999px;font-variant-numeric:tabular-nums">'
            f'{d["score"]:.1f}<span style="opacity:.55;font-weight:600"> /5</span></span>')
    ev = "".join(
        f'<div style="color:#9aa7b3;font-size:0.82rem;font-style:italic;margin-top:4px">'
        f'“{html.escape(q)}”</div>' for q in d.get("evidence", []))
    tip = (f'<div style="color:#d4dbe3;font-size:0.82rem;margin-top:3px">💡 '
           f'{html.escape(d["tip"])}</div>' if d.get("tip") else "")
    st.markdown(
        f'<div style="background:#171c24;border:1px solid #242b35;border-radius:8px;'
        f'padding:11px 13px;margin-bottom:11px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;font-size:0.9rem">'
        f'<span><b>{html.escape(d["label"])}</b> '
        f'<span style="color:#8a97a3">· {d["signal"]}</span></span>{chip}</div>'
        f'{ev}{tip}</div>',
        unsafe_allow_html=True)


def rep_evals(rid):
    return sorted([e for e in EVALS if e["rep_id"] == rid], key=lambda e: e["date"], reverse=True)


def hist_df():
    df = pd.DataFrame(HISTORY)
    df["date"] = pd.to_datetime(df["date"])
    return df


def rep_trend(rid):
    """▲/▬/▼ from first-2-weeks vs last-2-weeks history overall."""
    d = hist_df()
    d = d[d["rep_id"] == rid].sort_values("date")
    if len(d) < 4:
        return "▬"
    first = d.head(max(2, len(d) // 3))["overall"].mean()
    last = d.tail(max(2, len(d) // 3))["overall"].mean()
    return "▲" if last - first > 4 else "▼" if last - first < -4 else "▬"


# ---- users (the picker: managers + reps) ------------------------------------

MANAGERS = PERSONAS_CFG.get("managers", [])
# Managers first so the demo opens on the team view; then the reps.
USERS = ([{"id": m["id"], "name": m["name"], "role": "manager", "title": m.get("title", "Manager")}
          for m in MANAGERS]
         + [{"id": rid, "name": REPS[rid]["name"], "role": "rep"} for rid in REPS])
USER_BY_ID = {u["id"]: u for u in USERS}


def user_label(u):
    return f'{u["name"]} — {u.get("title", "Rep")}' if u["role"] == "manager" else f'{u["name"]} — Rep'


# ---- call catalog (transcripts + merged evals) ------------------------------

@st.cache_data
def all_transcripts():
    """call_id → transcript dict, for every call in data/synthetic/."""
    out = {}
    for p in sorted((DATA / "synthetic").glob("*.json")):
        t = json.loads(p.read_text())
        out[t["call_id"]] = t
    return out


DISK_EVALS = {e["call_id"]: e for e in EVALS}
adapters.seed_from_evals(EVALS)   # populate the Activity feed for the pre-scored demo calls (once)


def session_evals():
    """Calls processed live this session — kept in memory so the committed dataset stays clean
    and the 'process it live' demo resets on every restart."""
    return st.session_state.setdefault("session_evals", {})


def eval_for(call_id):
    """Merged evaluation: a call processed this session overrides/adds to the committed set."""
    return session_evals().get(call_id) or DISK_EVALS.get(call_id)


def call_catalog(rep_id=None):
    """Every call (from transcripts), tagged scored/unscored, newest first."""
    rows = []
    for cid, t in all_transcripts().items():
        if rep_id and t["rep_id"] != rep_id:
            continue
        ev = eval_for(cid)
        rows.append({
            "call_id": cid, "rep_id": t["rep_id"], "rep_name": t.get("rep_name", ""),
            "product": t["product"], "account": t.get("account", "—"),
            "call_type": t["call_type"], "date": t.get("date", ""),
            "overall": ev["overall"] if ev else None,
        })
    return sorted(rows, key=lambda r: r["date"], reverse=True)


# ---- shared scorecard + routing ---------------------------------------------

def overall_summary(e):
    """The call's overall summary — the LLM's if present, else a deterministic fallback so the
    detail page always has one (the assignment's 'generate if not available')."""
    if e.get("summary"):
        return e["summary"]
    dims = e["dimensions"]
    strong = max(dims, key=lambda d: d["score"])
    weak = min(dims, key=lambda d: d["score"])
    flag = ""
    if e.get("flags"):
        flag = " Flags raised: " + ", ".join(
            sorted({f["type"].replace('_', ' ') for f in e["flags"]})) + "."
    return (f"Overall {e['overall']}/100. Strongest: {strong['label']} ({strong['score']:.1f}/5); "
            f"weakest: {weak['label']} ({weak['score']:.1f}/5).{flag}")


CARD = "background:#171c24;border:1px solid #2a313c;border-radius:10px;padding:14px 16px"
CARD_LABEL = "font-size:0.7rem;font-weight:700;letter-spacing:.05em;color:#8a97a3"


def render_scorecard(e):
    """Render one evaluation record (header + visual scorecard + Coach's next steps). Returns the
    top-2 focus dims. Shared by the call-detail page."""
    st.markdown(f"### {html.escape(e.get('rep_name', ''))} — {e['call_type'].replace('_', ' ')} · "
                f"{html.escape(str(e['product']))} · {html.escape(str(e.get('account', '')))}")
    st.caption(e.get("date", ""))

    lab, c = band_label(e["overall"])
    top = st.columns([1, 3.6], gap="medium")
    top[0].markdown(
        f'<div style="{CARD}">'
        f'<div style="{CARD_LABEL}">OVERALL SCORE</div>'
        f'<div style="font-size:2.4rem;font-weight:800;color:{c};line-height:1.1;margin-top:2px">'
        f'{e["overall"]}<span style="font-size:1rem;color:#8a97a3;font-weight:600"> /100</span></div>'
        f'<div style="margin-top:7px"><span style="background:{c}22;color:{c};font-weight:700;'
        f'font-size:0.74rem;padding:2px 11px;border-radius:999px">{lab}</span></div></div>',
        unsafe_allow_html=True)
    flags_html = ""
    if e["flags"]:
        fl = " · ".join(sorted({f["type"].replace('_', ' ') for f in e["flags"]}))
        flags_html = (f'<div style="margin-top:9px;color:#e5645a;font-size:0.8rem;font-weight:600">'
                      f'🚩 {html.escape(fl)}</div>')
    top[1].markdown(
        f'<div style="{CARD}">'
        f'<div style="{CARD_LABEL}">SUMMARY</div>'
        f'<div style="margin-top:5px;font-size:0.92rem;line-height:1.45">'
        f'{html.escape(overall_summary(e))}</div>{flags_html}</div>',
        unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("##### Scorecard")
        left, right = st.columns(2)
        for i, d in enumerate(e["dimensions"]):
            with (left if i % 2 == 0 else right):
                dim_row(d)

    # Coach's next steps — the two weakest dims (with tips) as the actions, recommended
    # micro-content as the resources to close the gap (merged from the old two sections).
    focus = sorted(e["dimensions"], key=lambda d: d["score"])[:2]
    with st.container(border=True):
        st.markdown("##### Coach's next steps")
        for i, d in enumerate(focus, 1):
            st.markdown(f"{i}. **{d['label']}** ({d['score']:.1f}/5) — {d.get('tip', '')}")
        if e.get("recommendations"):
            st.markdown("**Resources to close the gap**")
            for r in e["recommendations"]:
                st.markdown(f"- **{r['title']}** — {r['why']}")
    return focus


def route_slack(e, focus):
    adapters.MockNotifier().send_nudge(
        ctx_of(e), f"{e['call_type'].replace('_', ' ')} call scored {e['overall']}/100 — "
                   f"top fix: {focus[0]['label']}.")


def route_hubspot(e, focus):
    crm = adapters.MockCRM()
    crm.attach_scorecard(ctx_of(e), f"Scorecard {e['overall']}/100 attached to the call record")
    crm.create_task(ctx_of(e), f"Coaching: {focus[0]['label']} — due in 3 days")


# ---- call list → detail -----------------------------------------------------

def open_call(call_id):
    st.session_state["open_call"] = call_id


def render_call_list(calls, show_rep, key):
    """Filterable call table: one filter per column (labels double as headers), aligned above the
    data, with a per-row Details/Process button. Overall → — for unscored calls."""
    if not calls:
        st.info("No calls yet.")
        return
    widths = ([1.3] if show_rep else []) + [1.1, 1.8, 1.2, 1.2, 1.2, 1.1]  # [Rep] Date Acct Prod Type Overall Btn
    opt = lambda f: ["All"] + sorted({f(r) for r in calls if f(r)})

    # filter row — each control sits above the column it filters
    fc = st.columns(widths)
    i = 0
    rep_f = "All"
    if show_rep:
        rep_f = fc[i].selectbox("Rep", opt(lambda r: r["rep_name"]), key=f"{key}_rep"); i += 1
    date_q = fc[i].text_input("Date", key=f"{key}_date", placeholder="search"); i += 1
    acc_f = fc[i].selectbox("Account", opt(lambda r: r["account"]), key=f"{key}_acc"); i += 1
    prod_f = fc[i].selectbox("Product", opt(lambda r: r["product"]), key=f"{key}_prod"); i += 1
    type_f = fc[i].selectbox("Type", opt(lambda r: r["call_type"]), key=f"{key}_type",
                             format_func=lambda x: x if x == "All" else x.replace("_", " ")); i += 1
    ov_f = fc[i].selectbox("Overall", ["All", "scored", "unscored"], key=f"{key}_ov"); i += 1

    def keep(r):
        status = "scored" if r["overall"] is not None else "unscored"
        if show_rep and rep_f != "All" and r["rep_name"] != rep_f:
            return False
        if acc_f != "All" and r["account"] != acc_f:
            return False
        if prod_f != "All" and r["product"] != prod_f:
            return False
        if type_f != "All" and r["call_type"] != type_f:
            return False
        if ov_f != "All" and status != ov_f:
            return False
        if date_q and date_q.lower() not in str(r["date"]).lower():
            return False
        return True
    rows = [r for r in calls if keep(r)]
    if not rows:
        st.caption("No calls match these filters.")
        return
    for r in rows:
        scored = r["overall"] is not None
        cells = st.columns(widths)
        j = 0
        if show_rep:
            cells[j].write(r["rep_name"]); j += 1
        cells[j].write(r["date"]); j += 1
        cells[j].write(r["account"]); j += 1
        cells[j].write(r["product"]); j += 1
        cells[j].write(r["call_type"].replace("_", " ")); j += 1
        cells[j].markdown(f"**{r['overall']}**" if scored else "—"); j += 1
        label = "Details" if scored else "⚡ Process"
        if cells[j].button(label, key=f"{key}_{r['call_id']}", type="secondary" if scored else "primary"):
            open_call(r["call_id"])
            st.rerun()


def render_call_activity(call_id):
    st.markdown("##### Integration activity")
    st.caption("What the loop routed for this call — Slack nudge, HubSpot scorecard & coaching task.")
    log = [a for a in adapters.load_log() if a.get("call_id") == call_id]
    if not log:
        st.info("No integration activity yet for this call.")
        return
    rows = [{"Time": a.get("ts", "").replace("T", " "),
             "Endpoint": ENDPOINT_LABEL.get(a.get("endpoint"), str(a.get("endpoint")).title()),
             "Type": a.get("action"), "Content": a.get("content")} for a in reversed(log)]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
                 column_config={"Content": st.column_config.TextColumn(width="large")})


def render_transcript(t, expanded=False):
    """Full call transcript, speaker-labeled (Rep in accent, Prospect muted)."""
    if not t or not t.get("turns"):
        return
    with st.expander(f"Full transcript · {len(t['turns'])} turns", expanded=expanded):
        for turn in t["turns"]:
            color = "#4c9be8" if turn["speaker"] == "Rep" else "#9aa7b3"
            st.markdown(
                f'<div style="margin:5px 0;font-size:0.9rem;line-height:1.45">'
                f'<b style="color:{color}">{turn["speaker"]}:</b> {html.escape(turn["text"])}</div>',
                unsafe_allow_html=True)


def render_unscored(t):
    """Detail for a not-yet-processed call: full transcript + the Process button."""
    st.markdown(f"### {html.escape(t.get('rep_name', ''))} — {t['call_type'].replace('_', ' ')} · "
                f"{html.escape(str(t['product']))} · {html.escape(str(t.get('account', '')))}")
    st.info("This call hasn't been processed yet. In production the post-call trigger runs this "
            "automatically — here you kick it off.")
    render_transcript(t, expanded=True)
    if st.button("⚡ Process this call", type="primary", key=f"proc_{t['call_id']}"):
        with st.spinner("Processing — deterministic metrics + Claude scoring, then routing…"):
            try:
                rec, _ = score_live(t)
            except (Exception, SystemExit) as ex:
                st.error(f"Processing failed: {ex}")
                return
        session_evals()[t["call_id"]] = rec
        focus = sorted(rec["dimensions"], key=lambda d: d["score"])[:2]
        route_slack(rec, focus)          # close the loop automatically (auto-routed on process)
        route_hubspot(rec, focus)
        st.rerun()


def render_call_detail(call_id):
    if st.button("← Back to calls"):
        st.session_state.pop("open_call", None)
        st.rerun()
    t = all_transcripts().get(call_id)
    ev = eval_for(call_id)
    if t is None and ev is None:
        st.warning("Call not found.")
        return
    if ev is None:
        render_unscored(t)
        return
    render_scorecard(ev)
    st.divider()
    render_transcript(t)
    st.divider()
    render_call_activity(call_id)


def view_my_calls(rep_id):
    st.caption("Your calls. **Details** opens the scorecard; an unscored call has a **Process** "
               "button that runs the whole pipeline.")
    render_call_list(call_catalog(rep_id), show_rep=False, key="calls_mine")


def view_all_calls():
    st.caption("Every rep's calls — **Details** opens the scorecard (an unscored call runs Process).")
    render_call_list(call_catalog(), show_rep=True, key="calls_all")


def _endpoint_label(a):
    return ENDPOINT_LABEL.get(a.get("endpoint"), str(a.get("endpoint")).title())


def _filter_activity(log, show_rep, key):
    """A compact filter bar (one control per meaningful column) → the filtered activity log."""
    opts = lambda f: ["All"] + sorted({v for v in (f(a) for a in log) if v})
    ncols = 5 + (1 if show_rep else 0)
    fc = st.columns([2] + [1] * (ncols - 1))
    i = 0
    q = fc[i].text_input("Search", key=f"{key}_q", placeholder="call, content, time…"); i += 1
    rep_f = "All"
    if show_rep:
        rep_f = fc[i].selectbox("Rep", opts(lambda a: a.get("rep_name")), key=f"{key}_rep"); i += 1
    ep_f = fc[i].selectbox("Endpoint", opts(_endpoint_label), key=f"{key}_ep"); i += 1
    ty_f = fc[i].selectbox("Type", opts(lambda a: a.get("action")), key=f"{key}_ty"); i += 1
    pr_f = fc[i].selectbox("Product", opts(lambda a: a.get("product")), key=f"{key}_pr"); i += 1
    ac_f = fc[i].selectbox("Account", opts(lambda a: a.get("account")), key=f"{key}_ac"); i += 1

    def keep(a):
        if show_rep and rep_f != "All" and a.get("rep_name") != rep_f:
            return False
        if ep_f != "All" and _endpoint_label(a) != ep_f:
            return False
        if ty_f != "All" and a.get("action") != ty_f:
            return False
        if pr_f != "All" and a.get("product") != pr_f:
            return False
        if ac_f != "All" and a.get("account") != ac_f:
            return False
        if q:
            hay = " ".join(str(x) for x in (a.get("ts"), _endpoint_label(a), a.get("action"),
                                            a.get("rep_name"), a.get("product"), a.get("account"),
                                            a.get("call_id"), a.get("content"))).lower()
            if q.lower() not in hay:
                return False
        return True
    return [a for a in log if keep(a)]


def view_activity(rep_id=None):
    show_rep = rep_id is None
    st.subheader("Integration activity")
    st.caption(("Every action the loop routed across the team" if show_rep else
                "Every action the loop routed for your calls")
               + " — Slack nudges and HubSpot scorecards/tasks. Process a call to route the loop.")
    log = adapters.load_log()
    if rep_id:
        log = [a for a in log if a.get("rep_id") == rep_id]
    if not log:
        st.info("No activity yet. Open an **unscored** call and press **Process** to route the loop.")
        return
    log = _filter_activity(log, show_rep, key="act_all" if show_rep else "act_rep")
    if not log:
        st.caption("No activity matches these filters.")
        return
    rows = []
    for a in reversed(log):
        row = {"Time": a.get("ts", "").replace("T", " "), "Endpoint": _endpoint_label(a),
               "Type": a.get("action"), "Product": a.get("product"), "Account": a.get("account"),
               "Call": a.get("call_id"), "Content": a.get("content")}
        if show_rep:
            row = {"Time": row["Time"], "Endpoint": row["Endpoint"], "Type": row["Type"],
                   "Rep": a.get("rep_name"), **{k: row[k] for k in ("Product", "Account", "Call", "Content")}}
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
                 column_config={"Content": st.column_config.TextColumn(width="large")})


# ---- Manager view -----------------------------------------------------------

def is_escalation(e):
    """Reserve escalation for genuinely bad calls — not a solid call with one weak dimension."""
    severe = sum(1 for d in e["dimensions"] if d["key"] in CORE_DIMS and d["score"] <= 1.5)
    return e["overall"] < 35 or len(e["flags"]) >= 3 or severe >= 2


def view_manager():
    st.subheader("Team rollup")
    rows = []
    for rid, r in REPS.items():
        me = rep_evals(rid)
        latest = me[0]["overall"] if me else None
        rows.append({"Rep": r["name"], "Archetype": r["archetype"].split(" — ")[0],
                     "Last call": latest, "Trend": rep_trend(rid),
                     "Scored calls": len(me), "id": rid})
    df = pd.DataFrame(rows).sort_values("Last call")
    st.dataframe(df.drop(columns="id"), hide_index=True, use_container_width=True)

    st.subheader("🚨 Escalation queue")
    esc = [e for e in EVALS if is_escalation(e)]
    if not esc:
        st.success("Nothing critical this week.")
    for e in sorted(esc, key=lambda e: e["overall"]):
        reasons = []
        if e["overall"] < 35:
            reasons.append(f"score {e['overall']}")
        if e["flags"]:
            reasons.append(", ".join(sorted({f["type"].replace('_', ' ') for f in e["flags"]})))
        with st.expander(f"⚠️ {REPS[e['rep_id']]['name']} · {e['call_type']} · {e['overall']}/100 "
                         f"— {'; '.join(reasons)}"):
            st.caption(overall_summary(e))
            weak = sorted(e["dimensions"], key=lambda d: d["score"])[:3]
            st.markdown("Weakest: " + " · ".join(f"{d['label']} {d['score']:.1f}" for d in weak))
            if st.button("Open call detail →", key=f"open_{e['call_id']}"):
                open_call(e["call_id"])
                st.rerun()

    st.subheader("📋 Coaching queue — this week")
    need = sorted([(rid, rep_evals(rid)) for rid in REPS if rep_evals(rid)],
                  key=lambda t: t[1][0]["overall"])
    for rid, me in need:
        latest = me[0]
        if latest["overall"] >= 70:
            continue
        weakest = min(latest["dimensions"], key=lambda d: d["score"])
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"**{REPS[rid]['name']}** ({latest['overall']}/100) — focus "
                    f"**{weakest['label']}** ({weakest['score']:.1f}/5)")
        if c2.button("Open call", key=f"coach_{latest['call_id']}"):
            open_call(latest["call_id"])
            st.rerun()


# ---- Trend view -------------------------------------------------------------

def view_trend(rep_id=None):
    st.subheader("Score trajectories")
    df = hist_df()
    df["Rep"] = df["rep_id"].map(lambda r: REPS[r]["name"])
    if rep_id:
        st.caption(f"Your weekly trend, {REPS[rep_id]['name']} — pick a metric to drill into a dimension.")
        df = df[df["rep_id"] == rep_id]
    else:
        st.caption("Seeded history — the archetype story. Pick a metric to drill into a dimension.")

    # one chart, metric-selectable: Overall (default) or any single rubric dimension over time.
    metrics = ["overall"] + DIM_ORDER
    mkey = st.selectbox("Metric", metrics,
                        format_func=lambda k: "Overall" if k == "overall" else DIM_LABEL[k])
    df["_val"] = df["overall"] if mkey == "overall" else df["dimensions"].map(lambda dd: dd.get(mkey))
    weekly = (df.assign(week=df["date"].dt.to_period("W").dt.start_time)
                .groupby(["week", "Rep"])["_val"].mean().reset_index())
    st.line_chart(weekly.pivot(index="week", columns="Rep", values="_val"), height=360)


# ---- Measurement view -------------------------------------------------------

def stat_card(col, label, value=None, delta=None, up=True, desc=None, proxy=False):
    """One clean metric tile. proxy=True → a 'Production' pill instead of a placeholder value."""
    if proxy:
        body = ('<div style="margin-top:8px"><span style="background:#232a34;color:#9aa7b3;'
                'font-size:0.68rem;letter-spacing:.05em;padding:3px 9px;border-radius:999px">'
                'PRODUCTION</span></div>')
    else:
        body = (f'<div style="font-size:1.9rem;font-weight:700;color:#eef2f6;margin-top:4px;'
                f'line-height:1.1">{html.escape(str(value))}</div>')
        if delta:
            body += (f'<div style="font-size:0.78rem;margin-top:3px;color:'
                     f'{"#4ccf8f" if up else "#e56a6a"}">{"▲" if up else "▼"} '
                     f'{html.escape(str(delta))}</div>')
    dsc = (f'<div style="font-size:0.74rem;color:#7f8b98;margin-top:8px">{html.escape(desc)}</div>'
           if desc else "")
    col.markdown(
        f'<div style="{CARD};height:100%;min-height:120px">'
        f'<div style="{CARD_LABEL};text-transform:uppercase">{html.escape(label)}</div>'
        f'{body}{dsc}</div>',
        unsafe_allow_html=True)


def view_measurement():
    st.subheader("Measurement — if you can't measure it, it didn't work")
    st.caption("Leading signals move in **weeks**, lagging outcomes in a **quarter**. Real values are "
               "computed from evaluations; **Production** tiles wire to Jiminny / HubSpot.")
    df = hist_df()
    weeks = df["date"].dt.to_period("W")
    last_week = weeks.max()
    active = df[weeks == last_week]["rep_id"].nunique()

    deltas = []                                   # behavior change: mean per-rep (last − first weeks)
    for rid in REPS:
        d = df[df["rep_id"] == rid].sort_values("date")
        if len(d) >= 4:
            deltas.append(d.tail(3)["overall"].mean() - d.head(3)["overall"].mean())
    behavior = round(sum(deltas) / len(deltas), 1) if deltas else 0
    team_first = df[weeks == weeks.min()]["overall"].mean()
    team_last = df[weeks == last_week]["overall"].mean()

    st.markdown("###### Leading · internal — moves in weeks · three lenses")
    st.caption("**Adoption** — are the recommendations acted on?")
    c = st.columns(3)
    stat_card(c[0], "Calls scored", value=len(EVALS) + len(HISTORY),
              desc="Coverage — evaluations produced across the team.")
    stat_card(c[1], "Rec-adoption", proxy=True,
              desc="Share of coaching recommendations acted on.")
    stat_card(c[2], "Tasks completed / followed up", proxy=True,
              desc="Coaching to-dos closed in HubSpot.")

    st.caption("**Usage** — are reps and managers coming back?")
    c = st.columns(3)
    stat_card(c[0], "Weekly-active reps", value=f"{active}/{len(REPS)}",
              desc="Reps who reviewed a scorecard this week.")
    stat_card(c[1], "Content engagement", proxy=True,
              desc="Training / coaching-content opened from a scorecard.")
    stat_card(c[2], "Return rate", proxy=True,
              desc="Do reps come back to their scorecard?")

    st.caption("**Behavior change** — do calls actually get better?")
    c = st.columns(3)
    stat_card(c[0], "Flagged-dimension movement", value=f"{behavior:+.1f} pts", up=behavior >= 0,
              desc="Mean per-rep score movement, first→last weeks.")
    stat_card(c[1], "Fixes recur on later calls", proxy=True,
              desc="Recommended fixes show up on subsequent calls.")
    stat_card(c[2], "Coverage %", proxy=True,
              desc="Share of calls evaluated, from the Jiminny feed.")

    st.markdown("###### Lagging · external — call quality · ramp · conversion")
    c = st.columns(3)
    stat_card(c[0], "Call quality", value=f"{team_last:.0f}",
              delta=f"{team_last - team_first:+.0f} vs wk1", up=team_last >= team_first,
              desc="Team average rubric score (0–100).")
    stat_card(c[1], "Ramp-time", proxy=True,
              desc="New-rep time-to-productivity — from HubSpot outcomes.")
    stat_card(c[2], "Conversion / win-rate", proxy=True,
              desc="By pipeline stage, from the CRM.")

    st.info("**Honest baseline:** none of these were measured before — Rep Coach **creates the "
            "baseline from call one.** Internal metrics are computed from real evaluations; the "
            "lagging metrics wire to HubSpot outcome data in production.")


# ---- live scoring engine (invoked by the Process button) --------------------

def score_live(t):
    """Run the REAL engine end-to-end on a transcript dict. Returns (rec, non_verbatim_count)."""
    scoring.load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set — add it to build/.env to score live.")
    import anthropic
    client = anthropic.Anthropic()
    model = os.environ.get("REPCOACH_MODEL", "claude-sonnet-5")
    m = scoring.deterministic_metrics(t["turns"], t["call_type"])
    llm = scoring.llm_pass(t, RUBRIC, client, model)
    rec = scoring.combine(t, RUBRIC, m, llm)
    return rec, scoring.verify_quotes(llm, t["turns"])


# ---- header + user picker + dispatch ----------------------------------------

_model = EVALS[0]["model"] if EVALS else "n/a"
hc = st.columns([3, 2])
hc[0].markdown(
    "<div style='font-size:1.5rem;font-weight:800;line-height:1.1'>🎯 Rep Coach</div>"
    "<div style='color:#8a97a3;font-size:0.84rem;margin-top:1px'>Post-call evaluation &amp; "
    "coaching loop</div>"
    f"<div style='color:#697585;font-size:0.72rem;margin-top:2px'>Prototype · synthetic data · "
    f"CRM/Slack mocked · Rubric v{RUBRIC['version']} · model {_model}</div>",
    unsafe_allow_html=True)

# The user picker drives the whole app: pick a manager → team view; pick a rep → that rep's view.
# Switching user returns to the main menu (clear any open call detail).
def _on_user_change():
    st.session_state.pop("open_call", None)   # keep _call_seeded so a ?call= URL won't re-open


_qu = st.query_params.get("user")
_default_user = next((i for i, u in enumerate(USERS) if u["id"] == _qu), 0)
user = hc[1].selectbox("User", USERS, index=_default_user, format_func=user_label, key="user",
                       on_change=_on_user_change)

st.markdown("<hr style='margin:10px 0 4px;border:none;border-top:1px solid #2a313c'>",
            unsafe_allow_html=True)

# deep-link straight into a call detail: ?call=<call_id> (seeded once; Back still works)
_qc = st.query_params.get("call")
if _qc and not st.session_state.get("_call_seeded"):
    st.session_state["open_call"] = _qc
    st.session_state["_call_seeded"] = True

# A call detail takes over the whole surface (Back returns to the tabs).
if st.session_state.get("open_call"):
    render_call_detail(st.session_state["open_call"])
elif user["role"] == "manager":
    t_calls, t_team, t_trends, t_measure, t_act = st.tabs(
        ["Calls", "Team", "Trends", "Measurement", "Activity"])
    with t_calls:
        view_all_calls()
    with t_team:
        view_manager()
    with t_trends:
        view_trend()
    with t_measure:
        view_measurement()
    with t_act:
        view_activity()
else:
    t_calls, t_trends, t_act = st.tabs(["My Calls", "Trends", "Activity"])
    with t_calls:
        view_my_calls(user["id"])
    with t_trends:
        view_trend(user["id"])
    with t_act:
        view_activity(user["id"])
