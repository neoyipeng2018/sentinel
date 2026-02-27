"""Generate a standalone HTML report from Sentinel's SQLite database.

Usage:
    poetry run python generate_report.py              # writes report.html
    poetry run python generate_report.py -o my.html   # custom output path
"""

import argparse
import html
from datetime import UTC, datetime

from ai.chains.risk_assessor import compute_asset_risk_scores, get_top_risks
from models.schemas import AssetClass, Narrative, RiskLevel, SignalSource
from storage.narrative_store import get_narrative_history, init_db, load_active_narratives

# --- Constants (mirrored from dashboard modules) ---

RISK_COLORS = {
    RiskLevel.CRITICAL: "#FF1744",
    RiskLevel.HIGH: "#FF9100",
    RiskLevel.MEDIUM: "#FFEA00",
    RiskLevel.LOW: "#00E676",
}

ASSET_LABELS = {
    AssetClass.EQUITIES: "Equities",
    AssetClass.CREDIT: "Credit",
    AssetClass.RATES: "Rates",
    AssetClass.PRIVATE_MARKETS: "Private Markets",
    AssetClass.REAL_ESTATE: "Real Estate",
    AssetClass.COMMODITIES: "Commodities",
    AssetClass.FX: "FX",
}

SOURCE_ICONS = {
    SignalSource.NEWS: "&#x1F4F0;",      # 📰
    SignalSource.MARKET_DATA: "&#x1F4CA;",  # 📊
    SignalSource.SOCIAL: "&#x1F4AC;",      # 💬
}

RISK_LEVEL_NUM = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _esc(text: str) -> str:
    """HTML-escape a string."""
    return html.escape(str(text))


def _risk_color_for_score(score: float) -> str:
    if score >= 7:
        return RISK_COLORS[RiskLevel.CRITICAL]
    elif score >= 5:
        return RISK_COLORS[RiskLevel.HIGH]
    elif score >= 3:
        return RISK_COLORS[RiskLevel.MEDIUM]
    return RISK_COLORS[RiskLevel.LOW]


def _trend_arrow(trend: str) -> str:
    return {"intensifying": "&#x2191;", "fading": "&#x2193;", "stable": "&#x2192;"}.get(
        trend, "&#x2192;"
    )


def render_overview(narratives: list[Narrative]) -> str:
    if not narratives:
        return '<p class="empty">No active narratives in the database.</p>'

    scores = compute_asset_risk_scores(narratives)

    # Heatmap cards
    cards = []
    for asset, score in scores.items():
        color = _risk_color_for_score(score)
        label = ASSET_LABELS.get(asset, asset.value)
        cards.append(
            f'<div class="heatmap-card" style="border-left:4px solid {color};'
            f'background:{color}20;">'
            f'<div class="hm-label">{_esc(label)}</div>'
            f'<div class="hm-score">{score}</div>'
            f"</div>"
        )

    heatmap = '<div class="heatmap-grid">' + "\n".join(cards) + "</div>"

    # Top narratives
    top = get_top_risks(narratives, n=10)
    rows = []
    for nar in top:
        color = RISK_COLORS[nar.risk_level]
        # Build hurt / benefit asset strings
        risk_parts = []
        for a, imps in nar.assets_at_risk.items():
            label = ASSET_LABELS.get(a, a.value)
            subs = ", ".join(f"{_esc(i.asset)}" for i in imps)
            risk_parts.append(f"{label} ({subs})")
        risk_str = ", ".join(risk_parts) if risk_parts else "—"

        benefit_parts = []
        for a, imps in nar.assets_to_benefit.items():
            label = ASSET_LABELS.get(a, a.value)
            subs = ", ".join(f"{_esc(i.asset)}" for i in imps)
            benefit_parts.append(f"{label} ({subs})")
        benefit_str = ", ".join(benefit_parts) if benefit_parts else "—"

        arrow = _trend_arrow(nar.trend)
        rows.append(
            f"<details>"
            f'<summary><span class="risk-badge" style="background:{color};">'
            f"{_esc(nar.risk_level.value.upper())}</span> "
            f"{_esc(nar.title)}</summary>"
            f'<div class="narrative-detail">'
            f"<p>{_esc(nar.summary)}</p>"
            f"<p><strong>Assets at risk:</strong> {risk_str}</p>"
            f"<p><strong>Assets to benefit:</strong> {benefit_str}</p>"
            f"<p><strong>Trend:</strong> {arrow} {_esc(nar.trend)} &middot; "
            f"<strong>Confidence:</strong> {nar.confidence:.0%} &middot; "
            f"<strong>Signals:</strong> {len(nar.signals)} &middot; "
            f"<strong>Updated:</strong> {nar.last_updated.strftime('%Y-%m-%d %H:%M')}</p>"
            f"</div></details>"
        )

    narrative_list = "\n".join(rows)

    return (
        f"<h2>Risk Heatmap by Asset Class</h2>\n{heatmap}\n"
        f"<h2>Top Risk Narratives</h2>\n{narrative_list}"
    )


def render_alerts(narratives: list[Narrative]) -> str:
    all_signals: list[tuple] = []
    for nar in narratives:
        for sig in nar.signals:
            all_signals.append((sig, nar))

    if not all_signals:
        return '<p class="empty">No signals in the database.</p>'

    all_signals.sort(key=lambda x: x[0].timestamp, reverse=True)

    rows = []
    for sig, nar in all_signals[:100]:
        icon = SOURCE_ICONS.get(sig.source, "&#x1F4CC;")
        color = RISK_COLORS[nar.risk_level]
        ts = sig.timestamp.strftime("%b %d, %H:%M")
        url_link = (
            f' &middot; <a href="{_esc(sig.url)}" target="_blank">source</a>'
            if sig.url
            else ""
        )
        rows.append(
            f'<div class="signal-row">'
            f'<div class="signal-title">{icon} {_esc(sig.title)}</div>'
            f'<div class="signal-meta">'
            f"{ts} &middot; {_esc(sig.source.value)} &middot; "
            f'Narrative: {_esc(nar.title)} &middot; <span class="risk-badge" '
            f'style="background:{color};">{_esc(nar.risk_level.value.upper())}</span>'
            f"{url_link}"
            f"</div></div>"
        )

    header = f"<p class='signal-count'>Showing {len(rows)} of {len(all_signals)} signals</p>"
    return header + "\n".join(rows)


def render_timeline(narratives: list[Narrative]) -> str:
    if not narratives:
        return '<p class="empty">No active narratives to display.</p>'

    sections = []
    for nar in narratives:
        history = get_narrative_history(nar.id)
        color = RISK_COLORS[nar.risk_level]

        # History table
        if history:
            hist_rows = []
            for h in history:
                ts = datetime.fromisoformat(h["timestamp"]).strftime("%Y-%m-%d %H:%M")
                lvl = h["risk_level"]
                lvl_color = RISK_COLORS.get(RiskLevel(lvl), "#888")
                hist_rows.append(
                    f"<tr>"
                    f"<td>{ts}</td>"
                    f'<td><span class="risk-badge" style="background:{lvl_color};">'
                    f"{_esc(lvl.upper())}</span></td>"
                    f"<td>{_esc(h['trend'])}</td>"
                    f"</tr>"
                )

            # SVG bar chart of risk levels over time
            svg = _render_timeline_svg(history)

            hist_table = (
                f"{svg}"
                f'<table class="history-table">'
                f"<thead><tr><th>Timestamp</th><th>Risk</th><th>Trend</th></tr></thead>"
                f"<tbody>{''.join(hist_rows)}</tbody></table>"
            )
        else:
            hist_table = "<p class='empty'>No history snapshots yet.</p>"

        # Associated signals
        sig_items = []
        for sig in sorted(nar.signals, key=lambda s: s.timestamp, reverse=True):
            ds = sig.timestamp.strftime("%b %d")
            sig_items.append(
                f"<li><strong>{_esc(sig.title)}</strong> ({_esc(sig.source.value)}, {ds})</li>"
            )
        sig_list = f"<ul>{''.join(sig_items)}</ul>" if sig_items else "<p>No signals.</p>"

        sections.append(
            f"<details>"
            f'<summary><span class="risk-badge" style="background:{color};">'
            f"{_esc(nar.risk_level.value.upper())}</span> "
            f"{_esc(nar.title)}</summary>"
            f'<div class="narrative-detail">'
            f"<p><em>{_esc(nar.summary)}</em></p>"
            f"<p><strong>Trend:</strong> {_esc(nar.trend)} &middot; "
            f"<strong>Confidence:</strong> {nar.confidence:.0%}</p>"
            f"<h4>Risk History</h4>{hist_table}"
            f"<h4>Associated Signals</h4>{sig_list}"
            f"</div></details>"
        )

    return "\n".join(sections)


def _render_timeline_svg(history: list[dict]) -> str:
    """Render an inline SVG bar chart of risk level over time."""
    if len(history) < 2:
        return ""

    bar_w = 32
    gap = 4
    chart_h = 100
    label_h = 20
    total_w = len(history) * (bar_w + gap)
    svg_h = chart_h + label_h + 10

    level_names = ["low", "medium", "high", "critical"]
    level_colors = {
        "low": RISK_COLORS[RiskLevel.LOW],
        "medium": RISK_COLORS[RiskLevel.MEDIUM],
        "high": RISK_COLORS[RiskLevel.HIGH],
        "critical": RISK_COLORS[RiskLevel.CRITICAL],
    }

    # Y-axis labels
    y_labels = ""
    for i, name in enumerate(level_names):
        y = chart_h - ((i + 1) / 4) * chart_h + 5
        y_labels += (
            f'<text x="0" y="{y}" fill="#888" font-size="10" '
            f'font-family="monospace">{name[:3].upper()}</text>'
        )

    bars = []
    x_offset = 50  # room for y-axis labels
    for i, h in enumerate(history):
        lvl = RISK_LEVEL_NUM.get(h["risk_level"], 1)
        bar_h = (lvl / 4) * chart_h
        x = x_offset + i * (bar_w + gap)
        y = chart_h - bar_h
        color = level_colors.get(h["risk_level"], "#888")
        ts = datetime.fromisoformat(h["timestamp"]).strftime("%m/%d")
        bars.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" '
            f'fill="{color}" rx="3" opacity="0.85"/>'
            f'<text x="{x + bar_w // 2}" y="{chart_h + label_h}" '
            f'fill="#888" font-size="9" font-family="monospace" '
            f'text-anchor="middle">{ts}</text>'
        )

    total_svg_w = x_offset + total_w + 10
    return (
        f'<svg width="{total_svg_w}" height="{svg_h}" '
        f'xmlns="http://www.w3.org/2000/svg" style="margin:12px 0;">'
        f"{y_labels}{''.join(bars)}</svg>"
    )


def render_briefing() -> str:
    return (
        '<p class="empty">AI briefings are generated on-demand in the Streamlit app '
        "and are not stored in the database. Run the app and click "
        "<strong>Generate Briefing</strong> to create one.</p>"
    )


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0E1117; color: #FAFAFA; padding: 24px; line-height: 1.6;
    max-width: 1200px; margin: 0 auto;
}
h1 { font-size: 1.8em; margin-bottom: 4px; }
h2 { font-size: 1.3em; margin: 28px 0 12px 0; color: #ccc;
  border-bottom: 1px solid #333; padding-bottom: 6px; }
h4 { font-size: 1em; margin: 16px 0 8px 0; color: #aaa; }
a { color: #4DA6FF; }
p { margin: 6px 0; }
.header-meta { color: #888; font-size: 0.85em; margin-bottom: 24px; }
.empty { color: #888; font-style: italic; padding: 16px 0; }
.section { margin-bottom: 40px; }
.section > h1 { font-size: 1.5em; color: #fff;
  border-bottom: 2px solid #333; padding-bottom: 8px; margin-bottom: 16px; }
/* Heatmap */
.heatmap-grid { display: grid; gap: 10px;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }
.heatmap-card { padding: 14px; border-radius: 6px; }
.hm-label { font-size: 0.8em; color: #aaa; }
.hm-score { font-size: 2em; font-weight: bold; }
/* Risk badge */
.risk-badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 0.7em; font-weight: 700; color: #000; vertical-align: middle;
}
/* Details / collapsible */
details { background: #1A1D23; border-radius: 6px; margin: 6px 0; }
details > summary {
    padding: 10px 14px; cursor: pointer; list-style: none; font-weight: 600;
}
details > summary::-webkit-details-marker { display: none; }
details > summary::before { content: "\\25B6  "; font-size: 0.7em; color: #888; }
details[open] > summary::before { content: "\\25BC  "; }
.narrative-detail { padding: 8px 14px 14px 14px; border-top: 1px solid #333; }
.narrative-detail p { margin: 4px 0; }
/* Signals */
.signal-row { padding: 10px 0; border-bottom: 1px solid #222; }
.signal-title { font-weight: 600; }
.signal-meta { font-size: 0.8em; color: #888; margin-top: 2px; }
.signal-count { color: #888; font-size: 0.85em; margin-bottom: 8px; }
/* History table */
.history-table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 0.85em; }
.history-table th { text-align: left; color: #888;
  padding: 4px 8px; border-bottom: 1px solid #333; }
.history-table td { padding: 4px 8px; border-bottom: 1px solid #1E2028; }
/* Lists */
ul { padding-left: 20px; margin: 6px 0; }
li { margin: 3px 0; }
/* Nav */
nav { display: flex; gap: 8px; margin: 16px 0 24px 0; flex-wrap: wrap; }
nav a {
    padding: 6px 16px; border-radius: 6px; background: #1A1D23;
    color: #ccc; text-decoration: none; font-size: 0.9em;
}
nav a:hover { background: #252830; color: #fff; }
"""


def build_report(narratives: list[Narrative]) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    overview_html = render_overview(narratives)
    alerts_html = render_alerts(narratives)
    timeline_html = render_timeline(narratives)
    briefing_html = render_briefing()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sentinel Risk Report</title>
<style>{CSS}</style>
</head>
<body>

<h1>&#x1F6E1;&#xFE0F; Sentinel Risk Report</h1>
<p class="header-meta">Generated {now} &middot; {len(narratives)} active narratives</p>

<nav>
<a href="#overview">Overview</a>
<a href="#alerts">Alert Feed</a>
<a href="#timeline">Timeline</a>
<a href="#briefing">AI Briefing</a>
</nav>

<div class="section" id="overview">
<h1>Risk Overview</h1>
{overview_html}
</div>

<div class="section" id="alerts">
<h1>Alert Feed</h1>
{alerts_html}
</div>

<div class="section" id="timeline">
<h1>Narrative Timeline</h1>
{timeline_html}
</div>

<div class="section" id="briefing">
<h1>AI Briefing</h1>
{briefing_html}
</div>

</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a static HTML report from Sentinel DB")
    parser.add_argument("-o", "--output", default="report.html", help="Output file path")
    args = parser.parse_args()

    init_db()
    narratives = load_active_narratives()

    report = build_report(narratives)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Report written to {args.output} ({len(narratives)} narratives)")


if __name__ == "__main__":
    main()
