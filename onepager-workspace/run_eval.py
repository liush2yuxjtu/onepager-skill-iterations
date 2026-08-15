import json
import subprocess
import sys
import time
from pathlib import Path


def load_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot load {path}: {exc}") from exc


cfg, eval_name = sys.argv[1:3]
root = Path("/Users/liushiyuwin/.pi/skills/onepager-workspace")
run = root / "iteration-1" / eval_name / cfg
meta = load_json(run.parent / "eval_metadata.json")
evals = load_json(Path("/Users/liushiyuwin/.pi/skills/onepager/evals/evals.json"))[
    "evals"
]
e = next(x for x in evals if x["id"] == meta["eval_id"])
skill = (
    Path("/Users/liushiyuwin/.pi/skills/onepager")
    if cfg == "with_skill"
    else root / "skill-snapshot"
)
out = run / "outputs"
files = [
    str(Path("/Users/liushiyuwin/.pi/skills/onepager") / f) for f in e.get("files", [])
]
prompt = f"""Execute this evaluation task using the loaded onepager skill.\nTask: {e["prompt"]}\nInput files: {files}\nSave every deliverable under: {out}\nCreate the final main HTML as {out / "main.html"}. Copy only session-owned linked files needed for a portable relative-link bundle into that output directory. Do not modify the skill. Verify the HTML and finish with a concise summary."""
cmd = [
    "pi",
    "--print",
    "--mode",
    "json",
    "--no-session",
    "--no-context-files",
    "--no-extensions",
    "--no-skills",
    "--skill",
    str(skill),
    "--provider",
    "openai-codex",
    "--model",
    "gpt-5.6-sol",
    "--thinking",
    "medium",
    prompt,
]
start = time.time()
p = subprocess.run(
    cmd,
    cwd="/Users/liushiyuwin",
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
duration = time.time() - start
(run / "transcript.jsonl").write_text(p.stdout)
usage = 0
for line in p.stdout.splitlines():
    try:
        o = json.loads(line)
        u = o.get("usage") or o.get("message", {}).get("usage") or {}
        usage = max(
            usage,
            int(
                u.get("total_tokens", 0)
                or (u.get("input_tokens", 0) + u.get("output_tokens", 0))
            ),
        )
    except Exception:
        pass
(run / "timing.json").write_text(
    json.dumps(
        {
            "total_tokens": usage,
            "duration_ms": round(duration * 1000),
            "total_duration_seconds": round(duration, 3),
            "exit_code": p.returncode,
        },
        indent=2,
    )
    + "\n"
)
files_created = [str(x.relative_to(out)) for x in out.rglob("*") if x.is_file()]
(run / "outputs" / "metrics.json").write_text(
    json.dumps(
        {
            "tool_calls": {},
            "total_tool_calls": 0,
            "total_steps": 0,
            "files_created": files_created,
            "errors_encountered": 0 if p.returncode == 0 else 1,
            "output_chars": sum(
                x.stat().st_size for x in out.rglob("*") if x.is_file()
            ),
            "transcript_chars": len(p.stdout),
        },
        indent=2,
    )
    + "\n"
)
print(
    json.dumps(
        {
            "config": cfg,
            "eval": eval_name,
            "exit": p.returncode,
            "duration": duration,
            "tokens": usage,
            "files": files_created,
        }
    )
)
sys.exit(p.returncode)
