#!/usr/bin/env python3
"""Render an activity heatmap card as static SVG from the GitHub GraphQL API."""
import json
import os
import urllib.request

TOKEN = os.environ["METRICS_TOKEN"]
LOGIN = os.environ.get("GH_LOGIN", "yuanyang-yyang")

CALENDAR_QUERY = """
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

LANGUAGES_QUERY = """
query {
  viewer {
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      nodes {
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
COLORS = ["#ebedf0", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]  # validated ordinal ramp (0, 1-3, 4-9, 10-18, 19+)
LANG_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]  # validated categorical order
OTHER_COLOR = "#9a9890"
MUTED = "#6b6b66"
DARK = "#24292f"
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


def graphql(query):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": LOGIN,
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)["data"]


def fetch_calendar():
    return graphql(CALENDAR_QUERY)["viewer"]["contributionsCollection"]["contributionCalendar"]


def fetch_languages(limit=6):
    repos = graphql(LANGUAGES_QUERY)["viewer"]["repositories"]["nodes"]
    totals = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            totals[edge["node"]["name"]] = totals.get(edge["node"]["name"], 0) + edge["size"]

    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    total = sum(totals.values()) or 1
    top = ranked[:limit]
    other = sum(v for _, v in ranked[limit:])

    langs = [(name, size / total) for name, size in top]
    if other:
        langs.append(("Other", other / total))
    return langs


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


def render_languages(langs, width=480):
    bar_h = 14
    pad = 12
    row_h = 18
    rows = (len(langs) + 2) // 3
    height = pad * 2 + bar_h + 10 + rows * row_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{SANS}">',
        f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>',
    ]

    colors = [LANG_COLORS[i % len(LANG_COLORS)] if name != "Other" else OTHER_COLOR for i, (name, _) in enumerate(langs)]

    x = pad
    bar_w = width - 2 * pad
    for (name, frac), c in zip(langs, colors):
        w = frac * bar_w
        parts.append(f'<rect x="{x:.1f}" y="{pad}" width="{max(w - 1, 0):.1f}" height="{bar_h}" fill="{c}"/>')
        x += w

    col_w = (width - 2 * pad) / 3
    for i, ((name, frac), c) in enumerate(zip(langs, colors)):
        col, row = i % 3, i // 3
        cx = pad + col * col_w
        cy = pad + bar_h + 22 + row * row_h
        parts.append(f'<circle cx="{cx + 4}" cy="{cy - 4}" r="4" fill="{c}"/>')
        parts.append(f'<text x="{cx + 12}" y="{cy}" font-size="10" fill="{DARK}">{name}</text>')
        parts.append(f'<text x="{cx + col_w - 6}" y="{cy}" font-size="10" fill="{MUTED}" text-anchor="end">{frac * 100:.0f}%</text>')

    parts.append("</svg>")
    return "".join(parts)


def main():
    cal = fetch_calendar()
    calendar_svg = render(cal["weeks"])
    languages_svg = render_languages(fetch_languages())

    for out, svg in [
        ("images/commit-log.svg", calendar_svg),
        ("images/languages.svg", languages_svg),
    ]:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as f:
            f.write(svg)


if __name__ == "__main__":
    main()
