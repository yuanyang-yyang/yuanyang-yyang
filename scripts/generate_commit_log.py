#!/usr/bin/env python3
"""Render a contribution calendar card as static SVG from the GitHub GraphQL API."""
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
COLORS = ["#ebedf0", "#e2a065", "#d67f3c", "#c2601c", "#8f3a08"]  # validated ordinal ramp (0, 1-3, 4-9, 10-18, 19+)
INK = "#0b0b0b"
MUTED = "#6b6b66"
ACCENT = "#8f3a08"
SURFACE = "#ffffff"


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


def render(weeks, total, active, longest, peak, start_date, end_date):
    cell, gap = 10, 2
    step = cell + gap
    grid_w = len(weeks) * step - gap
    pad = 26
    left_pad = 40
    width = pad * 2 + left_pad + grid_w
    grid_top = pad + 70
    height = grid_top + 7 * step + 66

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">',
        f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>',
    ]

    m = 8
    parts.append(
        f'<rect x="{m}" y="{m}" width="{width - 2 * m}" height="{height - 2 * m}" '
        f'fill="none" stroke="#d8d6cf" stroke-width="1" stroke-dasharray="3,3" rx="4"/>'
    )
    for cx, cy in [(m, m), (width - m, m), (m, height - m), (width - m, height - m)]:
        parts.append(f'<path d="M{cx - 5} {cy} H{cx + 5} M{cx} {cy - 5} V{cy + 5}" stroke="#b9b6ac" stroke-width="1"/>')

    parts.append(f'<text x="{pad}" y="{pad + 10}" font-size="11" letter-spacing="2" fill="{ACCENT}" font-weight="700">COMMIT LOG</text>')
    parts.append(
        f'<text x="{pad}" y="{pad + 34}" font-size="22" '
        f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" '
        f'font-weight="700" fill="{INK}">Contribution calendar</text>'
    )
    parts.append(f'<text x="{width - pad}" y="{pad + 16}" font-size="34" font-weight="700" fill="{ACCENT}" text-anchor="end">{total}</text>')
    parts.append(f'<text x="{width - pad}" y="{pad + 34}" font-size="11" fill="{MUTED}" text-anchor="end">{start_date} / {end_date}</text>')
    parts.append(f'<line x1="{pad}" y1="{pad + 48}" x2="{width - pad}" y2="{pad + 48}" stroke="#e5e3db"/>')

    grid_left = pad + left_pad - 14

    prev_month = None
    for wi, w in enumerate(weeks):
        m_idx = int(w["contributionDays"][0]["date"].split("-")[1]) - 1
        if m_idx != prev_month:
            x = grid_left + wi * step
            parts.append(f'<text x="{x}" y="{grid_top - 8}" font-size="10" fill="{MUTED}">{MONTHS[m_idx]}</text>')
            prev_month = m_idx

    for wd, label in {1: "MON", 3: "WED", 5: "FRI"}.items():
        y = grid_top + wd * step + cell - 1
        parts.append(f'<text x="{pad}" y="{y}" font-size="9" fill="{MUTED}">{label}</text>')

    for wi, w in enumerate(weeks):
        for d in w["contributionDays"]:
            x = grid_left + wi * step
            y = grid_top + d["weekday"] * step
            c = COLORS[bucket(d["contributionCount"])]
            parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{c}" stroke="rgba(27,31,35,0.06)"/>')

    legend_y = grid_top + 7 * step + 26
    parts.append(f'<text x="{pad}" y="{legend_y}" font-size="9" letter-spacing="1.5" fill="{MUTED}">PER DAY</text>')
    lx = pad + 70
    for i, (c, label) in enumerate(zip(COLORS, ["0", "1–3", "4–9", "10–18", "19+"])):
        parts.append(f'<rect x="{lx}" y="{legend_y - 9}" width="10" height="10" rx="2" fill="{c}"/>')
        parts.append(f'<text x="{lx + 14}" y="{legend_y}" font-size="9" fill="{MUTED}">{label}</text>')
        lx += 46

    foot_y = legend_y + 34
    col_w = (width - 2 * pad) / 3
    for i, (val, label) in enumerate([(str(active), "ACTIVE DAYS"), (f"{longest}d", "LONGEST RUN"), (str(peak), "PEAK DAY")]):
        cx = pad + col_w * (i + 0.5)
        parts.append(f'<text x="{cx}" y="{foot_y}" font-size="18" font-weight="700" fill="{INK}" text-anchor="middle">{val}</text>')
        parts.append(f'<text x="{cx}" y="{foot_y + 14}" font-size="8" letter-spacing="1" fill="{MUTED}" text-anchor="middle">{label}</text>')

    parts.append("</svg>")
    return "".join(parts)


def main():
    cal = fetch_calendar()
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]

    active = sum(1 for d in days if d["contributionCount"] > 0)
    peak = max((d["contributionCount"] for d in days), default=0)

    longest = cur = 0
    for d in days:
        if d["contributionCount"] > 0:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0

    svg = render(weeks, cal["totalContributions"], active, longest, peak, days[0]["date"], days[-1]["date"])

    out = sys.argv[1] if len(sys.argv) > 1 else "images/commit-log.svg"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
