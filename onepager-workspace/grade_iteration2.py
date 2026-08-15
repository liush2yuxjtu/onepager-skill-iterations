import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path("/Users/liushiyuwin/.pi/skills/onepager-workspace/iteration-2")


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.details_depth = 0
        self.links = []
        self.videos = []
        self.artifact_body_depth = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id") == "artifactBody":
            self.artifact_body_depth = self.details_depth
        if tag == "details":
            self.details_depth += 1
        elif tag == "a" and attrs.get("href"):
            self.links.append((attrs["href"], self.details_depth))
        elif tag == "video":
            self.videos.append(
                (attrs.get("src", ""), "controls" in attrs, self.details_depth)
            )
        elif tag == "source" and attrs.get("src"):
            self.links.append((attrs["src"], self.details_depth))
            if self.videos and not self.videos[-1][0]:
                _, controls, depth = self.videos[-1]
                self.videos[-1] = (attrs["src"], controls, depth)

    def handle_endtag(self, tag):
        if tag == "details":
            self.details_depth = max(0, self.details_depth - 1)


def load_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def basename(url):
    return Path(urlparse(url).path).name


def grade(run):
    meta = load_json(run.parent.parent / "eval_metadata.json")
    html_path = run / "outputs/main.html"
    html = html_path.read_text(errors="replace") if html_path.exists() else ""
    page = Page()
    page.feed(html)
    links = {basename(url) for url, _ in page.links}
    visible_links = {basename(url) for url, depth in page.links if depth == 0}
    dynamic_links = {
        basename(url) for url in re.findall(r"href\s*:\s*['\"]([^'\"]+)['\"]", html)
    }
    links |= dynamic_links
    if page.artifact_body_depth == 0:
        visible_links |= dynamic_links
    output_names = {
        path.name for path in (run / "outputs").rglob("*") if path.is_file()
    }
    results = []
    for assertion in meta.get("assertions", []):
        lower = assertion.lower()
        if "report.html, qa.json, run.webm, and trace.zip" in assertion:
            wanted = {"report.html", "qa.json", "run.webm", "trace.zip"}
            passed = wanted <= links and wanted <= output_names
            evidence = f"links={sorted(links)}; outputs={sorted(output_names)}"
        elif lower.startswith("run.webm is rendered"):
            passed = any(
                basename(src) == "run.webm" and controls and depth == 0
                for src, controls, depth in page.videos
            )
            evidence = f"videos={page.videos}"
        elif lower.startswith("the artifact links are visible"):
            wanted = (
                {"report.html", "qa.json", "run.webm", "trace.zip"}
                if meta.get("eval_id") == 8
                else {"current-report.html", "current-qa.json"}
            )
            passed = wanted <= visible_links
            evidence = f"visible_links={sorted(visible_links)}"
        elif "current-report.html and current-qa.json" in assertion:
            wanted = {"current-report.html", "current-qa.json"}
            passed = wanted <= links and wanted <= output_names
            evidence = f"links={sorted(links)}; outputs={sorted(output_names)}"
        elif "does not link or copy old-failure.webm" in lower:
            passed = (
                "old-failure.webm" not in links
                and "old-failure.webm" not in output_names
            )
            evidence = f"linked={'old-failure.webm' in links}; copied={'old-failure.webm' in output_names}"
        elif (
            "explicitly states that this session produced no independent sub-artifacts"
            in lower
        ):
            phrases = (
                "未产生独立子产物",
                "没有独立子产物",
                "无独立子产物",
                "未生成独立子产物",
                "no independent sub-artifacts",
            )
            passed = any(phrase in html.lower() for phrase in phrases)
            evidence = (
                f"matched={[phrase for phrase in phrases if phrase in html.lower()]}"
            )
        elif "contains no artifact download or placeholder links" in lower:
            artifact_suffixes = (
                ".html",
                ".json",
                ".webm",
                ".zip",
                ".pdf",
                ".csv",
                ".png",
                ".svg",
            )
            artifacts = {
                name for name in links if name.lower().endswith(artifact_suffixes)
            }
            passed = not artifacts
            evidence = f"artifact_links={sorted(artifacts)}"
        elif "footer includes" in lower:
            expected = {
                8: ("/tmp/pitch-video", "implicit-session-8"),
                9: ("/tmp/scoped-recap", "implicit-session-9"),
                10: ("/tmp/no-artifacts", "implicit-session-10"),
            }[meta["eval_id"]]
            passed = all(value in html for value in expected)
            evidence = f"project={expected[0] in html}; session={expected[1] in html}"
        else:
            passed = False
            evidence = "No deterministic check matched this assertion."
        results.append({"text": assertion, "passed": passed, "evidence": evidence})
    count = sum(item["passed"] for item in results)
    output = {
        "expectations": results,
        "summary": {
            "passed": count,
            "failed": len(results) - count,
            "total": len(results),
            "pass_rate": count / len(results) if results else 0,
        },
        "execution_metrics": load_json(run / "outputs/metrics.json"),
        "timing": load_json(run / "timing.json"),
        "claims": [],
        "user_notes_summary": {
            "uncertainties": [],
            "needs_review": [],
            "workarounds": [],
        },
        "eval_feedback": {
            "suggestions": [],
            "overall": "Assertions inspect proactive discovery, main-page visibility, scope, empty state, and provenance.",
        },
    }
    (run / "grading.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    )
    return meta.get("eval_name"), run.parent.parent.name, output["summary"]


for eval_dir in sorted(ROOT.glob("eval-*")):
    for config in ("with_skill", "without_skill"):
        run = eval_dir / config / "run-1"
        if (run / "outputs/main.html").exists():
            print(grade(run))
