#!/usr/bin/env python3
"""
rank.py — Redrob Intelligent Candidate Ranking Engine
IndiaRuns HackSkill2 | Track 1

Usage:
    python rank.py --candidates data/sample_candidates.json --out outputs/submission_sample.csv
    python rank.py --candidates data/sample_candidates.json --out outputs/submission_sample.csv --debug
    python rank.py --candidates candidates.jsonl.gz --out submission.csv
"""

import argparse
import csv
import gzip
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.engine import score_candidate, is_honeypot


def load_candidates(path):
    p = Path(path)
    cands = []
    if p.suffix == ".gz":
        print(f"[loader] Opening gzip: {p.name}")
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    cands.append(json.loads(line))
    elif p.suffix == ".jsonl":
        print(f"[loader] Opening JSONL: {p.name}")
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    cands.append(json.loads(line))
    elif p.suffix == ".json":
        print(f"[loader] Opening JSON: {p.name}")
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        cands = data if isinstance(data, list) else [data]
    else:
        raise ValueError(f"Unsupported format: {p.suffix}")
    print(f"[loader] Loaded {len(cands):,} candidates")
    return cands


def write_csv(ranked, out_path):
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank, item in enumerate(ranked, start=1):
            w.writerow([item["candidate_id"], rank, item["score"], item["reasoning"]])
    print(f"[writer] Submission saved -> {p}")


def main():
    parser = argparse.ArgumentParser(description="Redrob Candidate Ranking Engine")
    parser.add_argument("--candidates", required=True, help="Path to candidates file")
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--top-n", type=int, default=100, dest="top_n", help="Number of candidates to output")
    parser.add_argument("--debug", action="store_true", help="Print score breakdown")
    args = parser.parse_args()

    t0 = time.time()

    candidates = load_candidates(args.candidates)

    print(f"[engine] Scoring {len(candidates):,} candidates...")
    scored = []
    honeypots = 0
    for i, c in enumerate(candidates):
        result = score_candidate(c)
        if result["is_honeypot"]:
            honeypots += 1
        else:
            scored.append(result)
        if (i + 1) % 10000 == 0:
            print(f"[engine] {i+1:,}/{len(candidates):,} ({time.time()-t0:.1f}s)")

    print(f"[engine] Honeypots removed: {honeypots}")
    print(f"[engine] Valid candidates:  {len(scored):,}")

    scored.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    top = scored[:args.top_n]

    if len(top) < args.top_n:
        print(f"[warn] Only {len(top)} candidates found (need {args.top_n})")

    write_csv(top, args.out)

    elapsed = time.time() - t0
    print(f"\n[done] Runtime: {elapsed:.1f}s")
    print(f"\n{'='*60}")
    print(f"  TOP 10 CANDIDATES")
    print(f"{'='*60}")
    for i, item in enumerate(top[:10], 1):
        print(f"  #{i:>2}  {item['candidate_id']}  score={item['score']:.4f}")
        print(f"       {item['reasoning'][:90]}...")
        if args.debug and item.get("breakdown"):
            bd = item["breakdown"]
            print(f"       skills={bd['skills']:.3f} career={bd['career']:.3f} "
                  f"exp={bd['experience']:.3f} loc={bd['location']:.3f} "
                  f"edu={bd['education']:.3f} x{bd['behavioral_multiplier']:.3f}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()