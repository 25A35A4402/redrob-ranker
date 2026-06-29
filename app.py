"""
Redrob Ranker — Streamlit Sandbox Demo
Hosted demo for HuggingFace Spaces / Streamlit Cloud.

Run locally:  streamlit run app.py
"""

import json
import csv
import io
import streamlit as st
import sys
from pathlib import Path

# Import the ranker
sys.path.insert(0, str(Path(__file__).parent))
from rank import score_candidate, load_candidates

st.set_page_config(
    page_title="Redrob Intelligent Candidate Ranker",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 Redrob Intelligent Candidate Discovery & Ranking Engine")
st.caption("IndiaRuns HackSkill2 — Track 1 Submission")

st.markdown("""
This system ranks candidates for the **Senior AI Engineer** role using a multi-signal scoring engine:
- **Skill matching** (35%) — semantic skill relevance with proficiency & endorsement trust
- **Career trajectory** (25%) — product companies, title relevance, no pure-consulting
- **Experience years** (15%) — calibrated against JD's 5-9 year preference  
- **Location fit** (10%) — India & target cities prioritized
- **Education** (5%) — institution tier + CS field bonus
- **Behavioral signals** (multiplier) — recency, response rate, GitHub, notice period
""")

st.divider()

# Upload
st.subheader("Upload Candidate Data")
uploaded = st.file_uploader(
    "Upload candidates JSON or JSONL file (sample of ≤500 candidates)",
    type=["json", "jsonl"],
)

top_n = st.slider("Number of top candidates to show", min_value=5, max_value=100, value=20)

if uploaded:
    try:
        content = uploaded.read().decode("utf-8")
        # Try JSON array first
        try:
            candidates = json.loads(content)
            if not isinstance(candidates, list):
                candidates = [candidates]
        except json.JSONDecodeError:
            # Try JSONL
            candidates = [json.loads(line) for line in content.splitlines() if line.strip()]

        st.success(f"Loaded **{len(candidates)}** candidates")

        with st.spinner("Scoring candidates..."):
            scored = [score_candidate(c) for c in candidates]
            non_hp = [s for s in scored if not s["is_honeypot"]]
            non_hp.sort(key=lambda x: (-x["score"], x["candidate_id"]))
            top = non_hp[:top_n]

        honeypots = sum(1 for s in scored if s["is_honeypot"])
        if honeypots:
            st.warning(f"⚠️ {honeypots} honeypot candidate(s) detected and excluded from ranking.")

        st.subheader(f"Top {len(top)} Candidates")

        # Display table
        import pandas as pd
        rows = []
        for i, item in enumerate(top, 1):
            cid = item["candidate_id"]
            # Find original candidate data
            orig = next((c for c in candidates if c["candidate_id"] == cid), {})
            profile = orig.get("profile", {})
            rows.append({
                "Rank": i,
                "Candidate ID": cid,
                "Score": f"{item['score']:.4f}",
                "Name": profile.get("anonymized_name", "—"),
                "Title": profile.get("current_title", "—"),
                "YoE": profile.get("years_of_experience", "—"),
                "Location": profile.get("location", "—"),
                "Reasoning": item["reasoning"],
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Score breakdown for top candidate
        st.subheader("Score Breakdown — Top Candidate")
        if top:
            breakdown = top[0].get("_breakdown", {})
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Skills Score", f"{breakdown.get('skills', 0):.3f}")
                st.metric("Career Score", f"{breakdown.get('career', 0):.3f}")
            with col2:
                st.metric("Experience Score", f"{breakdown.get('experience', 0):.3f}")
                st.metric("Location Score", f"{breakdown.get('location', 0):.3f}")
            with col3:
                st.metric("Education Score", f"{breakdown.get('education', 0):.3f}")
                st.metric("Behavioral Multiplier", f"{breakdown.get('behavioral_multiplier', 1):.3f}")

        # Download CSV
        st.subheader("Download Submission CSV")
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank, item in enumerate(top, 1):
            writer.writerow([item["candidate_id"], rank, item["score"], item["reasoning"]])

        st.download_button(
            "⬇️ Download submission.csv",
            data=buf.getvalue(),
            file_name="submission.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"Error processing file: {e}")
        st.exception(e)
else:
    st.info("👆 Upload a candidates JSON or JSONL file to start ranking.")

st.divider()
st.caption("Built for IndiaRuns HackSkill2 | Team submission | AI tools declared: Claude (architecture & review)")