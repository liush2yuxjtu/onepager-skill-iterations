import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/Users/liushiyuwin/.pi/skills/onepager-workspace")
SKILL = Path("/Users/liushiyuwin/.pi/skills/onepager")


def load_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot load {path}: {exc}") from exc


def safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


iteration, config, eval_id_text, eval_name = sys.argv[1:5]
try:
    eval_id = int(eval_id_text)
except ValueError as exc:
    raise SystemExit(f"Invalid eval ID: {eval_id_text}") from exc
run = ROOT / iteration / f"eval-{eval_id}-{eval_name}" / config / "run-1"
out = run / "outputs"
out.mkdir(parents=True, exist_ok=True)
evals = load_json(SKILL / "evals/evals.json")["evals"]
eval_case = next(item for item in evals if item["id"] == eval_id)
input_files = [str(SKILL / item) for item in eval_case.get("files", [])]
loaded_skill = SKILL if config == "with_skill" else ROOT / "skill-snapshot"
prompt = f"""Execute this evaluation task using the loaded onepager skill.
Task: {eval_case["prompt"]}
Input files: {input_files}
Save the final Onepager as {out / "main.html"} and keep its local deliverables portable within {out}.
Do not modify the skill or eval fixtures. Validate the result and finish concisely."""
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
    str(loaded_skill),
    "--provider",
    "openai-codex",
    "--model",
    "gpt-5.6-sol",
    "--thinking",
    "medium",
    prompt,
]
start = time.time()
usage = 0
kept = []
with subprocess.Popen(
    cmd,
    cwd="/Users/liushiyuwin",
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
) as proc:
    if proc.stdout is None:
        proc.kill()
        raise SystemExit("Pi executor did not expose stdout")
    for line in proc.stdout:
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if event.get("type") in {
            "tool_execution_start",
            "tool_execution_end",
            "message_end",
        }:
            kept.append(event)
        message = event.get("message")
        if isinstance(message, dict):
            current = message.get("usage", {}).get("totalTokens", 0)
            usage = max(usage, safe_int(current))
    exit_code = proc.wait()
duration = time.time() - start
(run / "transcript.json").write_text(
    json.dumps(kept, ensure_ascii=False, indent=2) + "\n"
)
(run / "timing.json").write_text(
    json.dumps(
        {
            "total_tokens": usage,
            "duration_ms": round(duration * 1000),
            "total_duration_seconds": round(duration, 3),
            "exit_code": exit_code,
        },
        indent=2,
    )
    + "\n"
)
files = [path for path in out.rglob("*") if path.is_file()]
(out / "metrics.json").write_text(
    json.dumps(
        {
            "tool_calls": {},
            "total_tool_calls": 0,
            "total_steps": 0,
            "files_created": [str(path.relative_to(out)) for path in files],
            "errors_encountered": 1 if exit_code else 0,
            "output_chars": sum(path.stat().st_size for path in files),
            "transcript_chars": len(json.dumps(kept, ensure_ascii=False)),
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n"
)
print(
    json.dumps(
        {
            "config": config,
            "eval": eval_name,
            "exit": exit_code,
            "seconds": round(duration, 2),
            "tokens": usage,
        }
    )
)
raise SystemExit(exit_code)
