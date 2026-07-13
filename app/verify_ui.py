#!/usr/bin/env python3
"""End-to-end UI verification for Rep Coach — the "drive the running app" gate.

Each scenario boots its OWN fresh Streamlit server on a free port and loads one page, so a
websocket hiccup in one view can't cascade into the next. Deep-links carry the app's real state:
`?user=<id>` drives the picker (manager → team tabs, rep → own tabs) and `?call=<id>` lands
straight on a call detail. Within a scenario we click real tabs and the per-row Details/Process
buttons and assert the resulting surface rendered — so "it works" means the pixels are right,
not just that a function returned. Every surface is screenshotted to build/_screens/.

Covers AC2/AC4/AC5/AC9/AC10. The "Process unscored" scenario exercises the LIVE engine, so it
needs ANTHROPIC_API_KEY in build/.env (same requirement as verify_ac8.py); the other three run
against the committed, cached evaluations and need no key.

Run:  .venv/bin/python verify_ui.py      → prints PASS/FAIL per scenario, exits non-zero on any fail
"""
import re
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BUILD = Path(__file__).resolve().parent
STREAMLIT = BUILD / ".venv/bin/streamlit"
OUT = BUILD / "_screens"
OUT.mkdir(exist_ok=True)
results = []


def free_port():
    s = socket.socket(); s.bind(("", 0)); p = s.getsockname()[1]; s.close(); return p


def start_server(port):
    proc = subprocess.Popen(
        [str(STREAMLIT), "run", "app.py", "--server.headless", "true",
         "--server.port", str(port), "--server.fileWatcherType", "none"],
        cwd=str(BUILD), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://localhost:{port}/", timeout=1); return proc
        except Exception:
            time.sleep(0.5)
    return proc


def stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()


def load(browser, port, **params):
    q = urllib.parse.urlencode(params)
    pg = browser.new_page(viewport={"width": 1440, "height": 1024})
    pg.goto(f"http://localhost:{port}/?{q}", wait_until="domcontentloaded", timeout=45000)
    pg.get_by_text("Rep Coach").first.wait_for(timeout=45000)
    pg.wait_for_timeout(1200)
    return pg


def scenario(name, fn):
    port = free_port(); proc = start_server(port)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            note = fn(browser, port)
            browser.close()
        results.append((name, "PASS", note))
    except Exception as e:
        results.append((name, "FAIL", str(e).splitlines()[0][:110]))
    finally:
        stop(proc)


def s_process(browser, port):                                                  # AC9 (live engine)
    pg = load(browser, port, user="R1", call="R1_disc_new")
    pg.get_by_text(re.compile("hasn't been processed")).wait_for(timeout=15000)
    pg.get_by_role("button", name=re.compile("Process this call")).click()
    pg.get_by_text(re.compile("Coach's next steps")).wait_for(timeout=180000)  # live LLM + retries
    pg.get_by_text(re.compile("Integration activity")).wait_for(timeout=10000)
    pg.get_by_text(re.compile("HubSpot")).first.wait_for(timeout=10000)
    pg.screenshot(path=str(OUT / "0_process.png"), full_page=True)
    return "unscored → Process → scorecard + auto-routed activity"


def s_scored_detail(browser, port):                                            # AC2
    pg = load(browser, port, user="R1", call="R1_disc_001")
    pg.get_by_text(re.compile("Coach's next steps")).wait_for(timeout=15000)
    pg.get_by_text(re.compile("Integration activity")).wait_for(timeout=10000)
    pg.screenshot(path=str(OUT / "1_scored_detail.png"), full_page=True)
    return "scored detail renders scorecard + coach steps + activity"


def s_rep_tabs(browser, port):                                                 # AC5/AC10
    pg = load(browser, port, user="R1")
    pg.get_by_text(re.compile("Your calls")).wait_for(timeout=15000)           # My Calls tab
    assert pg.get_by_role("button", name="Details").count() >= 1              # per-row Details button
    pg.screenshot(path=str(OUT / "2_rep_mycalls.png"), full_page=True)

    pg.get_by_role("tab", name="Trends").click()                               # tabs
    pg.get_by_text(re.compile("Score trajectories")).wait_for(timeout=10000)
    pg.get_by_label("Metric").click()                                          # Overall option
    pg.get_by_role("option", name="Overall", exact=True).wait_for(timeout=8000)
    pg.keyboard.press("Escape")
    pg.screenshot(path=str(OUT / "3_rep_trends.png"), full_page=True)

    pg.get_by_role("tab", name="My Calls").click()
    pg.get_by_role("button", name="Details").first.click()                     # opens detail
    pg.get_by_text(re.compile("Coach's next steps")).wait_for(timeout=15000)
    return "rep own calls · tabs · Trends Overall option · Details opens detail"


def s_manager_tabs(browser, port):                                             # AC4/AC10
    pg = load(browser, port, user="M1")
    pg.get_by_text(re.compile("Every rep's calls")).wait_for(timeout=15000)    # Calls tab (all reps)
    pg.screenshot(path=str(OUT / "4_manager_calls.png"), full_page=True)
    pg.get_by_role("tab", name="Team").click()
    pg.get_by_text(re.compile("Team rollup")).wait_for(timeout=10000)          # rollup + escalation
    pg.screenshot(path=str(OUT / "5_manager_team.png"), full_page=True)
    pg.get_by_role("tab", name="Trends").click()
    pg.get_by_text(re.compile("Score trajectories")).wait_for(timeout=10000)
    pg.get_by_role("tab", name="Measurement").click()
    pg.get_by_text(re.compile("if you can't measure it")).wait_for(timeout=10000)
    pg.screenshot(path=str(OUT / "6_manager_measurement.png"), full_page=True)
    return "manager tabs: Calls · Team · Trends · Measurement"


(BUILD / "data" / "routing_log.json").unlink(missing_ok=True)
scenario("Process unscored", s_process)
scenario("Scored detail", s_scored_detail)
scenario("Rep tabs+Details", s_rep_tabs)
scenario("Manager tabs", s_manager_tabs)

print("\n=== Rep Coach — user picker · tabs · Details · Process ===")
ok = True
for name, status, note in results:
    print(f"  {name:<18} {status:<6} {note}")
    ok = ok and status == "PASS"
print("\nRESULT:", "ALL PASS" if ok else "FAILURES")
print("screenshots:", OUT)
sys.exit(0 if ok else 1)
