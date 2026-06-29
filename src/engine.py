"""
engine.py — Core Candidate Scoring Engine
==========================================
Multi-signal ranking for Senior AI Engineer JD.
No GPU. No external APIs. Pure Python + stdlib.
"""

import math
import re
from datetime import date, datetime
from typing import Any

# ─── TODAY ────────────────────────────────────────────────────────────────────
TODAY = date.today()

# ─── JD DEFINITION ────────────────────────────────────────────────────────────
# Parsed from the actual job_description provided in the hackathon bundle.

REQUIRED_SKILLS = {
    # Embeddings & retrieval (core requirement)
    "embeddings", "sentence-transformers", "sentence transformer",
    "bge", "e5", "openai embeddings", "text embeddings",
    "semantic search", "dense retrieval", "retrieval",
    # Vector DBs (core requirement)
    "faiss", "pinecone", "qdrant", "weaviate", "milvus",
    "opensearch", "elasticsearch", "vector database", "hybrid search",
    "ann", "approximate nearest neighbor",
    # Ranking & eval (core requirement)
    "ranking", "ndcg", "mrr", "map", "learning to rank",
    "reranking", "re-ranking", "recommendation systems",
    "information retrieval", "search relevance",
    # Language
    "python", "nlp",
}

NICE_TO_HAVE_SKILLS = {
    "lora", "qlora", "peft", "fine-tuning", "fine-tune", "fine tuning",
    "fine-tuning llms", "rag", "retrieval augmented generation",
    "xgboost", "distributed systems", "inference optimization",
    "pytorch", "hugging face", "huggingface", "transformers",
    "mlflow", "kubeflow", "feature engineering",
}

NEGATIVE_SKILLS = {
    # Computer vision / speech / robotics as primary domain
    "computer vision", "opencv", "image classification", "object detection",
    "yolo", "cnn", "speech recognition", "tts", "gans", "robotics",
}

CONSULTING_FIRMS = {
    "tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini",
    "hcl", "tech mahindra", "mindtree", "mphasis", "hexaware",
    "ltimindtree", "l&t infotech",
}

TARGET_TITLES = {
    "ai engineer", "ml engineer", "machine learning engineer",
    "nlp engineer", "search engineer", "recommendation systems engineer",
    "applied scientist", "research engineer", "data scientist",
    "software engineer", "backend engineer", "full stack developer",
    "senior engineer", "staff engineer",
}

INDIA_LOCATIONS = {
    "pune", "noida", "hyderabad", "mumbai", "delhi", "bangalore",
    "bengaluru", "chennai", "kolkata", "ahmedabad", "kochi",
    "trivandrum", "gurgaon", "gurugram", "vizag", "indore",
    "bhubaneswar", "chandigarh", "india",
}

SKILL_ALIASES: dict[str, str] = {
    "sentence transformer":          "sentence-transformers",
    "sentence transformers":         "sentence-transformers",
    "fine tuning":                   "fine-tuning",
    "fine-tuning llms":              "fine-tuning",
    "retrieval augmented generation":"retrieval",
    "rag":                           "retrieval",
    "vector search":                 "vector database",
    "vector store":                  "vector database",
    "dense retrieval":               "retrieval",
    "hybrid retrieval":              "hybrid search",
    "reranking":                     "ranking",
    "re-ranking":                    "ranking",
    "recommendation systems":        "ranking",
    "search relevance":              "ranking",
    "hugging face":                  "huggingface",
    "hugging face transformers":     "huggingface",
    "hugging face hub":              "huggingface",
    "bm25":                          "retrieval",
    "text embeddings":               "embeddings",
    "word embeddings":               "embeddings",
}


def _norm(s: str) -> str:
    return SKILL_ALIASES.get(s.lower().strip(), s.lower().strip())


# ─── HONEYPOT DETECTOR ────────────────────────────────────────────────────────

def is_honeypot(c: dict) -> bool:
    """
    Return True if the candidate profile contains impossible/fabricated data.
    Honeypots are tier-0 in the ground truth and must not appear in top 100.

    Patterns we detect:
      1. Claimed duration at a company exceeds the company's possible age
      2. 3+ "expert" skills with 0 months of use
      3. YoE far exceeds career start date arithmetic
      4. Expert self-rating + assessment score < 20 (contradiction)
    """
    profile = c.get("profile", {})
    career  = c.get("career_history", [])
    skills  = c.get("skills", [])
    sigs    = c.get("redrob_signals", {})
    assess  = sigs.get("skill_assessment_scores", {})
    yoe     = profile.get("years_of_experience", 0)

    # 1. Duration vs company age
    for job in career:
        start = job.get("start_date", "2020-01-01")
        dur   = job.get("duration_months", 0)
        try:
            sy    = int(start[:4])
            sm    = int(start[5:7])
            max_dur = (TODAY.year - sy) * 12 + (TODAY.month - sm) + 2
            if dur > max_dur + 6:         # 6-month tolerance
                return True
        except Exception:
            pass

    # 2. Expert + 0 months
    expert_zero = sum(
        1 for sk in skills
        if sk.get("proficiency") == "expert" and sk.get("duration_months", 1) == 0
    )
    if expert_zero >= 3:
        return True

    # 3. YoE vs earliest career start
    if career:
        starts = [j.get("start_date", "2030-01") for j in career]
        earliest = min(starts)
        try:
            ey = int(earliest[:4])
            max_yoe = (TODAY.year - ey) + 1
            if yoe > max_yoe + 3:
                return True
        except Exception:
            pass

    # 4. Expert claim contradicted by low assessment
    for sk in skills:
        name = sk.get("name", "")
        if sk.get("proficiency") == "expert" and name in assess:
            if assess[name] < 20:
                return True

    return False


# ─── INDIVIDUAL SCORING FUNCTIONS ─────────────────────────────────────────────

def _score_skills(c: dict) -> tuple[float, list[str]]:
    """
    Skill match score (0–1).
    Weights: required > nice-to-have; penalizes negative domain skills.
    Trust modifiers: proficiency × endorsement (log) × duration × assessment bonus.
    """
    skills  = c.get("skills", [])
    assess  = c.get("redrob_signals", {}).get("skill_assessment_scores", {})
    matched = []
    total   = 0.0

    prof_w = {"beginner": 0.25, "intermediate": 0.55, "advanced": 0.80, "expert": 1.00}

    for sk in skills:
        raw   = sk.get("name", "")
        norm  = _norm(raw)
        prof  = prof_w.get(sk.get("proficiency", "beginner"), 0.25)
        dur   = sk.get("duration_months", 0)
        end_  = sk.get("endorsements", 0)

        # Trust multiplier: caps at 1.0
        dur_t  = min(dur / 36.0, 1.0) if dur > 0 else 0.05
        end_t  = min(math.log1p(end_) / math.log1p(60), 1.0)
        assess_bonus = (assess.get(raw, 0) / 100.0) * 0.15  # up to +0.15

        val = prof * (0.55 + 0.25 * dur_t + 0.20 * end_t) + assess_bonus

        if norm in REQUIRED_SKILLS or any(r in norm for r in REQUIRED_SKILLS):
            matched.append(raw)
            total += val * 2.5          # required skills — highest weight
        elif norm in NICE_TO_HAVE_SKILLS or any(n in norm for n in NICE_TO_HAVE_SKILLS):
            matched.append(f"(+){raw}")
            total += val * 0.6
        elif norm in NEGATIVE_SKILLS or any(neg in norm for neg in NEGATIVE_SKILLS):
            total -= 0.08               # small penalty for wrong domain

    max_possible = len(REQUIRED_SKILLS) * 2.5 + len(NICE_TO_HAVE_SKILLS) * 0.6
    score = min(max(total / max_possible, 0.0), 1.0)

    # Hard penalty: zero required skills → very low score regardless
    req_matched = [m for m in matched if not m.startswith("(+)")]
    if not req_matched:
        score *= 0.2

    return round(score, 4), matched


def _score_career(c: dict) -> tuple[float, str]:
    """
    Career trajectory score (0–1).
    Rewards: relevant AI/ML titles, product company experience.
    Penalises: pure consulting careers, completely irrelevant titles.
    """
    career  = c.get("career_history", [])
    profile = c.get("profile", {})
    title   = profile.get("current_title", "").lower()

    if not career:
        return 0.10, "no career history available"

    # Title relevance
    title_hit  = any(t in title for t in TARGET_TITLES)
    title_note = f"'{profile.get('current_title')}' is {'relevant' if title_hit else 'not a core AI/ML role'}"
    score = 0.55 if title_hit else 0.30

    # Career history analysis
    all_consulting    = True
    ai_roles          = 0
    product_months    = 0
    total_months      = sum(j.get("duration_months", 0) for j in career)

    for job in career:
        co   = job.get("company", "").lower()
        desc = job.get("description", "").lower()
        ind  = job.get("industry", "").lower()
        dur  = job.get("duration_months", 0)

        consulting = any(f in co for f in CONSULTING_FIRMS)
        if not consulting:
            all_consulting = False
            product_months += dur

        ai_kw = ["embedding", "retrieval", "ranking", "recommendation",
                 "nlp", "machine learning", "search", "vector", "llm", "ai "]
        if any(kw in desc for kw in ai_kw):
            ai_roles += 1
            score += 0.07

    if all_consulting:
        score -= 0.30
        career_note = "entire career at consulting firms (disqualifier)"
    else:
        frac = product_months / max(total_months, 1)
        score += 0.15 * frac
        career_note = f"{int(frac*100)}% product company experience"

    if ai_roles >= 2:
        career_note += f"; {ai_roles} AI/ML-relevant roles"

    return round(min(max(score, 0.0), 1.0), 4), f"{title_note}; {career_note}"


def _score_experience(c: dict) -> tuple[float, str]:
    """Experience years fit against JD range (5–9 preferred)."""
    yoe = c.get("profile", {}).get("years_of_experience", 0)
    lo, hi = 5, 9

    if lo <= yoe <= hi:
        return 1.0, f"{yoe:.1f} yrs — within preferred {lo}–{hi} range"
    elif yoe < lo:
        s = max(0.0, yoe / lo) * 0.75
        return round(s, 4), f"{yoe:.1f} yrs — below minimum of {lo}"
    else:
        s = max(0.50, 1.0 - (yoe - hi) * 0.03)
        return round(s, 4), f"{yoe:.1f} yrs — above preferred max of {hi}"


def _score_location(c: dict) -> tuple[float, str]:
    """Location fit: India target cities > willing-to-relocate > abroad."""
    p    = c.get("profile", {})
    sig  = c.get("redrob_signals", {})
    loc  = p.get("location", "").lower()
    ctry = p.get("country",   "").lower()
    rel  = sig.get("willing_to_relocate", False)

    if any(tl in loc for tl in INDIA_LOCATIONS) or "india" in ctry:
        return 1.0, f"based in {p.get('location')} — target region"
    elif rel:
        return 0.65, f"in {p.get('location')} but willing to relocate"
    else:
        return 0.20, f"in {p.get('location')}, not open to relocation"


def _score_education(c: dict) -> tuple[float, str]:
    """Institution tier + CS-field relevance."""
    edu = c.get("education", [])
    if not edu:
        return 0.40, "no education listed"

    best    = edu[0]
    tier    = best.get("tier", "unknown")
    field   = best.get("field_of_study", "").lower()
    degree  = best.get("degree", "")
    inst    = best.get("institution", "")
    tier_s  = {"tier_1": 1.0, "tier_2": 0.80, "tier_3": 0.60,
               "tier_4": 0.40, "unknown": 0.50}
    base    = tier_s.get(tier, 0.50)

    cs_fields = ["computer science", "information technology", "ai",
                 "machine learning", "data science", "electronics",
                 "engineering", "mathematics", "statistics"]
    if any(f in field for f in cs_fields):
        base = min(base + 0.10, 1.0)

    return round(base, 4), f"{degree} in {best.get('field_of_study')} from {inst} ({tier})"


def _score_behavioral(c: dict) -> tuple[float, list[str]]:
    """
    Behavioral signal multiplier (0.1 – 1.5).
    Used to multiply the base score — bad signals can halve a great profile.
    """
    s     = c.get("redrob_signals", {})
    mult  = 1.0
    notes: list[str] = []

    # Recency — biggest factor
    last_active = s.get("last_active_date", "2020-01-01")
    try:
        last_dt      = datetime.strptime(last_active, "%Y-%m-%d").date()
        days_ago     = (TODAY - last_dt).days
        if days_ago > 180:
            mult -= 0.40
            notes.append(f"inactive {days_ago}d ⚠")
        elif days_ago > 90:
            mult -= 0.20
            notes.append(f"inactive {days_ago}d")
        elif days_ago < 14:
            mult += 0.08
            notes.append("active this week")
        elif days_ago < 30:
            mult += 0.04
    except Exception:
        pass

    # Open to work
    if s.get("open_to_work_flag"):
        mult += 0.05
        notes.append("open to work")

    # Recruiter responsiveness
    rrr = s.get("recruiter_response_rate", 0.5)
    if rrr < 0.15:
        mult -= 0.20
        notes.append(f"response rate {rrr:.0%} ⚠")
    elif rrr > 0.75:
        mult += 0.05
        notes.append(f"response rate {rrr:.0%} ✓")

    # Notice period
    notice = s.get("notice_period_days", 30)
    if notice <= 15:
        mult += 0.06
        notes.append(f"notice {notice}d ✓")
    elif notice > 90:
        mult -= 0.08
        notes.append(f"notice {notice}d")

    # GitHub activity
    gh = s.get("github_activity_score", -1)
    if gh >= 70:
        mult += 0.10
        notes.append(f"GitHub {gh:.0f}/100 ✓")
    elif gh >= 40:
        mult += 0.04
        notes.append(f"GitHub {gh:.0f}/100")
    elif gh == -1:
        pass   # neutral — no GitHub linked

    # Interview reliability
    icr = s.get("interview_completion_rate", 0.5)
    if icr < 0.50:
        mult -= 0.10
        notes.append(f"interview completion {icr:.0%} ⚠")
    elif icr > 0.90:
        mult += 0.03

    # Work mode fit (JD: hybrid/onsite/flexible preferred)
    preferred = s.get("preferred_work_mode", "flexible")
    if preferred in {"hybrid", "onsite", "flexible"}:
        mult += 0.02
    elif preferred == "remote":
        mult -= 0.04

    # Profile completeness
    comp = s.get("profile_completeness_score", 50)
    if comp > 85:
        mult += 0.03
    elif comp < 50:
        mult -= 0.04

    # Verification
    if s.get("verified_email") and s.get("verified_phone"):
        mult += 0.02

    return round(min(max(mult, 0.10), 1.50), 4), notes


# ─── WEIGHTS ──────────────────────────────────────────────────────────────────
W = {
    "skills":     0.35,
    "career":     0.25,
    "experience": 0.15,
    "location":   0.10,
    "education":  0.05,
    # remaining 0.10 is captured via behavioral multiplier
}


# ─── MAIN SCORER ──────────────────────────────────────────────────────────────

def score_candidate(c: dict) -> dict[str, Any]:
    """
    Score one candidate and return a full result dict including:
      - score (final 0–1)
      - reasoning (1–2 sentences for submission CSV)
      - breakdown (per-component, for debugging / UI display)
      - is_honeypot flag
    """
    cid = c.get("candidate_id", "UNKNOWN")

    # Honeypot check first — exclude immediately
    if is_honeypot(c):
        return {
            "candidate_id": cid,
            "score":        0.0,
            "is_honeypot":  True,
            "reasoning":    "Profile contains impossible data patterns (honeypot).",
            "breakdown":    {},
            "matched_skills": [],
        }

    sk_score, sk_matched  = _score_skills(c)
    ca_score, ca_note     = _score_career(c)
    ex_score, ex_note     = _score_experience(c)
    lo_score, lo_note     = _score_location(c)
    ed_score, ed_note     = _score_education(c)
    be_mult,  be_notes    = _score_behavioral(c)

    base  = (
        W["skills"]     * sk_score +
        W["career"]     * ca_score +
        W["experience"] * ex_score +
        W["location"]   * lo_score +
        W["education"]  * ed_score
    )
    final = round(min(max(base * be_mult, 0.0), 1.0), 6)

    # ── Build reasoning string ──────────────────────────────────────────────
    profile = c.get("profile", {})
    yoe     = profile.get("years_of_experience", 0)
    title   = profile.get("current_title", "N/A")
    loc     = profile.get("location", "N/A")

    req_skills  = [m for m in sk_matched if not m.startswith("(+)")][:3]
    nice_skills = [m[3:] for m in sk_matched if m.startswith("(+)")][:2]

    if req_skills:
        skill_part = f"matched required: {', '.join(req_skills)}"
        if nice_skills:
            skill_part += f"; also: {', '.join(nice_skills)}"
    else:
        skill_part = "no required skills matched"

    # Behavioral summary — pick most important signal
    be_summary = be_notes[0] if be_notes else "normal engagement"

    reasoning = (
        f"{yoe:.0f}yr {title} ({loc}); {skill_part}; "
        f"{ca_note.split(';')[0].strip()}; {be_summary}."
    )[:280]

    return {
        "candidate_id":   cid,
        "score":          final,
        "is_honeypot":    False,
        "reasoning":      reasoning,
        "matched_skills": sk_matched,
        "breakdown": {
            "skills":                round(sk_score, 4),
            "career":                round(ca_score, 4),
            "experience":            round(ex_score, 4),
            "location":              round(lo_score, 4),
            "education":             round(ed_score, 4),
            "behavioral_multiplier": be_mult,
            "base_score":            round(base, 4),
            "final_score":           final,
            "career_note":           ca_note,
            "experience_note":       ex_note,
            "location_note":         lo_note,
            "education_note":        ed_note,
            "behavioral_signals":    be_notes,
        },
    }