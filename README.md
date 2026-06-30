# 🎯 Redrob Intelligent Candidate Discovery & Ranking Engine
### IndiaRuns HackSkill2 · Track 1 · AI & Datathon Arena

---

## What This Is

A multi-signal candidate ranking system built for the **Senior AI Engineer** role at Redrob AI.

**Input:** 100,000 candidate profiles (JSON/JSONL) + the Job Description
**Output:** Top-100 ranked candidates as a CSV with explainable, one-line reasoning per candidate

**Constraints met:**
- ✅ CPU only — no GPU
- ✅ No external API calls during ranking
- ✅ < 5 minutes for 100K candidates (typically ~60–90s)
- ✅ < 2 GB RAM
- ✅ Exactly 100 ranked rows, validator-clean CSV format

---

## System Architecture

```
candidates.jsonl (or candidates.jsonl.gz)
        │
        ▼
  [Data Loader]  — supports .json / .jsonl / .jsonl.gz
        │
        ▼
 [Honeypot Detector]
   ├─ Impossible tenure durations
   ├─ Expert claims + 0 months usage
   ├─ YoE contradicts career history
   └─ Assessment scores contradict proficiency
        │
        ▼
 [Multi-Signal Scorer]
  ┌─────────────────────────────┐
  │  Career Trajectory  32%      │ ← title relevance, product vs consulting,
  │                               │   shipped-system signal, JD disqualifiers
  │  Skill Match        30%      │ ← required vs nice-to-have vs negative,
  │                               │   proficiency × duration × endorsement trust
  │  Location Fit        15%      │ ← Pune/Noida > Hyderabad/Mumbai/Delhi NCR
  │                               │   > rest of India > willing-to-relocate
  │  Experience Years    13%      │ ← calibrated to JD's ideal 6–8 yr range
  │  Education            10%     │ ← institution tier + CS field relevance
  └──────────────┬───────────────┘
                 │ base_score
                 × Behavioral Multiplier (0.1–1.5)
                   ├─ last_active_date recency
                   ├─ recruiter_response_rate
                   ├─ notice_period_days (JD: sub-30-day preferred)
                   ├─ github_activity_score
                   └─ interview_completion_rate
                 │
                 ▼
          final_score (0–1)
                 │
                 ▼
     [Top-100 CSV — ranked, scored, with reasoning]
     [Optional: styled HTML report for demo]
```

---

## Quick Start

### 1. Install dependencies (sandbox UI only — ranking itself needs zero installs)

```bash
pip install streamlit
```

### 2. Test on the sample dataset first

```bash
python rank.py --candidates data/sample_candidates.json --out outputs/submission_sample.csv --html outputs/report.html --debug
```

### 3. Run on the full 100K candidate pool

```bash
python rank.py --candidates candidates.jsonl --out outputs/submission.csv --html outputs/report.html --debug
```

> If you downloaded the gzipped version instead, point to that file directly —
> the loader auto-detects format from the extension:
> ```bash
> python rank.py --candidates candidates.jsonl.gz --out outputs/submission.csv --html outputs/report.html --debug
> ```

### 4. Validate the submission format

```bash
python validate_submission.py outputs/submission.csv
```
Expected output: `Submission is valid.`

### 5. Rename to your participant/team ID before uploading

```bash
copy outputs\submission.csv outputs\your_team_id.csv
```

### 6. Launch the sandbox UI locally (optional, for demo)

```bash
streamlit run app.py
```

---

## CLI Reference

```
python rank.py --candidates <path> --out <path> [--top-n N] [--html <path>] [--debug]
```

| Flag | Description |
|---|---|
| `--candidates` | Path to candidate data: `.json`, `.jsonl`, or `.jsonl.gz` |
| `--out` | Output CSV path |
| `--top-n` | Number of ranked candidates to output (default: 100) |
| `--html` | Optional path to write a styled HTML report alongside the CSV |
| `--debug` | Print per-component score breakdown for the top 10 in the terminal |

---

## Project Structure

```
redrob_ranker/
├── rank.py                      ← Main CLI — produces submission.csv
├── app.py                       ← Streamlit sandbox UI (for HuggingFace Spaces deployment)
├── validate_submission.py       ← Hackathon's official format validator
├── requirements.txt             ← Dependencies (streamlit, for the UI only)
├── submission_metadata.yaml     ← Team details, AI tools declaration, methodology
├── README.md                    ← This file
│
├── .streamlit/
│   └── config.toml              ← 800MB upload limit + dark theme for sandbox UI
│
├── src/
│   ├── engine.py                ← Core scoring logic — honeypot detection, 5-signal scorer
│   ├── pretty.py                ← Colored terminal output (progress bar, medals, score bars)
│   └── report.py                ← Standalone HTML report generator
│
├── data/
│   └── sample_candidates.json   ← 50-candidate sample for quick testing
│
├── candidates.jsonl             ← Full 100K dataset (NOT committed to GitHub — see .gitignore)
│
└── outputs/
    ├── submission.csv           ← Generated — final ranked submission
    └── report.html              ← Generated — visual ranking report
```

> **Note:** `candidates.jsonl` / `candidates.jsonl.gz` and the `outputs/` folder
> should be excluded from version control via `.gitignore` — they're either too
> large or auto-generated.

---

## Scoring Logic — Key Design Decisions

### Why career trajectory carries the most weight (32%)
The JD is explicit: *"The right answer is not to find candidates whose skills section contains the most AI keywords. That's a trap we've explicitly built into the dataset."*

A candidate with "RAG, Pinecone, Weaviate" in their skills list but a title of "Marketing Manager" gets a low career score (~0.28 base) regardless of skill match — this is the single most decisive signal against keyword-stuffer traps.

Conversely, a candidate **without** trendy AI keywords but with career history showing they *shipped a recommendation/search/ranking system at a product company* gets a +0.15 career bonus — directly rewarding the JD's stated "ideal candidate" profile even when their skills section looks unimpressive on paper.

### Why behavioral signals are a multiplier, not an additive score
The JD states: *"A perfect-on-paper candidate who hasn't logged in for 6 months and has a 5% recruiter response rate is, for hiring purposes, not actually available. Down-weight them appropriately."*

By making behavioral signals a **multiplier** (0.1×–1.5×) rather than a fifth additive component, a candidate inactive for 180+ days loses ~45% of their final score — pushing them far down the rankings even with a perfect skill/career match.

### Skill trust = proficiency × duration × endorsements × assessment
Skills aren't counted by name alone. A skill listed as "expert" with 0 months of use and 0 endorsements scores near-zero trust. The same skill at "advanced" proficiency with 36 months of use and strong endorsements scores close to maximum.

### Explicit JD disqualifier checks
Five hard-disqualifier patterns from the JD are detected and penalize the career score:
1. Pure research/academic career with no production deployment evidence
2. Recent (<12mo) LangChain/API-only "AI experience" with no pre-LLM ML background
3. Senior titles (architect/tech lead/manager) with no recent hands-on coding signal
4. Title-chasing career pattern (frequent <18-month stints with title escalation)
5. 5+ years closed-source-only work with no external validation (OSS/papers/talks)

### Location scoring matches the JD's exact city tiers
Pune/Noida (JD's stated preference) score highest, followed by Hyderabad/Mumbai/Delhi NCR (explicitly welcomed), then the rest of India, then willing-to-relocate candidates abroad.

### Honeypot detection
Profiles are flagged and excluded before scoring if they show:
1. Duration at a company exceeding that company's possible age
2. 3+ "expert"-proficiency skills with 0 months of usage
3. Claimed years of experience exceeding what their career start date allows
4. "Expert" self-rating contradicted by a platform assessment score under 20

---

## Submission Checklist

- [ ] `outputs/your_team_id.csv` generated and passes `validate_submission.py`
- [ ] Code pushed to GitHub (public, or private with organizer access granted)
- [ ] `app.py` deployed to HuggingFace Spaces / Streamlit Cloud for the sandbox link
- [ ] `submission_metadata.yaml` filled in with team name, contact, GitHub repo, sandbox link
- [ ] All declarations in `submission_metadata.yaml` reviewed and accurate

---

## AI Tools Declaration
- **Claude** — used for architecture discussion, code structure, and design review
- No candidate data was processed by any external LLM
- Zero LLM API calls occur during the ranking step (verified by the compute constraints: no network access during ranking)