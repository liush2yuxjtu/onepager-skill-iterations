import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path("/Users/liushiyuwin/.pi/skills/onepager-workspace/iteration-1")


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.details_depth = 0
        self.links = []
        self.videos = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "details":
            self.details_depth += 1
        elif tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        elif tag == "video":
            self.videos.append(
                (attrs.get("src", ""), "controls" in attrs, self.details_depth)
            )
            if attrs.get("src"):
                self.links.append(attrs["src"])
        elif tag == "source" and attrs.get("src"):
            self.links.append(attrs["src"])
            if self.videos and not self.videos[-1][0]:
                _, controls, depth = self.videos[-1]
                self.videos[-1] = (attrs["src"], controls, depth)

    def handle_endtag(self, tag):
        if tag == "details":
            self.details_depth = max(0, self.details_depth - 1)


def result(assertion, passed, evidence):
    return {"text": assertion, "passed": bool(passed), "evidence": evidence}


def load_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def grade(run):
    meta = load_json(run.parent / "eval_metadata.json")
    html_path = run / "outputs/main.html"
    html = html_path.read_text(errors="replace") if html_path.exists() else ""
    page = Page()
    page.feed(html)
    links = set(page.links)
    results = []
    for assertion in meta["assertions"]:
        a = assertion.lower()
        if "report.html, qa.json, run.webm, and trace.zip" in assertion:
            wanted = {"report.html", "qa.json", "run.webm", "trace.zip"}
            ok = wanted <= links
            ev = f"links={sorted(links)}"
        elif "both run.webm and failure.webm and report.html" in assertion:
            wanted = {"run.webm", "failure.webm", "report.html"}
            ok = wanted <= links and ("<svg" in html or "data:image/svg+xml" in html)
            ev = f"links={sorted(links)}; inline_svg={'<svg' in html or 'data:image/svg+xml' in html}"
        elif a.startswith("the primary video run.webm is visible"):
            matches = [v for v in page.videos if v[0] == "run.webm"]
            ok = any(controls and depth == 0 for _, controls, depth in matches)
            ev = f"video_nodes={page.videos}"
        elif "does not link or copy failure.webm" in a:
            copied = (run / "outputs/failure.webm").exists()
            ok = "failure.webm" not in links and not copied
            ev = f"linked={'failure.webm' in links}; copied={copied}"
        elif "directly links qa.json" in a:
            ok = "qa.json" in links
            ev = f"links={sorted(links)}"
        elif "does not invent" in a or "does not invent any artifact" in a:
            allowed = {
                "report.html",
                "qa.json",
                "run.webm",
                "failure.webm",
                "trace.zip",
                "#",
                "",
            }
            artifact_links = {
                x for x in links if not x.startswith(("javascript:", "mailto:"))
            }
            ok = artifact_links <= allowed
            ev = f"artifact_links={sorted(artifact_links)}"
        elif "footer" in a and "/tmp/pitch-video-project" in assertion:
            ok = "/tmp/pitch-video-project" in html and "eval-session-5" in html
            ev = f"project={'/tmp/pitch-video-project' in html}; session={'eval-session-5' in html}"
        elif "footer" in a and "/tmp/scoped-handoff" in assertion:
            ok = "/tmp/scoped-handoff" in html and "eval-session-7" in html
            ev = f"project={'/tmp/scoped-handoff' in html}; session={'eval-session-7' in html}"
        elif "source project absolute path and a pi session id" in a:
            expected = {
                5: ("/tmp/pitch-video-project", "eval-session-5"),
                6: ("/tmp/debug-session", "eval-session-6"),
            }[meta["eval_id"]]
            ok = all(value in html for value in expected)
            ev = f"project={expected[0] in html}; session={expected[1] in html}"
        else:
            ok = False
            ev = "No deterministic grader matched this assertion."
        results.append(result(assertion, ok, ev))
    passed = sum(x["passed"] for x in results)
    timing_path = run / "timing.json"
    metrics_path = run / "outputs/metrics.json"
    output = {
        "expectations": results,
        "summary": {
            "passed": passed,
            "failed": len(results) - passed,
            "total": len(results),
            "pass_rate": passed / len(results) if results else 0,
        },
        "execution_metrics": load_json(metrics_path),
        "timing": load_json(timing_path),
        "claims": [],
        "user_notes_summary": {
            "uncertainties": [],
            "needs_review": [],
            "workarounds": [],
        },
        "eval_feedback": {
            "suggestions": [],
            "overall": "Assertions directly inspect link scope and media placement in main.html.",
        },
    }
    (run / "grading.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    )
    return meta["eval_name"], run.name, output["summary"]


for eval_dir in ROOT.iterdir():
    if not eval_dir.is_dir():
        continue
    for config in ("with_skill", "old_skill"):
        run = eval_dir / config
        if run.exists():
            print(grade(run))
