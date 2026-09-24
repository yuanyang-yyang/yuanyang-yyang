#!/usr/bin/env python3
"""Render an activity heatmap card as static SVG from the GitHub GraphQL API."""
import json
import os
import sys
import urllib.request

TOKEN = os.environ["METRICS_TOKEN"]
LOGIN = os.environ.get("GH_LOGIN", "yuanyang-yyang")

QUERY = """
query {
  viewer {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date weekday contributionCount }
        }
      }
    }
  }
}
"""

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
COLORS = ["#ebedf0", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]  # validated ordinal ramp (0, 1-3, 4-9, 10-18, 19+)
INK = "#0b0b0b"
MUTED = "#6b6b66"
ACCENT = "#1c5cab"
SURFACE = "#ffffff"
BORDER = "#e5e3df"
SANS = "-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif"


def bucket(n):
    if n == 0:
        return 0
    if n <= 3:
        return 1
    if n <= 9:
        return 2
    if n <= 18:
        return 3
    return 4


def fetch_calendar():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY}).encode(),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": LOGIN,
        },
    )
    with urllib.request.urlopen(req) as r:
        payload = json.load(r)
    return payload["data"]["viewer"]["contributionsCollection"]["contributionCalendar"]


def current_streak(days):
    streak = 0
    for d in reversed(days):
        if d["contributionCount"] > 0:
            streak += 1
        else:
            break
    return streak


def render(weeks, total, streak, start_date, end_date):
    cell, gap = 10, 2
    step = cell + gap
    grid_w = len(weeks) * step - gap
    pad = 20
    left_pad = 30
    width = pad * 2 + left_pad + grid_w
    grid_top = pad + 48
    grid_h = 7 * step
    stats_h = 56
    height = grid_top + grid_h + 20 + stats_h + pad

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{SANS}">',
        f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" '
        f'fill="none" stroke="{BORDER}"/>',
        f'<text x="{pad}" y="{pad + 14}" font-size="15" font-weight="600" fill="{INK}">Activity</text>',
        f'<text x="{pad}" y="{pad + 32}" font-size="11" fill="{MUTED}">{start_date} → {end_date}</text>',
    ]

    grid_left = pad + left_pad

    prev_month = None
    for wi, w in enumerate(weeks):
        m_idx = int(w["contributionDays"][0]["date"].split("-")[1]) - 1
        if m_idx != prev_month:
            x = grid_left + wi * step
            parts.append(f'<text x="{x}" y="{grid_top - 6}" font-size="9" fill="{MUTED}">{MONTHS[m_idx]}</text>')
            prev_month = m_idx

    for wd, label in {1: "Mon", 3: "Wed", 5: "Fri"}.items():
        y = grid_top + wd * step + cell - 1
        parts.append(f'<text x="{pad}" y="{y}" font-size="9" fill="{MUTED}">{label}</text>')

    for wi, w in enumerate(weeks):
        for d in w["contributionDays"]:
            x = grid_left + wi * step
            y = grid_top + d["weekday"] * step
            c = COLORS[bucket(d["contributionCount"])]
            parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{c}"/>')

    legend_y = grid_top + grid_h + 14
    parts.append(f'<text x="{grid_left}" y="{legend_y + 8}" font-size="9" fill="{MUTED}">Less</text>')
    lx = grid_left + 30
    for c in COLORS:
        parts.append(f'<rect x="{lx}" y="{legend_y}" width="10" height="10" rx="2" fill="{c}"/>')
        lx += 14
    parts.append(f'<text x="{lx + 4}" y="{legend_y + 8}" font-size="9" fill="{MUTED}">More</text>')

    stats_y = legend_y + 34
    parts.append(f'<line x1="{pad}" y1="{stats_y - 12}" x2="{width - pad}" y2="{stats_y - 12}" stroke="{BORDER}"/>')
    for i, (val, label) in enumerate([(str(total), "TOTAL CONTRIBUTIONS"), (f"{streak}d", "CURRENT STREAK")]):
        cx = pad + i * (width - 2 * pad) / 2
        parts.append(f'<text x="{cx}" y="{stats_y + 18}" font-size="20" font-weight="700" fill="{ACCENT}">{val}</text>')
        parts.append(f'<text x="{cx}" y="{stats_y + 32}" font-size="8" letter-spacing="0.5" fill="{MUTED}">{label}</text>')

    parts.append("</svg>")
    return "".join(parts)


def main():
    cal = fetch_calendar()
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]

    svg = render(weeks, cal["totalContributions"], current_streak(days), days[0]["date"], days[-1]["date"])

    out = sys.argv[1] if len(sys.argv) > 1 else "images/commit-log.svg"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
