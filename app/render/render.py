#!/usr/bin/env python3
"""Shared PDF renderer for the Sensi enablement deliverables.

Two modes, one house style:
  report  -> portrait document (report.css): synthesizes a phase's markdown deliverables into
             a single <phase>_detail.pdf (cover + TOC + tables + diagrams).
  slides  -> landscape 16:9 (slides.css): renders a summary.md (slides delimited by lines that
             are exactly '---') into a <phase>_summary.pdf, or the capstone presentation.md.

Pipeline: Markdown (Python-Markdown) -> HTML -> Chromium (Playwright) -> PDF.
Mermaid ```mermaid fenced blocks render client-side via the vendored mermaid.min.js; the print
waits for mermaid to finish (window.__renderDone) before capturing.

RENDER-FIDELITY SELF-CHECK (the content gate validates the markdown; this validates that the
PDF didn't silently lose any of it). After printing, we assert against the rendered DOM:
  - every source table ROW is present (catches dropped rows),
  - every source HEADING is present (catches dropped sections),
  - every ```mermaid block rendered to an <svg> (catches blank/raw diagrams),
  - (slides) no slide overflows its fixed, overflow:hidden box (catches SILENT clipping),
  - (slides) DOM slide count matches the number of '---'-delimited slides.
Any failure exits non-zero and NO "good" PDF is trusted. Run with the media_tools venv:

  automation/media_tools/.venv/bin/python build/render/render.py --mode report --phase phase1_diagnose
"""
import argparse
import datetime
import html
import re
import sys
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent          # .../Assignment/build/render
ASSIGN = HERE.parents[1]                          # .../Assignment
DELIV = ASSIGN / "deliverables"
CACHE = HERE / "_cache"
MERMAID_JS = HERE / "mermaid.min.js"

PHASES = {
    "phase1_diagnose": {
        "title": "Phase 1 — Diagnose Before You Build",
        "subtitle": "Seller Enablement Intelligence · GTM AI Enablement",
        "footer": "Phase 1 · Diagnose",
        "report_inputs": ["diagnosis.md", "decision_log.md", "make_vs_buy.md"],
        "detail_out": "phase1_detail.pdf",
        "summary_in": "summary.md",
        "summary_out": "phase1_summary.pdf",
    },
    "phase2_build": {
        "title": "Phase 2 — Build Something That Runs",
        "subtitle": "Rep Coach · post-call evaluation & coaching",
        "footer": "Phase 2 · Build",
        "report_inputs": ["prd.md", "design.md", "tool_note.md"],
        "detail_out": "phase2_detail.pdf",
        "summary_in": "summary.md",
        "summary_out": "phase2_summary.pdf",
    },
    "phase3_playbook": {
        "title": "Phase 3 — Make It a Playbook",
        "subtitle": "The enablement loop that compounds",
        "footer": "Phase 3 · Playbook",
        "report_inputs": ["scalability.md"],
        "detail_out": "phase3_detail.pdf",
        "summary_in": "summary.md",
        "summary_out": "phase3_summary.pdf",
    },
    "production_readiness": {
        "title": "Scalability & Production Readiness",
        "subtitle": "Orchestration, integrations, security, cost",
        "footer": "Production Readiness",
        "report_inputs": ["production_readiness.md"],
        "detail_out": "production_readiness_detail.pdf",
        "summary_in": "summary.md",
        "summary_out": "production_readiness_summary.pdf",
    },
    "presentation": {
        "title": "Seller Enablement Intelligence",
        "subtitle": "GTM AI Enablement — capstone",
        "footer": "Sensi · GTM AI Enablement",
        "report_inputs": [],
        "detail_out": "presentation_detail.pdf",
        "summary_in": "presentation.md",
        "summary_out": "presentation.pdf",
    },
}

MD_EXTS = ["tables", "fenced_code", "toc", "sane_lists", "attr_list"]


# ---- markdown -> html -------------------------------------------------------

def extract_mermaid(text):
    blocks = []

    def repl(m):
        blocks.append(m.group(1))
        return f"\n\nMERMAIDBLOCK{len(blocks) - 1}ENDMERMAID\n\n"

    text = re.sub(r"```mermaid\s*\n(.*?)\n```", repl, text, flags=re.DOTALL)
    return text, blocks


def reinsert_mermaid(html_str, blocks):
    for i, code in enumerate(blocks):
        token = f"MERMAIDBLOCK{i}ENDMERMAID"
        div = f'<div class="mermaid">{code}</div>'
        html_str = html_str.replace(f"<p>{token}</p>", div).replace(token, div)
    return html_str


def md_to_html(text):
    text, blocks = extract_mermaid(text)
    body = markdown.markdown(text, extensions=MD_EXTS)
    return reinsert_mermaid(body, blocks), len(blocks)


def apply_variant(text, variant):
    """Resolve `:::detail … :::` leave-behind blocks for a deck variant.

    master    → keep the detail content, drop only the `:::`/`:::detail` marker lines.
    presenter → drop the whole block (content included), so the slide is a sparse backdrop.

    Returned text is what actually renders AND what the fidelity check counts against, so a
    line hidden in presenter is genuinely absent from both — never mistaken for 'lost'.
    """
    if variant == "presenter":
        text = re.sub(r"(?ms)^:::detail[ \t]*\n.*?^:::[ \t]*$\n?", "", text)
    text = re.sub(r"(?m)^:::detail[ \t]*$\n?", "", text)
    text = re.sub(r"(?m)^:::[ \t]*$\n?", "", text)
    return text


def page_shell(css, body, has_mermaid):
    if has_mermaid:
        js = MERMAID_JS.read_text(encoding="utf-8")
        mermaid_script = (
            f"<script>{js}</script>"
            "<script>mermaid.initialize({startOnLoad:false,theme:'neutral',"
            "flowchart:{useMaxWidth:true,htmlLabels:true}});"
            "window.__renderDone=false;"
            "(async()=>{try{await mermaid.run();}catch(e){console.error(e);}"
            "window.__renderDone=true;})();</script>"
        )
    else:
        mermaid_script = "<script>window.__renderDone=true;</script>"
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{css}</style></head><body>{body}{mermaid_script}</body></html>"
    )


def build_report_html(cfg, phase_dir):
    docs = []
    for name in cfg["report_inputs"]:
        p = phase_dir / name
        if not p.exists():
            sys.exit(f"missing input: {p}")
        docs.append(p.read_text(encoding="utf-8"))
    joined = "\n\n<div class=\"pagebreak\"></div>\n\n".join(docs)
    combined_md = "[TOC]\n\n" + joined
    body_html, n_mermaid = md_to_html(combined_md)
    today = datetime.date.today().strftime("%B %-d, %Y")
    cover = (
        f'<div class="cover"><div class="kicker">{html.escape(cfg["subtitle"])}</div>'
        f'<h1>{html.escape(cfg["title"])}</h1>'
        f'<div class="meta">Janos Kristof &nbsp;·&nbsp; {today}</div>'
        f'<div class="conf">Prepared under NDA · call data anonymized</div></div>'
    )
    body_html = cover + '<div class="toc-page"><h2>Contents</h2>' + body_html + "</div>"
    css = (HERE / "report.css").read_text(encoding="utf-8")
    return page_shell(css, body_html, n_mermaid > 0), docs


def build_slides_html(cfg, phase_dir, variant="master"):
    src = phase_dir / cfg["summary_in"]
    if not src.exists():
        sys.exit(f"missing summary source: {src}")
    raw = apply_variant(src.read_text(encoding="utf-8"), variant)
    chunks = [c.strip() for c in re.split(r"(?m)^---[ \t]*$", raw) if c.strip()]
    footer = html.escape(cfg["footer"])
    total = len(chunks)
    slides_html, any_mermaid = [], False
    for i, chunk in enumerate(chunks):
        inner, n = md_to_html(chunk)
        any_mermaid = any_mermaid or n > 0
        cls = "slide title" if i == 0 else "slide"
        foot = f'<div class="foot">{footer} &nbsp;·&nbsp; {i + 1}/{total}</div>'
        slides_html.append(f'<section class="{cls}">{inner}{foot}</section>')
    css = (HERE / "slides.css").read_text(encoding="utf-8")
    return page_shell(css, "".join(slides_html), any_mermaid), [raw], total


# ---- render-fidelity self-check --------------------------------------------

def _norm(s):
    return " ".join(re.sub(r"[*_`~]", "", s).split())


def _strip_fences(t):
    return re.sub(r"```.*?```", "", t, flags=re.DOTALL)


def _source_table_rows(texts):
    n = 0
    for t in texts:
        for line in _strip_fences(t).splitlines():
            s = line.strip()
            if s.startswith("|") and not re.match(r"^\|[\s:\-|]+\|?$", s):
                n += 1
    return n


def _source_headings(texts):
    hs = []
    for t in texts:
        for line in _strip_fences(t).splitlines():
            m = re.match(r"^#{1,4}\s+(.+)", line)
            if m:
                hs.append(_norm(m.group(1)))
    return hs


def verify_render(page, mode, source_texts, expected_slides):
    """Return a list of (level, message). level 'FAIL' means content was lost."""
    issues = []
    body = _norm(page.inner_text("body"))

    merm = page.eval_on_selector_all(".mermaid", "els => els.map(e => !!e.querySelector('svg'))")
    if merm and not all(merm):
        issues.append(("FAIL", f"{merm.count(False)}/{len(merm)} mermaid diagram(s) did not render to <svg>"))

    src_rows = _source_table_rows(source_texts)
    dom_rows = len(page.query_selector_all("table tr"))
    if dom_rows != src_rows:
        issues.append(("FAIL", f"table rows: source={src_rows} rendered={dom_rows} (rows dropped or added)"))

    for h in _source_headings(source_texts):
        probe = h[:38]
        if probe and probe not in body:
            issues.append(("FAIL", f"heading missing from rendered output: {h!r}"))

    if mode == "slides":
        info = page.eval_on_selector_all(
            "section.slide",
            "els => els.map((e,i)=>({i, over: e.scrollHeight > Math.ceil(e.getBoundingClientRect().height)+2}))",
        )
        clipped = [d["i"] for d in info if d["over"]]
        if clipped:
            issues.append(("FAIL", f"slide(s) overflow their fixed box and would be CLIPPED: {clipped}"))
        if expected_slides is not None and len(info) != expected_slides:
            issues.append(("FAIL", f"slide count: expected {expected_slides}, DOM has {len(info)}"))

    return issues, {"tables": dom_rows, "mermaid": len(merm), "slides": expected_slides}


def render_pdf(html_str, out_path, mode, source_texts, expected_slides):
    CACHE.mkdir(exist_ok=True)
    html_file = CACHE / (out_path.stem + ".html")
    html_file.write_text(html_str, encoding="utf-8")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(html_file.as_uri())
        try:
            page.wait_for_function("window.__renderDone === true", timeout=30000)
        except Exception:
            print("  (warning: render-done wait timed out; printing anyway)")
        page.emulate_media(media="print")
        if mode == "report":
            page.pdf(path=str(out_path), prefer_css_page_size=True, print_background=True)
        else:
            page.pdf(path=str(out_path), width="13.333in", height="7.5in", print_background=True)
        issues, stats = verify_render(page, mode, source_texts, expected_slides)
        browser.close()
    return issues, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["report", "slides"])
    ap.add_argument("--phase", required=True, choices=list(PHASES))
    ap.add_argument("--variant", default="master", choices=["master", "presenter"],
                    help="slides only: 'master' keeps :::detail leave-behind blocks; "
                         "'presenter' drops them for a sparse talk-track cut")
    args = ap.parse_args()
    cfg = PHASES[args.phase]
    phase_dir = DELIV / args.phase

    if args.mode == "report":
        html_str, sources = build_report_html(cfg, phase_dir)
        out = phase_dir / cfg["detail_out"]
        expected_slides = None
    else:
        html_str, sources, expected_slides = build_slides_html(cfg, phase_dir, args.variant)
        out = phase_dir / cfg["summary_out"]
        if args.variant == "presenter":
            out = out.with_name(out.stem + "_presenter" + out.suffix)

    issues, stats = render_pdf(html_str, out, args.mode, sources, expected_slides)

    fails = [m for lvl, m in issues if lvl == "FAIL"]
    if fails:
        # Remove the untrustworthy PDF so a lossy artifact is never mistaken for good.
        if out.exists():
            out.unlink()
        print(f"  ✗ RENDER FIDELITY FAILED for {out.name} — PDF discarded:")
        for m in fails:
            print(f"      - {m}")
        sys.exit(2)

    detail = f"{stats['tables']} table-rows, {stats['mermaid']} mermaid"
    if expected_slides is not None:
        detail += f", {expected_slides} slides"
    print(f"  wrote {out.relative_to(ASSIGN)}  ✓ fidelity OK ({detail})")


if __name__ == "__main__":
    main()
