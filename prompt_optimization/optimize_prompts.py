"""
2) Offline prompt optimization (separate process)
- Use a small tuner script (Python or TS) to:
  - grid search or iteratively mutate the prompt (system + task + few-shots).
  - run on the benchmark set via VibeKit sandbox.
  - score with your evaluators (compiles? graph topology present? outputs match?).
  - keep a leaderboard; select the best prompt variant.
- Store the winning prompt as prompts/base.md with a version tag (e.g., v0.7). Commit it.
"""

import os, json, subprocess, tempfile, hashlib, time
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "prompts"
CANDIDATES_DIR = PROMPTS_DIR / "candidates"
BENCH_DIR = ROOT / "benchmarks" / "inputs"
# Optional directory holding reference python scripts that produced the benchmark JSONs
BENCH_CODE_DIR = ROOT / "benchmarks" / "code"

NODE_CMD = ["npm", "run", "dev", "--", "--prompt-file"]  # calls src/index.ts
ENV = os.environ.copy()
NO_PR = os.getenv("NO_PR")
# Force NO_PR during optimization to avoid PR spam
ENV["NO_PR"] = ENV.get("NO_PR", "1")

# Debug flag to echo full stdout/stderr
OPT_DEBUG = os.getenv("OPT_DEBUG", "0").lower() in ("1", "true", "yes")

# Where to store generated artifacts (prompts + codeWrites)
OUT_DIR = ROOT / "debug" / "optimizer" / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

print(ROOT)
print(PROMPTS_DIR)
print(CANDIDATES_DIR)
print(BENCH_DIR)
print(NO_PR)

def inject_prompt(prompt_template: str, input_json: dict, input_code: Optional[str]) -> str:
    """Render a prompt template with JSON and optional reference code.

    Replaces:
    - {{INPUT_JSON}} with pretty-printed JSON
    - {{REFERENCE_CODE}} with the provided python source or an empty string if None
    """
    rendered = prompt_template.replace("{{INPUT_JSON}}", json.dumps(input_json, indent=2))
    if "{{REFERENCE_CODE}}" in rendered:
        rendered = rendered.replace("{{REFERENCE_CODE}}", input_code or "")
    return rendered


def find_reference_code(input_json_path: Path) -> Optional[str]:
    """Attempt to locate a reference python script corresponding to the JSON.

    Search strategy (first hit wins):
    1) Same directory as the JSON with the same stem and .py extension
    2) benchmarks/code/<stem>.py
    Returns the file contents or None if not found.
    """
    stem = input_json_path.stem
    # 1) same directory
    local_py = input_json_path.with_suffix(".py")
    if local_py.exists():
        return local_py.read_text(encoding="utf-8")
    # 2) benchmarks/code
    code_py = BENCH_CODE_DIR / f"{stem}.py"
    if code_py.exists():
        return code_py.read_text(encoding="utf-8")
    return None

def run_once(rendered_prompt: str) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"prompt": rendered_prompt}, f, ensure_ascii=False)
        tmp_path = f.name

    print(f"Temp prompt file at: {tmp_path}")

    print(f"Running with prompt: {rendered_prompt}")

    print(f"Running index.ts with command: {NODE_CMD + [tmp_path]} at {ROOT}")

    # Prepare debug log directory
    debug_dir = ROOT / "debug" / "optimizer"
    debug_dir.mkdir(parents=True, exist_ok=True)
    run_stamp = str(int(time.time() * 1000))

    try:
        start = time.time()
        proc = subprocess.run(
            NODE_CMD + [tmp_path],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            shell=True,
            env=ENV,
            encoding="utf-8",
            errors="replace",  # avoid cp1252 decode crashes on Windows
        )
        duration = time.time() - start
        stdout_text = proc.stdout or ""
        stderr_text = proc.stderr or ""

        # Save raw logs to files for post-mortem debugging
        (debug_dir / f"stdout_{run_stamp}.log").write_text(stdout_text, encoding="utf-8", errors="replace")
        (debug_dir / f"stderr_{run_stamp}.log").write_text(stderr_text, encoding="utf-8", errors="replace")

        if OPT_DEBUG:
            print("--- STDOUT (tail) ---")
            print(stdout_text[-2000:])
            print("--- STDERR (tail) ---")
            print(stderr_text[-2000:])

        stdout = stdout_text.splitlines()

        try:
            s_idx = stdout.index("AGENT_RESPONSE_START")
            e_idx = stdout.index("AGENT_RESPONSE_END")
            payload = json.loads(stdout[s_idx + 1])
        except Exception:
            payload = {
                "exitCode": proc.returncode if proc.returncode is not None else 1,
                "error": "No AGENT_RESPONSE block",
                "raw": stdout_text[-1000:],
            }

        code_writes = []
        try:
            cw = payload.get("codeWrites")
            if isinstance(cw, list):
                for item in cw:
                    if isinstance(item, dict) and "path" in item and "content" in item:
                        code_writes.append({
                            "path": str(item.get("path")),
                            "content": str(item.get("content", ""))
                        })
        except Exception:
            pass

        return {
            "exit_code": int(payload.get("exitCode", proc.returncode if proc.returncode is not None else 1)),
            "error": payload.get("error"),
            "duration_s": round(duration, 2),
            "raw_tail": stdout_text[-1000:],
            "code_writes": code_writes,
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)

def score_result(res: dict) -> float:
    # Baseline: require success AND at least one code file written
    base = 1.0 if (res.get("exit_code") == 0 and res.get("code_writes")) else 0.0
    penalty = min(0.2, res["duration_s"] / 60.0)
    return max(0.0, base - penalty)


def _sanitize(name: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in name)[:80]


def save_artifacts(candidate_path: Path, input_path: Path, rendered_prompt: str, code_writes: list[dict]) -> Path:
    """Save the rendered prompt and generated code for later scoring/inspection.

    Returns the directory path where artifacts were saved.
    """
    cand_stem = _sanitize(candidate_path.stem)
    inp_stem = _sanitize(input_path.stem)
    run_dir = OUT_DIR / cand_stem / inp_stem
    run_dir.mkdir(parents=True, exist_ok=True)

    # Save prompt
    (run_dir / "prompt.txt").write_text(rendered_prompt, encoding="utf-8")

    # Save code files
    saved = []
    for idx, cw in enumerate(code_writes or []):
        src_path = str(cw.get("path", ""))
        content = str(cw.get("content", ""))
        fname = f"code_{idx}_" + _sanitize(Path(src_path).name or f"file_{idx}.txt")
        out_fp = run_dir / fname
        out_fp.write_text(content, encoding="utf-8")
        saved.append({"source_path": src_path, "saved_as": str(out_fp)})

    # Save metadata
    meta = {
        "candidate": str(candidate_path),
        "input": str(input_path),
        "files": saved,
    }
    (run_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return run_dir

def main():
    candidates = sorted(CANDIDATES_DIR.glob("*.md"))
    # print(BENCH_DIR)
    inputs = sorted(BENCH_DIR.glob("*.json"))
    # print(candidates)
    # print(inputs)
    if not candidates or not inputs:
        raise SystemExit("No candidates or inputs found.")

    leaderboard = []
    artifacts_index = []  # collect artifact locations for all runs
    for cand in candidates:
        tpl = cand.read_text(encoding="utf-8")
        total, n = 0.0, 0
        failures = 0

        for inp in inputs:
            input_json = json.loads(inp.read_text(encoding="utf-8"))
            input_code = find_reference_code(inp)
            rendered = inject_prompt(tpl, input_json, input_code)
            res = run_once(rendered)
            # Save artifacts for later scoring/inspection
            try:
                art_dir = save_artifacts(cand, inp, rendered, res.get("code_writes") or [])
            except Exception as e:
                art_dir = None
                if OPT_DEBUG:
                    print(f"Failed to save artifacts for {cand.name} / {inp.name}: {e}")

            total += score_result(res)
            n += 1
            failures += int(res["exit_code"] != 0)
            artifacts_index.append({
                "candidate": str(cand),
                "input": str(inp),
                "artifact_dir": str(art_dir) if art_dir else None,
                "result": res,
            })

        avg = total / max(1, n)
        leaderboard.append((avg, failures, cand))

    leaderboard.sort(key=lambda x: (-x[0], x[1], str(x[2])))
    print("\nPrompt Leaderboard (avg_score desc, failures asc):")
    for avg, fail, path in leaderboard:
        print(f"- {path.name:30}  score={avg:.3f}  fails={fail}")

    best = leaderboard[0][2]
    print(f"\nBest prompt: {best}")
    # Copy best to prompts/base.md for promotion
    (PROMPTS_DIR / "base.md").write_text(best.read_text(encoding="utf-8"), encoding="utf-8")

    # Write a summary index for all artifacts and results
    index_fp = OUT_DIR / "artifacts_index.json"
    index_fp.write_text(json.dumps(artifacts_index, indent=2), encoding="utf-8")
    print(f"Artifacts index written to: {index_fp}")

if __name__ == "__main__":
    main()