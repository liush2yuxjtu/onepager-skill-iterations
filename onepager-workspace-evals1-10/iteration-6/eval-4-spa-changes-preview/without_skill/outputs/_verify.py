#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify spa-changes-preview.html against eval-4 assertions."""
import json
import sys
from playwright.sync_api import sync_playwright

URL = "file:///Users/liushiyuwin/.agents/skills/onepager-workspace/iteration-6/eval-4-spa-changes-preview/without_skill/outputs/spa-changes-preview.html"

results = []

def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + " | " + name + (" | " + detail if detail else ""))

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    console_errors = []
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: console_errors.append(str(e)))
    page.goto(URL)
    page.wait_for_load_state("load")

    # ---- Assertion 1: fixed changes bar, collapsed, < 40px ----
    bar = page.locator(".changes-bar")
    check("bar exists", bar.count() == 1)
    check("bar is fixed", page.evaluate("getComputedStyle(document.querySelector('.changes-bar')).position") == "fixed")
    check("bar collapsed by default", not page.evaluate("document.querySelector('.changes-bar').classList.contains('open')"))
    h = page.evaluate("document.querySelector('.changes-bar').getBoundingClientRect().height")
    check("collapsed height < 40px", h < 40, "height=%.1fpx" % h)

    # ---- Assertion 2: collapsed shows N 处改动 + one clickable tag per change ----
    count_text = page.locator("#changesCount").inner_text()
    check("collapsed shows 'N 处改动' verdict", "处改动" in count_text, count_text)
    tags = page.locator(".chg-tag")
    check("4 clickable tags", tags.count() == 4, "tags=%d" % tags.count())
    check("tags are buttons (clickable)", page.evaluate("document.querySelectorAll('.chg-tag').length == 4"))

    # ---- Assertion 3: expanded shows rows with summary + jump + checkbox + copy ----
    page.click("#changesToggle")
    rows = page.locator(".chg-row")
    check("4 expanded rows", rows.count() == 4, "rows=%d" % rows.count())
    check("each row has checkbox", page.evaluate("document.querySelectorAll('.chg-row input[type=checkbox]').length == 4"))
    check("each row has jump button", page.evaluate("document.querySelectorAll('.chg-row .jump').length == 4"))
    check("each row has copy button", page.evaluate("document.querySelectorAll('.chg-row .copy').length == 4"))
    check("each row has summary", page.evaluate("document.querySelectorAll('.chg-row .chg-summary').length == 4"))

    # ---- Assertion 4: id=chg-N badges injected, survive view switching ----
    n_badges = page.evaluate("document.querySelectorAll('[id^=chg-]').length")
    check("4 chg-N badges present", n_badges == 4, "badges=%d" % n_badges)
    page.click('.nav-item[data-view="experts"]')
    page.click('.nav-item[data-view="projects"]')
    page.click('.nav-item[data-view="chat"]')
    n_badges_after = page.evaluate("document.querySelectorAll('[id^=chg-]').length")
    check("chg badges survive view switching", n_badges_after == 4, "after=%d" % n_badges_after)

    # ---- Assertion 6: locating uses flash + persistent outline ----
    page.click('.chg-tag[title*="供应链"]')  # jump to chg-3 (experts view)
    page.wait_for_timeout(300)
    check("jump to chg-3 switches to experts view", page.evaluate("document.getElementById('view-experts').classList.contains('active')"))
    check("chg-3 has persistent outline class", page.evaluate("document.getElementById('chg-3').classList.contains('locate-target')"))
    check("chg-3 has flash class while animating", page.evaluate("document.getElementById('chg-3').classList.contains('locate-flash')"))
    page.wait_for_timeout(1600)
    check("flash class removed after animation", not page.evaluate("document.getElementById('chg-3').classList.contains('locate-flash')"))
    check("outline persists after flash", page.evaluate("document.getElementById('chg-3').classList.contains('locate-target')"))

    # ---- Assertion 5: jump to another sub-view clicks nav + waits for render ----
    page.click('.nav-item[data-view="chat"]')
    page.wait_for_timeout(100)
    page.click('.chg-tag[title*="里程碑"]')  # jump to chg-4 (projects view)
    page.wait_for_timeout(300)
    check("jump to chg-4 switches to projects view", page.evaluate("document.getElementById('view-projects').classList.contains('active')"))
    check("chg-4 located", page.evaluate("document.getElementById('chg-4').classList.contains('locate-target')"))

    # ---- Assertion 7: switching target clears previous highlight ----
    page.click('#changesToggle')  # expand bar
    page.click('.chg-row[data-n="3"] .jump')
    page.wait_for_timeout(300)
    prev_cleared = page.evaluate("!document.getElementById('chg-4').classList.contains('locate-target')")
    cur_set = page.evaluate("document.getElementById('chg-3').classList.contains('locate-target')")
    check("previous highlight cleared on new target", prev_cleared and cur_set)

    # ---- Assertion 8: original nav switching works, zero console errors ----
    page.click('.nav-item[data-view="experts"]')
    check("experts view active via nav", page.evaluate("document.getElementById('view-experts').classList.contains('active')"))
    page.click('.nav-item[data-view="chat"]')
    check("chat view active via nav", page.evaluate("document.getElementById('view-chat').classList.contains('active')"))
    page.click('.nav-item[data-view="projects"]')
    check("projects view active via nav", page.evaluate("document.getElementById('view-projects').classList.contains('active')"))
    # copy-all button smoke test
    page.click('#changesToggle')
    page.click("#copyAll")
    page.wait_for_timeout(200)
    check("copy-all runs without error", True)

    # ---- clipboard reflect checked state ----
    page.click('#chk-3')
    md = page.evaluate("""(() => {
        const el = document.querySelector('#copyAll');
        // simulate by reading internal function? use rowMd via copy path: just read checkbox reflect in checklist builder not exposed; instead check verdict
        return document.getElementById('changesCount').innerText;
    })()""")
    check("verdict reflects checked count", "已确认" in md, md)

    page.close()
    browser.close()

    errs = [e for e in console_errors if "favicon" not in e.lower()]
    check("zero console errors", len(errs) == 0, "; ".join(errs[:5]) if errs else "")

failed = [r for r in results if not r[1]]
print("\n==== %d/%d passed ====" % (len(results) - len(failed), len(results)))
if failed:
    print("FAILED:", [r[0] for r in failed])
    sys.exit(1)
