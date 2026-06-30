"""
report.py — Generates a polished, standalone HTML report of the ranking results.
No external dependencies — single self-contained HTML file with inline CSS/JS.
"""

import json
from datetime import datetime
from pathlib import Path


def _esc(s) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate_html_report(top: list[dict], all_candidates: list[dict], out_path: str,
                          honeypots: int, total: int) -> None:
    cand_map = {c["candidate_id"]: c for c in all_candidates}
    now = datetime.now().strftime("%d %b %Y, %H:%M")

    rows_html = []
    for i, item in enumerate(top, 1):
        cid = item["candidate_id"]
        orig = cand_map.get(cid, {})
        p = orig.get("profile", {})
        sig = orig.get("redrob_signals", {})
        bd = item.get("breakdown", {})

        name = _esc(p.get("anonymized_name", cid))
        title = _esc(p.get("current_title", "—"))
        loc = _esc(p.get("location", "—"))
        company = _esc(p.get("current_company", "—"))
        yoe = p.get("years_of_experience", "—")
        score = item["score"]
        reasoning = _esc(item["reasoning"])
        skills = _esc(", ".join(item.get("matched_skills", [])[:6]) or "none matched")

        medal = ""
        if i == 1: medal = '<span class="medal gold">1</span>'
        elif i == 2: medal = '<span class="medal silver">2</span>'
        elif i == 3: medal = '<span class="medal bronze">3</span>'
        else: medal = f'<span class="medal">{i}</span>'

        skill_score = bd.get("skills", 0)
        career_score = bd.get("career", 0)
        exp_score = bd.get("experience", 0)
        loc_score = bd.get("location", 0)
        edu_score = bd.get("education", 0)
        behav_mult = bd.get("behavioral_multiplier", 1.0)

        open_to_work = "🟢 Open" if sig.get("open_to_work_flag") else "⚪ Not flagged"
        github = sig.get("github_activity_score", -1)
        github_str = f"{github:.0f}/100" if github >= 0 else "—"
        last_active = sig.get("last_active_date", "—")
        notice = sig.get("notice_period_days", "—")

        rows_html.append(f"""
        <div class="card" style="--score: {score}">
          <div class="card-rank">{medal}</div>
          <div class="card-main">
            <div class="card-head">
              <div class="card-name">{name}</div>
              <div class="card-score">{score:.4f}</div>
            </div>
            <div class="card-sub">{title} · {company} · {loc} · {yoe} yrs</div>
            <div class="card-reasoning">{reasoning}</div>
            <div class="card-skills"><span class="label">Matched skills</span> {skills}</div>

            <div class="signal-bars">
              <div class="bar-row"><span>Skills</span><div class="bar-track"><div class="bar-fill skills" style="width:{skill_score*100:.0f}%"></div></div><span class="bar-val">{skill_score:.2f}</span></div>
              <div class="bar-row"><span>Career</span><div class="bar-track"><div class="bar-fill career" style="width:{career_score*100:.0f}%"></div></div><span class="bar-val">{career_score:.2f}</span></div>
              <div class="bar-row"><span>Exp</span><div class="bar-track"><div class="bar-fill exp" style="width:{exp_score*100:.0f}%"></div></div><span class="bar-val">{exp_score:.2f}</span></div>
              <div class="bar-row"><span>Location</span><div class="bar-track"><div class="bar-fill loc" style="width:{loc_score*100:.0f}%"></div></div><span class="bar-val">{loc_score:.2f}</span></div>
              <div class="bar-row"><span>Education</span><div class="bar-track"><div class="bar-fill edu" style="width:{edu_score*100:.0f}%"></div></div><span class="bar-val">{edu_score:.2f}</span></div>
            </div>

            <div class="meta-chips">
              <span class="chip">{open_to_work}</span>
              <span class="chip">GitHub {github_str}</span>
              <span class="chip">Active {last_active}</span>
              <span class="chip">Notice {notice}d</span>
              <span class="chip mult">×{behav_mult:.2f} behavioral</span>
            </div>
          </div>
        </div>
        """)

    avg_score = sum(t["score"] for t in top) / max(len(top), 1)
    top_score = top[0]["score"] if top else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Redrob Candidate Ranking Report</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

  :root {{
    --bg:        #0B0E14;
    --bg-panel:  #11151F;
    --bg-card:   #161B26;
    --border:    #232A38;
    --signal:    #00FF9C;
    --signal-dim:#00C97D;
    --amber:     #FFB800;
    --red:       #FF5C5C;
    --text:      #E8ECF2;
    --text-dim:  #8A93A6;
    --text-mute: #565F73;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: var(--bg);
    background-image:
      radial-gradient(circle at 10% 0%, rgba(0,255,156,0.06), transparent 40%),
      radial-gradient(circle at 90% 10%, rgba(0,255,156,0.04), transparent 35%);
    color: var(--text);
    font-family: 'Inter', sans-serif;
    line-height: 1.5;
    min-height: 100vh;
  }}

  .mono {{ font-family: 'JetBrains Mono', monospace; }}

  /* ── HEADER ───────────────────────────────────────── */
  header {{
    padding: 48px 32px 32px;
    max-width: 1100px;
    margin: 0 auto;
    border-bottom: 1px solid var(--border);
  }}

  .eyebrow {{
    font-family: 'JetBrains Mono', monospace;
    color: var(--signal);
    font-size: 12px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .eyebrow::before {{
    content: '';
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--signal);
    box-shadow: 0 0 8px var(--signal);
    animation: pulse 2s ease-in-out infinite;
  }}
  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.3; }}
  }}

  h1 {{
    font-family: 'JetBrains Mono', monospace;
    font-size: clamp(28px, 4vw, 42px);
    font-weight: 800;
    letter-spacing: -0.02em;
    margin-bottom: 8px;
  }}
  h1 .accent {{ color: var(--signal); }}

  .subtitle {{
    color: var(--text-dim);
    font-size: 15px;
    max-width: 600px;
  }}

  .stat-row {{
    display: flex;
    gap: 24px;
    margin-top: 32px;
    flex-wrap: wrap;
  }}
  .stat {{
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 20px;
    min-width: 140px;
  }}
  .stat-label {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-mute);
    margin-bottom: 6px;
  }}
  .stat-value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 26px;
    font-weight: 700;
    color: var(--text);
  }}
  .stat-value.signal {{ color: var(--signal); }}
  .stat-value.amber {{ color: var(--amber); }}

  /* ── MAIN ─────────────────────────────────────────── */
  main {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 40px 32px 80px;
  }}

  .section-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--text-mute);
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .section-label::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
  }}

  .card {{
    display: flex;
    gap: 20px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 3px solid color-mix(in srgb, var(--signal) calc(var(--score) * 100%), var(--border));
    border-radius: 12px;
    padding: 22px 24px;
    margin-bottom: 14px;
    transition: transform 0.15s ease, border-color 0.15s ease;
  }}
  .card:hover {{
    transform: translateX(4px);
    border-color: var(--signal-dim);
  }}

  .card-rank {{ flex-shrink: 0; padding-top: 2px; }}
  .medal {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 800;
    font-size: 14px;
    width: 32px; height: 32px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    background: var(--bg-panel);
    color: var(--text-dim);
    border: 1px solid var(--border);
  }}
  .medal.gold   {{ background: linear-gradient(135deg, #FFD86B, #FFB800); color: #1a1200; border: none; }}
  .medal.silver {{ background: linear-gradient(135deg, #E8ECF2, #B4BCCB); color: #1a1200; border: none; }}
  .medal.bronze {{ background: linear-gradient(135deg, #D89A6A, #B5703A); color: #1a1200; border: none; }}

  .card-main {{ flex: 1; min-width: 0; }}

  .card-head {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 4px;
  }}
  .card-name {{ font-size: 16px; font-weight: 600; }}
  .card-score {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 18px;
    color: var(--signal);
    flex-shrink: 0;
  }}

  .card-sub {{ color: var(--text-dim); font-size: 13px; margin-bottom: 10px; }}
  .card-reasoning {{ font-size: 13.5px; color: var(--text); margin-bottom: 8px; line-height: 1.5; }}
  .card-skills {{ font-size: 12.5px; color: var(--text-dim); margin-bottom: 14px; }}
  .card-skills .label {{ color: var(--text-mute); margin-right: 6px; }}

  .signal-bars {{ display: flex; flex-direction: column; gap: 5px; margin-bottom: 14px; }}
  .bar-row {{ display: flex; align-items: center; gap: 10px; font-size: 11px; color: var(--text-mute); }}
  .bar-row span:first-child {{ width: 56px; flex-shrink: 0; }}
  .bar-track {{ flex: 1; height: 6px; background: var(--bg-panel); border-radius: 3px; overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 3px; }}
  .bar-fill.skills {{ background: var(--signal); }}
  .bar-fill.career {{ background: #6C9EFF; }}
  .bar-fill.exp    {{ background: #C78CFF; }}
  .bar-fill.loc    {{ background: var(--amber); }}
  .bar-fill.edu    {{ background: #FF8AAE; }}
  .bar-val {{ width: 32px; text-align: right; font-family: 'JetBrains Mono', monospace; }}

  .meta-chips {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  .chip {{
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    color: var(--text-dim);
    padding: 4px 10px;
    border-radius: 999px;
  }}
  .chip.mult {{ color: var(--signal); border-color: rgba(0,255,156,0.3); }}

  footer {{
    text-align: center;
    padding: 32px;
    color: var(--text-mute);
    font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
    border-top: 1px solid var(--border);
  }}

  @media (max-width: 640px) {{
    .card {{ flex-direction: column; }}
    .card-head {{ flex-direction: column; gap: 2px; }}
  }}
</style>
</head>
<body>

<header>
  <div class="eyebrow">Live Ranking Report</div>
  <h1>Redrob <span class="accent">Candidate Ranking</span></h1>
  <p class="subtitle">IndiaRuns HackSkill2 · Track 1 · Intelligent Candidate Discovery & Ranking Engine — Senior AI Engineer role</p>

  <div class="stat-row">
    <div class="stat">
      <div class="stat-label">Pool Scanned</div>
      <div class="stat-value">{total:,}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Honeypots Caught</div>
      <div class="stat-value amber">{honeypots}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Ranked Output</div>
      <div class="stat-value signal">{len(top)}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Top Score</div>
      <div class="stat-value signal">{top_score:.3f}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Avg Score (Top {len(top)})</div>
      <div class="stat-value">{avg_score:.3f}</div>
    </div>
  </div>
</header>

<main>
  <div class="section-label">Ranked Candidates</div>
  {''.join(rows_html)}
</main>

<footer>
  Generated {now} · Redrob Intelligent Candidate Ranking Engine · CPU-only · No external API calls
</footer>

</body>
</html>"""

    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")