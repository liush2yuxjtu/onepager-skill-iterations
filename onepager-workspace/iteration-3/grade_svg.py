#!/usr/bin/env python3
"""Programmatic grader for onepager SVG evals 11 & 12.

Reads outputs/ under each eval-<id>/<config>/ dir, checks assertions, writes
grading.json with fields {text, passed, evidence}. Reusable across iterations.
"""
import json
import re
import sys
from pathlib import Path

WORKSPACE = Path(sys.argv[1] if len(sys.argv) > 1 else ".")

EXTERNAL_RE = re.compile(
    r'<script[^>]+src=["\'](?!data:)'
    r'|<link[^>]+href=["\'](?!data:)'
    r'|<img[^>]+src=["\'](?!data:)'
    r'|src=["\']https?:'
)


def load_html(run_dir: Path):
    outs = run_dir / "outputs"
    if not outs.exists():
        outs = run_dir / "run-1" / "outputs"
    if not outs.exists():
        return []
    return [p for p in outs.rglob("*") if p.suffix.lower() in (".html", ".htm")]


def svg_blocks(html: str):
    return re.findall(r"<svg[^>]*>(.*?)</svg>", html, flags=re.S | re.I)


def check_external(html: str, body: str):
    m = EXTERNAL_RE.search(html)
    return {
        "text": body,
        "passed": m is None,
        "evidence": "no external script/link/img/CDN refs" if m is None
                    else f"external ref found: {m.group(0)[:80]}",
    }


def check_svg_blocks_present(html: str, body: str, expect_branch: bool = False):
    blocks = svg_blocks(html)
    if not blocks:
        return {"text": body, "passed": False, "evidence": "no <svg> block in HTML"}
    # proxy for "branches shared entry into A and B and converges":
    # the SVG contains both path labels and an evals/published mention
    if expect_branch:
        joined = " ".join(blocks).lower()
        has_a = "path a" in joined or "路径a" in joined or ("路径 a" in joined) or "路径A" in joined
        has_b = "path b" in joined or "路径b" in joined or ("路径 b" in joined) or "路径B" in joined
        has_converge = ("evals" in joined) or ("快照" in joined)
        ok = has_a and has_b and has_converge
        return {
            "text": body, "passed": ok,
            "evidence": f"{len(blocks)} svg block(s); A={has_a} B={has_b} converge-evidence={has_converge}"
        }
    return {"text": body, "passed": True, "evidence": f"{len(blocks)} svg block(s) present"}


def check_badges(html: str, body: str):
    # path badges A / B / A+B in mock cards
    joined = html.lower()
    has_ab = ("a+b" in joined or "a/b" in joined or "a · b" in joined
              or "路径a" in joined or "路径b" in joined or "路径 a" in joined or "路径 b" in joined)
    badge_el = bool(re.search(r"[>]\s*A\s*<|[>]\s*B\s*<", html))
    return {
        "text": body, "passed": has_ab or badge_el,
        "evidence": "path badge labels (A/B/A+B) present" if (has_ab or badge_el)
                   else "no path badge labels found"
    }


def check_contrast_table(html: str, body: str):
    has_table = bool(re.search(r"<table", html, re.I))
    text = html.lower()
    has_form = "表单" in text or "form" in text
    has_exec = "执行" in text or "execut" in text
    has_pub = "发布" in text or "publish" in text
    ok = has_table and has_form and has_exec and has_pub
    return {
        "text": body, "passed": ok,
        "evidence": f"table={has_table} form={has_form} exec={has_exec} publish={has_pub}"
    }


def check_no_foreign_in_svg(html: str, body: str):
    blocks = svg_blocks(html)
    bad = []
    for b in blocks:
        for tag in ("<span", "<div", "<code", "<p ", "<td", "<table"):
            if re.search(re.escape(tag), b, re.I):
                bad.append(tag.strip("<>"))
    return {
        "text": body, "passed": not bad,
        "evidence": "no <span>/<div>/<code> inside any <svg>" if not bad
                   else f"foreign tags inside svg: {sorted(set(bad))}"
    }


def check_g_in_svg(html: str, body: str):
    blocks = svg_blocks(html)
    has_g = any("<g" in b for b in blocks)
    return {
        "text": body, "passed": has_g,
        "evidence": "svg uses <g> wrapper(s)" if has_g else "no <g> in svg"
    }


def check_text_plain(html: str, body: str):
    blocks = svg_blocks(html)
    bad = []
    # SVG text-content children that are legitimate: tspan/title/desc/textPath/a
    SVG_NATIVE = re.compile(r"<\s*/(?:tspan|title|desc|textPath|a)\s*>|<\s*(?:tspan|title|desc|textPath|a)[^>]*>")
    for b in blocks:
        for m in re.finditer(r"<text[^>]*>(.*?)</text>", b, flags=re.S):
            inner = m.group(1)
            stripped = SVG_NATIVE.sub("", inner)
            if re.search(r"<\s*[a-zA-Z]", stripped):
                bad.append(inner[:40])
    return {
        "text": body, "passed": not bad,
        "evidence": "all <text> nodes are plain text" if not bad
                   else f"nested elements inside <text>: {bad[:3]}"
    }


def check_checklist(html: str, body: str):
    has_check = bool(re.search(r'<input[^>]+type=["\']checkbox', html, re.I)) or "checkbox" in html.lower()
    has_copy = ("复制" in html) or ("copy" in html.lower())
    return {
        "text": body, "passed": has_check and has_copy,
        "evidence": f"checkbox={has_check} copy={has_copy}"
    }


def check_flow_svg(html: str, body: str):
    blocks = svg_blocks(html)
    if not blocks:
        return {"text": body, "passed": False, "evidence": "no svg"}
    joined = " ".join(blocks)
    has_arrows = bool(re.search(r"<marker|<line[^>]*marker|marker-end|<path[^>]*m\s", joined, re.I))
    has_nodes = joined.count("<rect") + joined.count("<g") >= 4
    ok = has_arrows and has_nodes
    return {
        "text": body, "passed": ok,
        "evidence": f"svg nodes(rect/g)={joined.count('<rect')+joined.count('<g')} arrows/markers={has_arrows}"
    }


def check_labeled_nodes(html: str, body: str):
    blocks = svg_blocks(html)
    if not blocks:
        return {"text": body, "passed": False, "evidence": "no svg"}
    text_nodes = sum(b.count("<text") for b in blocks)
    return {
        "text": body, "passed": text_nodes >= 4,
        "evidence": f"{text_nodes} <text> labels inside svg (>=4 = annotated nodes)"
    }


def check_edge_connect(html: str, body: str):
    blocks = svg_blocks(html)
    if not blocks:
        return {"text": body, "passed": False, "evidence": "no svg"}
    joined = " ".join(blocks)
    has_edges = bool(re.search(r"<line|<path|<polyline|<marker", joined, re.I))
    return {"text": body, "passed": has_edges, "evidence": f"edge elements present: {has_edges}"}


def check_verdict_first(html: str, body: str):
    blocks = svg_blocks(html)
    first_svg = blocks[0] if blocks else ""
    # strip html head/scripts and find text before first <svg>
    before = re.split(r"<svg", html, maxsplit=1)[0]
    plain = re.sub(r"<[^>]+>", " ", before)
    has_text = len(plain.strip()) >= 10
    return {
        "text": body, "passed": has_text,
        "evidence": "content precedes the diagram" if has_text else "nothing before first svg"
    }


def check_img_data_only(html: str, body: str):
    imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)', html, re.I)
    bad = [s[:40] for s in imgs if not s.startswith("data:")]
    return {
        "text": body, "passed": not bad,
        "evidence": f"{len(imgs)} img; non-data srcs: {bad}" if bad
                   else f"{len(imgs)} img, all data: URIs"
    }


def check_svg_substance(html: str, body: str):
    # proxy for "full SVG renders, not just outer box + title":
    # svg body should contain many shape/text nodes beyond one box + one title
    blocks = svg_blocks(html)
    if not blocks:
        return {"text": body, "passed": False, "evidence": "no svg"}
    worst = min(len(re.findall(r"<(rect|path|circle|g|text|line|polyline|polygon)", b))
                for b in blocks if b.strip())
    ok = worst >= 8
    return {
        "text": body, "passed": ok,
        "evidence": f"smallest svg has {worst} shape/text nodes (>=8 = substantial)"
    }


def grade_run(eval_dir: Path, config: str, assertions: list):
    run_dir = eval_dir / config
    # write grading into run-1/ for the aggregate script; create if missing
    grade_target = run_dir / "run-1"
    grade_target.mkdir(parents=True, exist_ok=True)
    files = load_html(run_dir)
    if not files:
        grading = {
            "expectations": [{"text": a, "passed": False,
                              "evidence": "no HTML output file produced"} for a in assertions],
            "summary": {"passed": 0, "failed": len(assertions),
                        "total": len(assertions), "pass_rate": 0.0},
        }
        (grade_target / "grading.json").write_text(json.dumps(grading, ensure_ascii=False, indent=2))
        print(f"[{eval_dir.name}/{config}] NO OUTPUT")
        return
    html = files[0].read_text(encoding="utf-8", errors="replace")
    results = []
    for a in assertions:
        t = a.lower()
        if "no external" in t or "self-contained" in t or "zero external" in t:
            results.append(check_external(html, t))
        elif "overview svg branches" in t:
            results.append(check_svg_blocks_present(html, t, expect_branch=True))
        elif "path badge" in t:
            results.append(check_badges(html, t))
        elif "contrast table" in t:
            results.append(check_contrast_table(html, t))
        elif "all svg is inline" in t:
            results.append(check_external(html, t))
        elif "no <span> or <code>" in t or "no <span>/<div>/<code>" in t:
            results.append(check_no_foreign_in_svg(html, t))
        elif "badge wrappers" in t or "<g>" in t:
            results.append(check_g_in_svg(html, t))
        elif "plain text only" in t:
            results.append(check_text_plain(html, t))
        elif "renders visibly" in t:
            results.append(check_svg_substance(html, t))
        elif "copy-to-markdown" in t or "copy to markdown" in t or "copy-to-md" in t:
            results.append(check_checklist(html, t))
        elif "swimlane" in t or "arrow-connected stage" in t or "flow or swimlane" in t:
            results.append(check_flow_svg(html, t))
        elif "arrow edges connect" in t:
            results.append(check_edge_connect(html, t))
        elif "labeled node" in t or "label and a short" in t:
            results.append(check_labeled_nodes(html, t))
        elif "verdict-first" in t or "verdict first" in t:
            results.append(check_verdict_first(html, t))
        elif "non-data:" in t or "non-data src" in t:
            results.append(check_img_data_only(html, t))
        elif "visible evidence" in t:
            results.append(check_img_data_only(html, t))
        else:
            results.append({"text": t, "passed": None, "evidence": "no rule matched"})
    passed = sum(1 for r in results if r["passed"] is True)
    grading = {
        "expectations": results,
        "summary": {"passed": passed, "failed": len(results) - passed,
                    "total": len(results), "pass_rate": round(passed / len(results), 4) if results else 0.0},
    }
    (grade_target / "grading.json").write_text(json.dumps(grading, ensure_ascii=False, indent=2))
    print(f"[{eval_dir.name}/{config}] pass {passed}/{len(results)} <- {files[0].name}")


ELEVEN = [
    "Output is a single self-contained HTML file with no external script/link/img resources",
    "An overview SVG branches a shared entry point into path A and path B and converges on published expert + evals snapshot",
    "Each screen mock card is labeled with a path badge (A, B, or A+B)",
    "A contrast table distinguishes the two paths on form stage (form vs chat), execution, and publish",
    "All SVG is inline, with zero external assets",
]
TWELVE = [
    "The HTML contains no <span> or <code> element inside any <svg> block",
    "Badge wrappers inside SVG use <g> elements",
    "SVG <text> nodes contain plain text only, no nested HTML elements",
    "The full SVG renders visibly (not just the outer box and title), verified via screenshot or pixel check",
    "The file remains self-contained with zero external resources",
]

for eval_dir in sorted(WORKSPACE.glob("eval-*")):
    if not eval_dir.is_dir():
        continue
    meta_p = eval_dir / "eval_metadata.json"
    if not meta_p.exists():
        continue
    meta = json.loads(meta_p.read_text())
    assertions = meta.get("assertions") or ELEVEN
    for config in ("old_skill", "new_skill"):
        cfg = eval_dir / config
        if (cfg / "outputs").exists() or (cfg / "run-1" / "outputs").exists():
            grade_run(eval_dir, config, assertions)
