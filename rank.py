#!/usr/bin/env python3
"""
rank.py — Redrob Intelligent Candidate Ranking Engine
IndiaRuns HackSkill2 | Track 1

Usage:
    python rank.py --candidates data/sample_candidates.json --out outputs/submission_sample.csv
    python rank.py --candidates candidates.jsonl.gz --out submission.csv
    python rank.py --candidates candidates.jsonl.gz --out submission.csv --html report.html
"""

import argparse
import csv
import gzip
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.engine import score_candidate
from src.report import generate_html_report
from src.pretty import (
    banner, section, progress_bar, candidate_card, summary_table,
    success, warn, info, GREEN, CYAN, YELLOW, RESET, BOLD,
)


def load_candidates(path):
    p = Path(path)
    cands = []
    if p.suffix == ".gz":
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    cands.append(json.loads(line))
    elif p.suffix == ".jsonl":
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    cands.append(json.loads(line))
    elif p.suffix == ".json":
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        cands = data if isinstance(data, list) else [data]
    else:
        raise ValueError(f"Unsupported format: {p.suffix}")
    return cands


def write_csv(ranked, out_path):
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank, item in enumerate(ranked, start=1):
            w.writerow([item["candidate_id"], rank, item["score"], item["reasoning"]])


def main():
    parser = argparse.ArgumentParser(description="Redrob Candidate Ranking Engine")
    parser.add_argument("--candidates", required=True, help="Path to candidates file")
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--top-n", type=int, default=100, dest="top_n", help="Number of candidates to output")
    parser.add_argument("--debug", action="store_true", help="Print score breakdown")
    parser.add_argument("--html", default=None, help="Optional path to write a styled HTML report")
    args = parser.parse_args()

    t0 = time.time()
    banner()

    # ── Load ──────────────────────────────────────────────
    section("LOADING CANDIDATES")
    candidates = load_candidates(args.candidates)
    success(f"Loaded {len(candidates):,} candidate profiles from {Path(args.candidates).name}")

    # ── Score ─────────────────────────────────────────────
    section("SCORING ENGINE")
    info("Running honeypot detection + 5-signal scorer...")
    scored, honeypots = [], 0
    n = len(candidates)
    for i, c in enumerate(candidates):
        result = score_candidate(c)
        if result["is_honeypot"]:
            honeypots += 1
        else:
            scored.append(result)
        if n >= 200 and ((i + 1) % max(n // 25, 1) == 0 or i + 1 == n):
            progress_bar(i + 1, n)
    if n >= 200:
        print()

    elapsed_score = time.time() - t0
    success(f"Scored {len(scored):,} valid candidates in {elapsed_score:.2f}s")
    if honeypots:
        warn(f"Detected & excluded {honeypots} honeypot profile(s)")
    else:
        info("No honeypots detected in this batch")

    # ── Rank ──────────────────────────────────────────────
    scored.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    top = scored[:args.top_n]
    if len(top) < args.top_n:
        warn(f"Only {len(top)} candidates available (requested {args.top_n})")

    # ── Write CSV ─────────────────────────────────────────
    section("WRITING SUBMISSION")
    write_csv(top, args.out)
    success(f"submission.csv written -> {args.out}")

    # ── Write HTML report ────────────────────────────────
    if args.html:
        generate_html_report(top, candidates, args.html, honeypots, len(candidates))
        success(f"HTML report written -> {args.html}")

    # ── Summary table ─────────────────────────────────────
    section(f"TOP {min(10, len(top))} CANDIDATES")
    for i, item in enumerate(top[:10], 1):
        orig = next((c for c in candidates if c["candidate_id"] == item["candidate_id"]), {})
        candidate_card(i, item, orig, debug=args.debug)

    section("RUN SUMMARY")
    summary_table({
        "Total candidates":  f"{len(candidates):,}",
        "Honeypots removed": f"{honeypots}",
        "Valid candidates":  f"{len(scored):,}",
        "Ranked output":     f"{len(top)} rows",
        "Runtime":           f"{time.time()-t0:.2f}s",
        "Output file":       args.out,
    })
    print(f"\n{GREEN}{BOLD}  ✓ DONE — ready for submission!{RESET}\n")


if __name__ == "__main__":
    main()