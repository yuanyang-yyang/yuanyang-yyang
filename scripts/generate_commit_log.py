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
MUTED = "#6b6b66"
SURFACE = "#ffffff"
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


def render(weeks):
    cell, gap = 10, 2
    step = cell + gap
    grid_w = len(weeks) * step - gap
    pad = 12
    left_pad = 30
    width = pad * 2 + left_pad + grid_w
    grid_top = pad + 14
    grid_h = 7 * step
    height = grid_top + grid_h + 26

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{SANS}">',
        f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>',
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

    parts.append("</svg>")
    return "".join(parts)


def main():
    cal = fetch_calendar()
    svg = render(cal["weeks"])

    out = sys.argv[1] if len(sys.argv) > 1 else "images/commit-log.svg"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
