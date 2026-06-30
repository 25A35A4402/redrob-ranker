"""
pretty.py — Beautiful terminal output using ANSI codes (stdlib only).
Works on Windows 10+, Mac, Linux terminals.
"""

import os
import sys

# Enable ANSI colors on Windows terminals
if os.name == "nt":
    os.system("")

RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

RED     = "\033[91m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"
CYAN    = "\033[96m"
WHITE   = "\033[97m"

BG_PURPLE = "\033[45m"


def banner():
    art = f"""
{CYAN}{BOLD}╔══════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🎯  REDROB INTELLIGENT CANDIDATE RANKING ENGINE                  ║
║       IndiaRuns HackSkill2 · Track 1                               ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════╝{RESET}
"""
    print(art)


def section(title: str):
    width = 70
    print(f"\n{MAGENTA}{BOLD}┌{'─' * (width-2)}┐{RESET}")
    pad = width - 4 - len(title)
    print(f"{MAGENTA}{BOLD}│ {CYAN}{title}{' ' * pad} {MAGENTA}│{RESET}")
    print(f"{MAGENTA}{BOLD}└{'─' * (width-2)}┘{RESET}")


def success(msg: str):
    print(f"  {GREEN}✓{RESET}  {msg}")


def warn(msg: str):
    print(f"  {YELLOW}⚠{RESET}  {YELLOW}{msg}{RESET}")


def info(msg: str):
    print(f"  {BLUE}ℹ{RESET}  {DIM}{msg}{RESET}")


def progress_bar(current: int, total: int, width: int = 40):
    frac = current / total
    filled = int(width * frac)
    bar = "█" * filled + "░" * (width - filled)
    pct = frac * 100
    sys.stdout.write(
        f"\r  {CYAN}[{bar}]{RESET} {pct:5.1f}%  "
        f"({current:,}/{total:,})"
    )
    sys.stdout.flush()


def score_bar(score: float, width: int = 20) -> str:
    filled = int(width * min(max(score, 0), 1))
    bar = "█" * filled + "░" * (width - filled)
    if score >= 0.6:
        color = GREEN
    elif score >= 0.4:
        color = YELLOW
    else:
        color = RED
    return f"{color}{bar}{RESET}"


def rank_medal(rank: int) -> str:
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    return medals.get(rank, f"#{rank:>2}")


def candidate_card(rank: int, item: dict, orig: dict, debug: bool = False):
    p = orig.get("profile", {})
    name = p.get("anonymized_name", item["candidate_id"])
    title = p.get("current_title", "—")
    loc = p.get("location", "—")
    yoe = p.get("years_of_experience", "—")
    score = item["score"]

    medal = rank_medal(rank)
    bar = score_bar(score)

    print(f"\n  {BOLD}{medal}  {WHITE}{name}{RESET}  {DIM}({item['candidate_id']}){RESET}")
    print(f"      {title}  ·  {loc}  ·  {yoe} yrs")
    print(f"      {bar}  {BOLD}{score:.4f}{RESET}")
    print(f"      {DIM}{item['reasoning'][:100]}{RESET}")

    if debug and item.get("breakdown"):
        bd = item["breakdown"]
        print(f"      {CYAN}skills{RESET}={bd['skills']:.2f} "
              f"{CYAN}career{RESET}={bd['career']:.2f} "
              f"{CYAN}exp{RESET}={bd['experience']:.2f} "
              f"{CYAN}loc{RESET}={bd['location']:.2f} "
              f"{CYAN}edu{RESET}={bd['education']:.2f} "
              f"{CYAN}×behav{RESET}={bd['behavioral_multiplier']:.2f}")


def summary_table(rows: dict):
    key_width = max(len(k) for k in rows) + 2
    for k, v in rows.items():
        print(f"  {DIM}{k:<{key_width}}{RESET} {BOLD}{v}{RESET}")