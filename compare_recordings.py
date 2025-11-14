
#!/usr/bin/env python3
"""
compare_recordings.py

Compare two UI recording JSON logs and compute:
- Typed text (best-effort reconstruction)
- Keystroke count (non-Shift)
- Click counts (total, pre-Enter, post-Enter)
- Index of first Enter in the overall event sequence
- Active duration (first → last non-manual event)
- Summary comparison (Agent vs Benchmark)

Manual events (e.g., start/stop recording) are excluded by default via window title filters.
You can add more substrings to match via --manual-exclude.

Usage:
  python compare_recordings.py agent.json benchmark.json \
    --label-a Agent --label-b Benchmark \
    --manual-exclude "system32\\cmd.exe" "Confirm Stop Recording" "Program Manager" \
    --out /path/to/report.json
"""

import json
import argparse
import os
import re
import csv
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional, Union
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# ---------- Parsing helpers ----------

def parse_timestamp(ts: Union[str, int, float]) -> float:
    """
    Parse timestamps that are either:
      - epoch milliseconds/seconds (int/float)
      - ISO-8601 strings
    Returns float seconds since epoch.
    """
    if isinstance(ts, (int, float)):
        # Heuristic: if it's large, assume ms
        if ts > 1e12:
            return ts / 1000.0
        return float(ts)
    if isinstance(ts, str):
        s = ts.strip().replace('Z', '+00:00')
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except Exception:
            pass
        try:
            v = float(s)
            return v / 1000.0 if v > 1e12 else v
        except Exception:
            raise ValueError(f"Unrecognized timestamp format: {ts!r}")
    raise TypeError(f"Unsupported timestamp type: {type(ts)}")

def coalesce_events(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in ("events", "log", "data"):
            if k in payload and isinstance(payload[k], list):
                return payload[k]
    raise ValueError("Could not find event list in JSON. Expected a top-level list or a dict with 'events'.")

# ---------- Filtering ----------

def is_manual_event(evt: Dict[str, Any], manual_substrings: List[str]) -> bool:
    title = str(evt.get("window_title") or evt.get("title") or "").lower()
    proc = str(evt.get("process") or "").lower()
    cat  = str(evt.get("category") or "").lower()
    combined = " ".join([title, proc, cat])
    for sub in manual_substrings:
        if sub.lower() in combined:
            return True
    return False

# ---------- Typing / clicks ----------

ENTER_KEYS = {"enter", "return"}
SHIFT_KEYS = {"shift", "shiftleft", "shiftright"}

KEY_TO_CHAR = {
    "space": " ",
    "underscore": "_",
    "minus": "-",
    "period": ".",
    "slash": "/",
    "backslash": "\\",
    "comma": ",",
    "semicolon": ";",
    "equal": "=",
    "plus": "+",
    "tab": "\t",
}

def normalize_keyname(k: Any) -> str:
    if k is None:
        return ""
    s = str(k).strip()
    s = s.replace("Key.", "").replace("Keyboard.", "").replace("VK_", "")
    return s.lower()

def event_kind(evt: Dict[str, Any]) -> str:
    t = str(evt.get("type") or evt.get("event") or "").lower()
    if "key" in t:
        return "key"
    if "click" in t or "mouse" in t:
        return "click" if "click" in t else "mouse"
    return t or "other"

def extract_text_from_event(evt: Dict[str, Any]) -> str:
    txt = evt.get("text")
    if isinstance(txt, str) and txt:
        return txt
    return ""

def reconstruct_typed_text(events: List[Dict[str, Any]]) -> str:
    out = []
    for e in events:
        kind = event_kind(e)
        if kind != "key":
            continue
        txt = extract_text_from_event(e)
        if txt:
            out.append(txt)
            continue
        keyname = normalize_keyname(e.get("key") or e.get("key_name") or e.get("code"))
        if not keyname:
            continue
        if keyname in SHIFT_KEYS:
            continue
        if keyname in ENTER_KEYS:
            continue
        if len(keyname) == 1:
            out.append(keyname)
        elif keyname in KEY_TO_CHAR:
            out.append(KEY_TO_CHAR[keyname])
        else:
            m = re.fullmatch(r"[a-z0-9]", keyname)
            if m:
                out.append(keyname)
    return "".join(out)

def count_keystrokes_non_shift(events: List[Dict[str, Any]]) -> int:
    c = 0
    for e in events:
        if event_kind(e) != "key":
            continue
        kn = normalize_keyname(e.get("key") or e.get("key_name") or e.get("code"))
        if kn and kn not in SHIFT_KEYS:
            c += 1
    return c

def find_first_enter_index(events: List[Dict[str, Any]]) -> Optional[int]:
    for i, e in enumerate(events, start=1):
        if event_kind(e) != "key":
            continue
        kn = normalize_keyname(e.get("key") or e.get("key_name") or e.get("code"))
        if kn in ENTER_KEYS:
            return i
    return None

def count_clicks(events: List[Dict[str, Any]]) -> int:
    return sum(1 for e in events if event_kind(e) in ("click", "mouse"))

def split_pre_post_enter(events: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    idx = find_first_enter_index(events)
    if idx is None:
        return events, []
    pre = events[:idx]
    post = events[idx:]
    return pre, post

def active_duration_seconds(events: List[Dict[str, Any]]) -> Optional[float]:
    if not events:
        return None
    times = []
    for e in events:
        ts = e.get("timestamp") or e.get("time") or e.get("@timestamp")
        if ts is None:
            continue
        try:
            times.append(parse_timestamp(ts))
        except Exception:
            continue
    if not times:
        return None
    return max(times) - min(times)

# ---------- Per-recording analysis ----------

def analyze_recording(events_raw: List[Dict[str, Any]], manual_substrings: List[str]) -> Dict[str, Any]:
    events = [e for e in events_raw if not is_manual_event(e, manual_substrings)]
    typed_text = reconstruct_typed_text(events)
    keystrokes_ns = count_keystrokes_non_shift(events)
    clicks_total = count_clicks(events)
    pre, post = split_pre_post_enter(events)
    clicks_pre = count_clicks(pre)
    clicks_post = count_clicks(post)
    enter_index = find_first_enter_index(events)
    duration = active_duration_seconds(events)

    return {
        "total_events_ex_manual": len(events),
        "typed_text_best_effort": typed_text,
        "keystrokes_non_shift": keystrokes_ns,
        "clicks_total": clicks_total,
        "clicks_pre_enter": clicks_pre,
        "clicks_post_enter": clicks_post,
        "first_enter_index": enter_index,
        "active_duration_seconds": duration,
    }

def load_events(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return coalesce_events(data)

def format_seconds(s: Optional[float]) -> str:
    if s is None:
        return "N/A"
    return f"{s:.1f} s"

def write_csv_report(report: Dict[str, Any], csv_path: str):
    """Write comparison report to CSV format."""
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(["Recording Comparison Report"])
        writer.writerow([])
        
        # File info
        writer.writerow(["Files"])
        writer.writerow(["Label A", report["labels"]["A"]])
        writer.writerow(["File A", report["files"]["A"]])
        writer.writerow(["Label B", report["labels"]["B"]])
        writer.writerow(["File B", report["files"]["B"]])
        writer.writerow([])
        
        # Metrics comparison
        writer.writerow(["Metric", "A", "B", "Delta (A-B)"])
        
        metrics = [
            ("Events (ex. manual)", "total_events_ex_manual"),
            ("Keystrokes non-Shift", "keystrokes_non_shift"),
            ("Clicks total", "clicks_total"),
            ("Clicks pre-Enter", "clicks_pre_enter"),
            ("Clicks post-Enter", "clicks_post_enter"),
            ("First Enter index", "first_enter_index"),
            ("Active duration (s)", "active_duration_seconds")
        ]
        
        for metric_name, metric_key in metrics:
            a_val = report["A_metrics"][metric_key]
            b_val = report["B_metrics"][metric_key]
            
            a_str = format_seconds(a_val) if "duration" in metric_key else ("N/A" if a_val is None else str(a_val))
            b_str = format_seconds(b_val) if "duration" in metric_key else ("N/A" if b_val is None else str(b_val))
            
            if isinstance(a_val, (int, float)) and isinstance(b_val, (int, float)):
                delta = a_val - b_val
                delta_str = f"{delta:+.1f}" if "duration" in metric_key or isinstance(delta, float) else f"{int(delta):+d}"
            else:
                delta_str = "N/A"
                
            writer.writerow([metric_name, a_str, b_str, delta_str])
        
        writer.writerow([])
        
        # Typed text comparison
        writer.writerow(["Typed Text Analysis"])
        writer.writerow(["Text Equal?", "YES" if report["comparison"]["typed_text_equal"] else "NO"])
        writer.writerow(["A typed", repr(report["A_metrics"]["typed_text_best_effort"])])
        writer.writerow(["B typed", repr(report["B_metrics"]["typed_text_best_effort"])])
        writer.writerow([])
        
        # Add CSV report explanation
        writer.writerow(["=== CSV REPORT EXPLANATION ==="])
        writer.writerow([])
        writer.writerow(["METRICS DESCRIPTION:"])
        writer.writerow(["• Events (ex. manual)", "Total UI events excluding manual/system actions"])
        writer.writerow(["• Keystrokes non-Shift", "Number of keystroke events (excluding Shift keys)"])
        writer.writerow(["• Clicks total", "Total number of mouse click events"])
        writer.writerow(["• Clicks pre-Enter", "Mouse clicks before first Enter key press"])
        writer.writerow(["• Clicks post-Enter", "Mouse clicks after first Enter key press"])
        writer.writerow(["• First Enter index", "Position of first Enter key in event sequence"])
        writer.writerow(["• Active duration", "Time from first to last event (seconds)"])
        writer.writerow([])
        writer.writerow(["INTERPRETATION GUIDE:"])
        writer.writerow(["• Positive Delta (A-B)", "A performed more actions/took longer than B"])
        writer.writerow(["• Negative Delta (A-B)", "A performed fewer actions/was faster than B"])
        writer.writerow(["• Lower event counts", "Generally indicate higher efficiency"])
        writer.writerow(["• Shorter duration", "Usually indicates better performance"])
        writer.writerow(["• Text match = YES", "Both recordings produced same text input"])
        writer.writerow(["• Text match = NO", "Different text inputs detected (accuracy issue)"])
        writer.writerow([])
        writer.writerow(["PERFORMANCE INDICATORS:"])
        writer.writerow(["• Efficiency", "Fewer events + shorter duration = more efficient"])
        writer.writerow(["• Accuracy", "Text match + similar click patterns = higher accuracy"])
        writer.writerow(["• Consistency", "Similar event distribution = more predictable behavior"])
        
def generate_llm_analysis(report: Dict[str, Any], provider: str, api_key: Optional[str] = None) -> str:
    """Generate LLM-powered analysis of the performance comparison."""
    
    if provider == "openai" and not HAS_OPENAI:
        raise ImportError("OpenAI library not installed. Install with: pip install openai")
    elif provider == "anthropic" and not HAS_ANTHROPIC:
        raise ImportError("Anthropic library not installed. Install with: pip install anthropic")
    
    # Get API key from parameter or environment
    if api_key is None:
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        raise ValueError(f"No API key provided for {provider}. Set --api-key or {provider.upper()}_API_KEY environment variable.")
    
    # Prepare data for LLM
    a_label = report["labels"]["A"]
    b_label = report["labels"]["B"]
    a_metrics = report["A_metrics"]
    b_metrics = report["B_metrics"]
    comparison = report["comparison"]
    
    # Calculate percentage differences for better analysis
    def calc_pct_diff(agent_val, benchmark_val):
        if benchmark_val is None or benchmark_val == 0:
            return "N/A"
        if agent_val is None:
            return "N/A"
        return f"{((agent_val - benchmark_val) / benchmark_val) * 100:+.1f}%"
    
    events_pct = calc_pct_diff(a_metrics['total_events_ex_manual'], b_metrics['total_events_ex_manual'])
    duration_pct = calc_pct_diff(a_metrics['active_duration_seconds'], b_metrics['active_duration_seconds'])
    clicks_pct = calc_pct_diff(a_metrics['clicks_total'], b_metrics['clicks_total'])
    
    prompt = f"""You are evaluating an AI agent's UI automation performance against a human benchmark. 

**CONTEXT:**
- {a_label}: AI Agent being evaluated
- {b_label}: Human benchmark/reference performance
- Task: UI automation workflow comparison

**PERFORMANCE METRICS:**
┌─────────────────────────┬─────────────┬─────────────┬──────────────┐
│ Metric                  │ {a_label:<11} │ {b_label:<11} │ Difference   │
├─────────────────────────┼─────────────┼─────────────┼──────────────┤
│ Total Events            │ {a_metrics['total_events_ex_manual']:<11} │ {b_metrics['total_events_ex_manual']:<11} │ {events_pct:<12} │
│ Duration                │ {format_seconds(a_metrics['active_duration_seconds']):<11} │ {format_seconds(b_metrics['active_duration_seconds']):<11} │ {duration_pct:<12} │
│ Total Clicks            │ {a_metrics['clicks_total']:<11} │ {b_metrics['clicks_total']:<11} │ {clicks_pct:<12} │
│ Keystrokes              │ {a_metrics['keystrokes_non_shift']:<11} │ {b_metrics['keystrokes_non_shift']:<11} │ {calc_pct_diff(a_metrics['keystrokes_non_shift'], b_metrics['keystrokes_non_shift']):<12} │
│ Pre-Enter Clicks        │ {a_metrics['clicks_pre_enter']:<11} │ {b_metrics['clicks_pre_enter']:<11} │ {calc_pct_diff(a_metrics['clicks_pre_enter'], b_metrics['clicks_pre_enter']):<12} │
│ Post-Enter Clicks       │ {a_metrics['clicks_post_enter']:<11} │ {b_metrics['clicks_post_enter']:<11} │ {calc_pct_diff(a_metrics['clicks_post_enter'], b_metrics['clicks_post_enter']):<12} │
│ First Enter Position    │ {a_metrics['first_enter_index'] or 'N/A':<11} │ {b_metrics['first_enter_index'] or 'N/A':<11} │ {calc_pct_diff(a_metrics['first_enter_index'], b_metrics['first_enter_index']):<12} │
└─────────────────────────┴─────────────┴─────────────┴──────────────┘

**INPUT ACCURACY:**
- Text Input Match: {'✅ EXACT MATCH' if comparison['typed_text_equal'] else '❌ MISMATCH'}
- {a_label} typed: {repr(a_metrics['typed_text_best_effort'])}
- {b_label} typed: {repr(b_metrics['typed_text_best_effort'])}

**ANALYSIS FRAMEWORK:**
Provide a comprehensive evaluation covering:

🎯 **PERFORMANCE ASSESSMENT:**
- Speed Efficiency: Is the agent faster/slower than human? Why?
- Interaction Efficiency: Does the agent use fewer/more actions?
- Task Completion: Did both achieve the same outcome?

🔍 **BEHAVIORAL ANALYSIS:**
- Interaction Patterns: How does the agent's approach differ?
- Navigation Strategy: Different paths taken to complete the task?
- Error Recovery: Any signs of hesitation, corrections, or retries?

📊 **QUANTITATIVE INSIGHTS:**
- Which metrics favor the agent vs. human?
- Are there concerning performance gaps?
- What do the timing patterns reveal?

💡 **ACTIONABLE RECOMMENDATIONS:**
- Specific areas where the agent needs improvement
- Strengths to leverage in future development
- Optimization opportunities (speed, accuracy, efficiency)
- Training data or model adjustments needed

🏆 **OVERALL VERDICT:**
- Agent readiness assessment (production-ready, needs work, etc.)
- Confidence level in agent performance
- Risk assessment for deployment

Focus on practical, actionable insights that help improve the AI agent's performance."""
    
    if provider == "openai":
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are an expert AI agent performance analyst specializing in UI automation evaluation. Provide detailed, actionable insights with specific recommendations."},
                {"role": "user", "content": prompt}
            ],
            # Comment out for GPT 5 mini (no token and temperature parameters)
            # max_tokens=2000,
            # temperature=0.2
        )
        return response.choices[0].message.content
    
    elif provider == "anthropic":
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1500,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    
    else:
        raise ValueError(f"Unsupported provider: {provider}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file_a", help="Recording JSON A (e.g., Agent)")
    ap.add_argument("file_b", help="Recording JSON B (e.g., Benchmark)")
    ap.add_argument("--label-a", default="A", help="Label for A")
    ap.add_argument("--label-b", default="B", help="Label for B")
    ap.add_argument("--manual-exclude", nargs="*", default=[
        r"system32\\cmd.exe",
        "confirm stop recording",
        "program manager",
    ], help="Substrings to mark events as manual (window title/process/category match).")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "tests", "output", f"report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.json"), help="Optional path to write JSON report.")
    ap.add_argument("--csv", default=os.path.join(os.path.dirname(__file__), "tests", "output", f"report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv"), help="Optional path to write CSV report.")
    ap.add_argument("--llm-analysis", action="store_true", help="Generate LLM-powered performance analysis.")
    ap.add_argument("--llm-provider", choices=["openai", "anthropic"], default="openai", help="LLM provider to use for analysis.")
    ap.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"), help="API key for LLM provider (or set OPENAI_API_KEY/ANTHROPIC_API_KEY env var).")
    args = ap.parse_args()

    events_a = load_events(args.file_a)
    events_b = load_events(args.file_b)

    res_a = analyze_recording(events_a, args.manual_exclude)
    res_b = analyze_recording(events_b, args.manual_exclude)

    def delta(a, b):
        if a is None or b is None:
            return None
        return a - b

    report = {
        "labels": {"A": args.label_a, "B": args.label_b},
        "files": {"A": os.path.abspath(args.file_a), "B": os.path.abspath(args.file_b)},
        "manual_exclude": args.manual_exclude,
        "A_metrics": res_a,
        "B_metrics": res_b,
        "comparison": {
            "typed_text_equal": (res_a["typed_text_best_effort"] == res_b["typed_text_best_effort"]),
            "keystrokes_non_shift_delta": delta(res_a["keystrokes_non_shift"], res_b["keystrokes_non_shift"]),
            "clicks_total_delta": delta(res_a["clicks_total"], res_b["clicks_total"]),
            "clicks_pre_enter_delta": delta(res_a["clicks_pre_enter"], res_b["clicks_pre_enter"]),
            "clicks_post_enter_delta": delta(res_a["clicks_post_enter"], res_b["clicks_post_enter"]),
            "first_enter_index_delta": delta(res_a["first_enter_index"], res_b["first_enter_index"]),
            "active_duration_seconds_delta": delta(res_a["active_duration_seconds"], res_b["active_duration_seconds"]),
        }
    }

    print("=== Recording Comparison ===")
    print(f"A: {args.label_a} -> {args.file_a}")
    print(f"B: {args.label_b} -> {args.file_b}")
    print(f"Manual exclusions: {args.manual_exclude}\n")

    def to_str_num(v):
        if v is None:
            return "N/A"
        if isinstance(v, float):
            return f"{v:.1f}"
        return str(v)

    def line(label, a, b, is_seconds=False):
        a_str = format_seconds(a) if is_seconds else to_str_num(a)
        b_str = format_seconds(b) if is_seconds else to_str_num(b)
        # Delta only if numbers and not None
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            d = a - b
            d_str = f"{d:+.1f}" if (is_seconds or isinstance(a, float) or isinstance(b, float)) else f"{int(d):+d}"
            print(f"{label:<28} A={a_str:>10}  B={b_str:>10}  Δ={d_str}")
        else:
            print(f"{label:<28} A={a_str:>10}  B={b_str:>10}")

    line("Events (ex. manual)", report["A_metrics"]["total_events_ex_manual"], report["B_metrics"]["total_events_ex_manual"])
    line("Keystrokes non-Shift", report["A_metrics"]["keystrokes_non_shift"], report["B_metrics"]["keystrokes_non_shift"])
    line("Clicks total",        report["A_metrics"]["clicks_total"],          report["B_metrics"]["clicks_total"])
    line("Clicks pre-Enter",    report["A_metrics"]["clicks_pre_enter"],      report["B_metrics"]["clicks_pre_enter"])
    line("Clicks post-Enter",   report["A_metrics"]["clicks_post_enter"],     report["B_metrics"]["clicks_post_enter"])
    line("First Enter index",   report["A_metrics"]["first_enter_index"],     report["B_metrics"]["first_enter_index"])
    line("Active duration",     report["A_metrics"]["active_duration_seconds"], report["B_metrics"]["active_duration_seconds"], is_seconds=True)
    print()

    eq = report["comparison"]["typed_text_equal"]
    print(f"Typed text equal? {'YES' if eq else 'NO'}")
    print(f"A typed (best-effort): {report['A_metrics']['typed_text_best_effort']!r}")
    print(f"B typed (best-effort): {report['B_metrics']['typed_text_best_effort']!r}\n")

    # Generate LLM analysis if requested
    llm_analysis = None
    if args.llm_analysis:
        try:
            print("Generating LLM analysis...")
            llm_analysis = generate_llm_analysis(report, args.llm_provider, args.api_key)
            print("\n=== LLM Performance Analysis ===")
            print(llm_analysis)
            print("\n")
            
            # Add analysis to report
            report["llm_analysis"] = {
                "provider": args.llm_provider,
                "analysis": llm_analysis
            }
        except Exception as e:
            print(f"Error generating LLM analysis: {e}")
            print("Continuing without LLM analysis...\n")

    # Write JSON report
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Wrote JSON report to: {args.out}")
    
    # Write CSV report
    if args.csv:
        write_csv_report(report, args.csv)
        print(f"Wrote CSV report to: {args.csv}")
    
    # Write LLM analysis to text file
    if llm_analysis and (args.out or args.csv):
        # Determine base filename from JSON or CSV output
        if args.out:
            base_path = os.path.splitext(args.out)[0]
        elif args.csv:
            base_path = os.path.splitext(args.csv)[0]
        
        txt_path = f"{base_path}.txt"
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("=== AI AGENT PERFORMANCE ANALYSIS ===\n\n")
            f.write(f"Analysis Provider: {args.llm_provider}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Agent: {report['labels']['A']}\n")
            f.write(f"Benchmark: {report['labels']['B']}\n\n")
            f.write("=" * 60 + "\n\n")
            f.write(llm_analysis)
            f.write("\n\n" + "=" * 60 + "\n")
            f.write("\nNote: This analysis was generated by AI and should be reviewed by domain experts.\n")
        
        print(f"Wrote LLM analysis to: {txt_path}")

if __name__ == "__main__":
    main()
