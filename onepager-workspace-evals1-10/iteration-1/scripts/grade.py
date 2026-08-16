#!/usr/bin/env python3
"""Auto-grade onepager eval HTML outputs into grading.json (schema: text/passed/evidence)."""
import json
import re
import sys
from pathlib import Path

WS = Path("/Users/liushiyuwin/.agents/skills/onepager-workspace/iteration-1")

ASSERTIONS = [
    ("verdict_first",
     "标题下 5 秒内出现一句话结论（verdict / TL;DR / 结论）",
     lambda h, meta: _verdict_first(h)),
    ("search_input",
     "存在搜索框（input class 含 search）",
     lambda h, meta: _re(r'<input[^>]+class="[^"]*search[^"]*"|<input[^>]+id="[^"]*search[^"]*"|placeholder="[^"]*(?:筛选|搜索|筛选进程)[^"]*"', h)),
    ("sortable_header",
     "表头可点击排序（data-k/data-sort/onclick + 排序 JS）",
     lambda h, meta: _re(r'<th[^>]+data-[a-z]+=', h) and ("sort" in h.lower() or "addEventListener('click'" in h)),
    ("checklist_checkbox",
     "存在可勾选行动清单（input[type=checkbox]，含 JS 动态渲染）",
     lambda h, meta: len(re.findall(r'<input[^>]+type=["\']checkbox["\']', h, re.I)) >= 1
                      and (bool(re.search(r'id=["\']checklist|class=["\'][^"\']*check', h, re.I))
                           or re.findall(r'type=["\']?checkbox', h, re.I))),
    ("copy_button",
     "存在复制按钮（navigator.clipboard 或 id=copybtn）",
     lambda h, meta: "navigator.clipboard" in h or "copybtn" in h or "copy-btn" in h),
    ("evidence_collapsed",
     "全量证据在 <details> 折叠区，默认收起",
     lambda h, meta: len(re.findall(r'<details', h, re.I)) > 0),
    ("no_cdn",
     "无 CDN / 外链资源（仅允许 data: 与本地回环）",
     lambda h, meta: _no_cdn(h)),
    ("provenance_footer",
     "页脚有来源标注（项目名 / 绝对路径 / 会话 ID）",
     lambda h, meta: bool(re.search(r'<footer', h, re.I)) and bool(re.search(r'/Users/|来源|来源项目|Session|会话|pi-session|Pi Session', h, re.I))),
]


def _re(pat, h):
    return bool(re.search(pat, h, re.I))


def _verdict_first(h):
    m = re.search(r'<body[\s\S]{0,4000}', h, re.I)
    window = m.group(0) if m else h[:4000]
    return bool(re.search(r'verdict|结论[:：]|验收结论|TL;DR|<b>结论|class="[^"]*vtag[^"]*"[^>]*>结论', window, re.I))


def _no_cdn(h):
    for m in re.finditer(r'(?:src|href)\s*=\s*["\']https?://([^"\']+)', h, re.I):
        host = m.group(1)
        if not (host.startswith("127.0.0.1") or host.startswith("localhost")):
            return False
    return True


def grade(html_path: Path) -> dict:
    html = html_path.read_text(encoding="utf-8")
    expectations = []
    passed = failed = 0
    for key, text, fn in ASSERTIONS:
        ok = bool(fn(html, {}))
        evidence = _evidence(key, ok, html)
        expectations.append({"text": text, "passed": ok, "evidence": evidence})
        passed += ok
        failed += (not ok)
    total = passed + failed
    return {
        "expectations": expectations,
        "summary": {
            "passed": passed,
            "failed": failed,
            "total": total,
            "pass_rate": round(passed / total, 4) if total else 0.0,
        },
    }


def _evidence(key, ok, html):
    snippets = {
        "verdict_first": r'class="[^"]*verdict|>结论[:：]|验收结论|TL;DR',
        "search_input": r'<input[^>]+(?:class|id)="[^"]*search[^"]*"',
        "sortable_header": r'<th[^>]+data-[a-z]+="[^"]+"',
        "checklist_checkbox": r'<input[^>]+type="checkbox"[^>]*>',
        "copy_button": r'copybtn|navigator\.clipboard',
        "evidence_collapsed": r'<details',
        "no_cdn": r'(?:src|href)="https?://[^"]+"',
        "provenance_footer": r'<footer[\s\S]{0,400}?/footer>',
    }
    pat = snippets.get(key)
    if not pat:
        return "ok" if ok else "missing"
    m = re.search(pat, html, re.I)
    if key == "no_cdn":
        ext = [u for u in re.findall(r'(?:src|href)="(https?://[^"]+)"', html, re.I)
               if not u.startswith(("http://127.0.0.1", "http://localhost"))]
        return "无外链" if not ext else f"发现外链: {ext[:3]}"
    if m:
        s = re.sub(r"\s+", " ", m.group(0)).strip()
        return s[:160]
    return "未找到匹配"


def main():
    for eval_dir in sorted(WS.glob("eval-*")):
        for config in ("with_skill", "without_skill"):
            run_dir = eval_dir / config
            outputs = run_dir / "outputs"
            htmls = sorted(outputs.glob("*.html"))
            if not htmls:
                print(f"WARN: no html in {outputs}")
                continue
            g = grade(htmls[0])
            run_dir.joinpath("grading.json").write_text(json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8")
            run1 = run_dir / "run-1"
            run1.mkdir(exist_ok=True)
            run1.joinpath("grading.json").write_text(json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{run_dir.relative_to(WS)}: pass_rate={g['summary']['pass_rate']} ({g['summary']['passed']}/{g['summary']['total']})  file={htmls[0].name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
