"""
TCO Calculator — Mint Ledger theme
==================================
Drop-in module for app_tco.py. Replaces apply_theme() and provides:

- apply_theme()                 → injects all CSS for the Mint Ledger look
- get_plotly_template()         → returns a Plotly layout dict matching the theme
- VEHICLE_PALETTE / SEG_COLORS  → consistent colors for charts
- render_hero(title, caption, hold_years, annual_km, n_vehicles)
- render_leaderboard(results, base_name) → ranked cards w/ best-value badge + sparkline placeholder
- render_heatmap_table(results, base_name)
- render_fuel_icon(fuel) → small SVG inline

Usage in app_tco.py:
    from theme_mint_ledger import (
        apply_theme, get_plotly_template, VEHICLE_PALETTE, SEG_COLORS,
        render_hero, render_leaderboard, render_heatmap_table,
    )
    apply_theme()
    render_hero(...)
    ...
    fig.update_layout(**get_plotly_template())
"""

import streamlit as st
import plotly.graph_objects as go
from typing import List

# ─────────────────────────────────────────────────────────────────────────────
# Palette — Mint Ledger (B2)
# ─────────────────────────────────────────────────────────────────────────────
PALETTE = {
    "bg":           "#0a0f10",
    "sidebar":      "#0f1517",
    "surface":      "#141c1e",
    "surface_alt":  "#1a2326",
    "surface_hi":   "#1f292c",
    "ink":          "#eaf2ee",
    "ink_dim":      "#c5d2cc",
    "muted":        "#7a8a85",
    "muted_strong": "#94a39d",
    "border":       "#1f2a2c",
    "border_strong":"#2a3739",
    "accent":       "#34d399",  # mint — primary / best
    "accent_dark":  "#059669",
    "amber":        "#a78bfa",  # violet — deltas
    "amber_dim":    "rgba(167, 139, 250, 0.13)",
    "good":         "#34d399",
    "bad":          "#f87171",
}

# Per-vehicle palette (cycle for arbitrary number of cars)
VEHICLE_PALETTE = ["#34d399", "#a78bfa", "#f4a16a", "#60a5fa", "#f472b6", "#facc15"]

# Cost-segment colors (consistent across stacked breakdown + tables)
SEG_COLORS = {
    "Aquisição":              "#34d399",
    "Energia":                "#a78bfa",
    "Energia/Combustível":    "#a78bfa",
    "Seguro+Fiscal":          "#60a5fa",
    "Seguro+Fiscalidade":     "#60a5fa",
    "Manutenção":             "#f4a16a",
    "Reparações+Manutenção":  "#f4a16a",
    "Portagens":              "#f472b6",
    "Portagens+Parqueamento": "#f472b6",
}

FUEL_COLORS = {
    "Elétrico": "#34d399",
    "Diesel":   "#7a8a85",
    "Gasolina": "#f4a16a",
    "GPL":      "#60a5fa",
}


# ─────────────────────────────────────────────────────────────────────────────
# CSS injection
# ─────────────────────────────────────────────────────────────────────────────
def apply_theme():
    p = PALETTE
    css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {{
    --bg: {p['bg']};
    --sidebar: {p['sidebar']};
    --surface: {p['surface']};
    --surface-alt: {p['surface_alt']};
    --surface-hi: {p['surface_hi']};
    --ink: {p['ink']};
    --ink-dim: {p['ink_dim']};
    --muted: {p['muted']};
    --muted-strong: {p['muted_strong']};
    --border: {p['border']};
    --border-strong: {p['border_strong']};
    --accent: {p['accent']};
    --accent-dark: {p['accent_dark']};
    --amber: {p['amber']};
    --good: {p['good']};
    --bad: {p['bad']};
    --font-body: "Inter", system-ui, -apple-system, sans-serif;
    --font-mono: "JetBrains Mono", ui-monospace, Menlo, monospace;
}}

/* Page background */
html, body, [data-testid="stAppViewContainer"], .stApp {{
    background: var(--bg) !important;
    color: var(--ink) !important;
    font-family: var(--font-body) !important;
}}

.main .block-container {{
    padding-top: 1.6rem;
    padding-bottom: 4rem;
    max-width: 1320px;
    color: var(--ink);
}}

h1, h2, h3, h4 {{
    color: var(--ink) !important;
    letter-spacing: -0.02em;
    font-family: var(--font-body) !important;
}}

p, label, .stMarkdown, .stText, .stCaption {{
    color: var(--ink-dim) !important;
}}

/* Numbers everywhere should be tabular */
.stMetric [data-testid="stMetricValue"],
.stDataFrame, .stTable, code {{
    font-variant-numeric: tabular-nums;
    font-family: var(--font-mono) !important;
}}

/* Sidebar */
section[data-testid="stSidebar"] > div {{
    background: var(--sidebar) !important;
    border-right: 1px solid var(--border);
}}

section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] p {{
    color: var(--ink-dim) !important;
}}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
    color: var(--ink) !important;
    font-size: 0.95rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted-strong) !important;
}}

/* Tabs — pill style */
.stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
    border-bottom: 1px solid var(--border);
    background: transparent;
}}

.stTabs [data-baseweb="tab"] {{
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    padding: 12px 18px !important;
    color: var(--muted-strong) !important;
    font-weight: 500;
    font-size: 13px;
}}

.stTabs [aria-selected="true"] {{
    color: var(--ink) !important;
    border-bottom-color: var(--accent) !important;
    background: transparent !important;
    box-shadow: none !important;
}}

/* Buttons */
.stButton > button {{
    background: var(--surface) !important;
    color: var(--ink) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 8px !important;
    padding: 0.5rem 1rem !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    box-shadow: none !important;
    transition: all 0.12s ease;
}}

.stButton > button:hover {{
    background: var(--surface-hi) !important;
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}}

.stButton > button[kind="primary"], .stDownloadButton > button {{
    background: var(--accent) !important;
    color: var(--bg) !important;
    border: none !important;
    font-weight: 600 !important;
}}

.stButton > button[kind="primary"]:hover, .stDownloadButton > button:hover {{
    background: var(--accent-dark) !important;
    color: var(--bg) !important;
}}

/* Inputs */
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div, .stTextArea textarea {{
    background: var(--surface) !important;
    color: var(--ink) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 8px !important;
    font-family: var(--font-body) !important;
}}

.stNumberInput input, .stTextInput input[type="number"] {{
    font-family: var(--font-mono) !important;
    font-variant-numeric: tabular-nums;
}}

.stTextInput input:focus, .stNumberInput input:focus {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.15) !important;
}}

/* Slider */
.stSlider [data-baseweb="slider"] [role="slider"] {{
    background: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.18) !important;
}}
.stSlider [data-baseweb="slider"] > div > div > div {{
    background: var(--accent) !important;
}}

/* Toggle */
.stCheckbox label, .stRadio label {{
    color: var(--ink-dim) !important;
}}

/* DataFrame */
.stDataFrame, .stTable {{
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    overflow: hidden;
    background: var(--surface) !important;
}}

.stDataFrame [data-testid="stDataFrameResizable"] {{
    background: var(--surface) !important;
}}

/* Expander */
.stExpander, .streamlit-expanderHeader, [data-testid="stExpander"] {{
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}}

/* Alerts */
.stAlert {{
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--ink-dim) !important;
}}

div[data-baseweb="notification"] {{
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
}}

/* Divider */
hr {{
    border-color: var(--border) !important;
    margin: 1.2rem 0 !important;
}}

/* ─────────────────────────────────────────────────────────────
   Custom HTML blocks (rendered via st.markdown)
   ───────────────────────────────────────────────────────────── */

.tco-hero {{
    padding: 8px 0 22px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 22px;
}}

.tco-hero-eyebrow {{
    font-size: 11px; color: var(--accent);
    font-weight: 500; letter-spacing: 1.4px;
    text-transform: uppercase; margin-bottom: 8px;
}}

.tco-hero-title {{
    font-size: 30px; font-weight: 600; color: var(--ink);
    letter-spacing: -0.6px; line-height: 1.05; margin: 0;
}}

.tco-hero-caption {{
    color: var(--muted-strong); font-size: 14px; margin-top: 6px;
}}

.tco-pills {{
    display: flex; gap: 6px; margin-top: 14px; flex-wrap: wrap;
}}

.tco-pill {{
    padding: 5px 12px; background: var(--surface);
    border: 1px solid var(--border); border-radius: 999px;
    font-size: 11px; color: var(--ink-dim);
    font-family: var(--font-mono);
}}

.tco-pill.accent {{
    color: var(--accent); border-color: rgba(52,211,153,0.35);
}}

/* Leaderboard */
.tco-lb-header {{
    display: flex; justify-content: space-between; align-items: baseline;
    margin: 8px 0 14px;
}}

.tco-lb-header h2 {{
    margin: 0; font-size: 16px; font-weight: 600; color: var(--ink);
}}

.tco-lb-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
    display: grid;
    grid-template-columns: 40px 1fr 200px 160px;
    align-items: center;
    gap: 16px;
}}

.tco-lb-rank {{
    width: 32px; height: 32px; border-radius: 10px;
    background: var(--surface-hi); color: var(--ink);
    font-family: var(--font-mono); font-weight: 700; font-size: 14px;
    display: flex; align-items: center; justify-content: center;
}}

.tco-lb-rank.best {{
    background: var(--accent); color: var(--bg);
}}

.tco-lb-name {{
    display: flex; align-items: center; gap: 8px;
    font-size: 14px; font-weight: 600; color: var(--ink);
    min-width: 0;
}}

.tco-lb-meta {{
    font-size: 11px; color: var(--muted);
    font-family: var(--font-mono); margin-top: 2px;
}}

.tco-lb-meta .imported {{
    color: var(--amber);
}}

.tco-lb-tco {{
    text-align: right;
}}

.tco-lb-tco .label {{
    font-size: 10px; color: var(--muted);
    text-transform: uppercase; letter-spacing: 1px;
}}

.tco-lb-tco .value {{
    font-size: 22px; font-family: var(--font-mono); font-weight: 600;
    color: var(--ink); letter-spacing: -0.4px; line-height: 1.1;
}}

.tco-lb-tco .delta {{
    font-size: 11px; font-family: var(--font-mono); margin-top: 2px;
}}

.tco-lb-tco .delta.baseline {{ color: var(--good); }}
.tco-lb-tco .delta.over     {{ color: var(--amber); }}

.tco-lb-km {{
    text-align: right;
    border-left: 1px solid var(--border);
    padding-left: 16px;
}}

.tco-lb-km .label {{
    font-size: 10px; color: var(--muted);
    text-transform: uppercase; letter-spacing: 1px;
}}

.tco-lb-km .value {{
    font-size: 16px; font-family: var(--font-mono);
    font-weight: 500; color: var(--ink);
}}

.tco-badge-best {{
    font-size: 9px; font-weight: 700; letter-spacing: 0.8px;
    text-transform: uppercase;
    padding: 2px 7px; border-radius: 4px;
    background: var(--accent); color: var(--bg);
    margin-left: 6px;
}}

.tco-fuel-icon {{
    display: inline-flex; align-items: center;
}}

/* Mobile responsive — compress leaderboard cards */
@media (max-width: 820px) {{
    .tco-lb-card {{
        grid-template-columns: 32px 1fr;
        gap: 10px;
        padding: 12px 14px;
    }}
    .tco-lb-tco, .tco-lb-km {{
        grid-column: 1 / -1; text-align: left;
        border-left: none; padding-left: 0;
        display: flex; justify-content: space-between; align-items: baseline;
        border-top: 1px solid var(--border); padding-top: 8px; margin-top: 4px;
    }}
    .tco-lb-tco .value {{ font-size: 18px; }}
    .tco-hero-title {{ font-size: 22px; }}
    .main .block-container {{ padding-left: 0.5rem; padding-right: 0.5rem; }}
}}

/* Manage app footer — just polish color */
[data-testid="manage-app-button"] {{
    color: var(--muted) !important;
}}

/* Hide Streamlit default header padding/branding chrome */
header[data-testid="stHeader"] {{
    background: transparent !important;
}}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Plotly template
# ─────────────────────────────────────────────────────────────────────────────
def get_plotly_template() -> dict:
    p = PALETTE
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family='"Inter", system-ui, sans-serif',
            color=p["ink_dim"],
            size=12,
        ),
        colorway=VEHICLE_PALETTE,
        xaxis=dict(
            gridcolor=p["border"],
            linecolor=p["border_strong"],
            tickfont=dict(family='"JetBrains Mono", monospace', color=p["muted_strong"], size=10),
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor=p["border"],
            linecolor=p["border_strong"],
            tickfont=dict(family='"JetBrains Mono", monospace', color=p["muted_strong"], size=10),
            zeroline=False,
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=p["ink_dim"], size=11),
            bordercolor=p["border"],
            borderwidth=0,
        ),
        margin=dict(l=50, r=20, t=40, b=40),
        hoverlabel=dict(
            bgcolor=p["surface"],
            bordercolor=p["border_strong"],
            font=dict(family='"JetBrains Mono", monospace', color=p["ink"], size=11),
        ),
        title=dict(font=dict(color=p["ink"], size=14, family='"Inter", system-ui, sans-serif')),
    )


def style_plotly(fig: go.Figure) -> go.Figure:
    """Apply theme to an existing figure."""
    fig.update_layout(**get_plotly_template())
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Custom HTML blocks
# ─────────────────────────────────────────────────────────────────────────────
def _fuel_icon_svg(fuel: str, size: int = 13) -> str:
    color = FUEL_COLORS.get(fuel, "#7a8a85")
    if fuel == "Elétrico":
        path = '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" fill="{c}" stroke="none"/>'.format(c=color)
    elif fuel == "Diesel":
        path = '<path d="M3 22h12V4H3z"/><path d="M15 12h3a2 2 0 0 1 2 2v4a2 2 0 0 0 2 2"/><path d="M20 6l-2-2"/><line x1="6" y1="8" x2="12" y2="8"/>'
    elif fuel == "GPL":
        path = '<path d="M8 3h8v3h-8z"/><path d="M7 6h10v15H7z"/><line x1="10" y1="11" x2="14" y2="11"/>'
    else:  # Gasolina
        path = '<path d="M3 22h12V4H3z"/><path d="M15 12h3a2 2 0 0 1 2 2v4a2 2 0 0 0 2 2"/><path d="M20 6l-2-2"/>'
    return (
        f'<svg class="tco-fuel-icon" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
        f'stroke-linejoin="round">{path}</svg>'
    )


def _eur(x: float, decimals: int = 0) -> str:
    if x is None:
        return "—"
    n = round(x, decimals)
    sign = "−" if n < 0 else ""
    n = abs(n)
    int_part, _, dec_part = f"{n:.{decimals}f}".partition(".")
    int_part = "{:,}".format(int(int_part)).replace(",", ".")
    out = sign + (f"{int_part},{dec_part}" if dec_part else int_part)
    return out + " €"


def render_hero(title: str, caption: str, hold_years: int, annual_km: int, n_vehicles: int):
    annual_km_str = "{:,}".format(int(annual_km)).replace(",", " ")
    html = f"""
<div class="tco-hero">
    <div class="tco-hero-eyebrow">Simulação · PT 2026</div>
    <div class="tco-hero-title">{title}</div>
    <div class="tco-hero-caption">{caption}</div>
    <div class="tco-pills">
        <div class="tco-pill">{hold_years} anos</div>
        <div class="tco-pill">{annual_km_str} km/ano</div>
        <div class="tco-pill accent">{n_vehicles} viatura{"s" if n_vehicles != 1 else ""}</div>
    </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


def render_leaderboard(results: list, base_name: str = None):
    """
    results: list of CalculationResult (or dicts with the same fields).
    base_name: name of baseline vehicle (defaults to best/lowest TCO).
    """
    if not results:
        return
    # Normalize accessor: support dataclass and dict
    def get(r, attr, default=None):
        if hasattr(r, attr):
            return getattr(r, attr)
        if isinstance(r, dict):
            return r.get(attr, default)
        return default

    sorted_r = sorted(results, key=lambda r: get(r, "total_cost", 0))
    best = sorted_r[0]
    base = next((r for r in sorted_r if get(r, "vehicle_name") == base_name), best)
    base_tco = get(base, "total_cost", 0)

    cards_html = []
    for i, r in enumerate(sorted_r):
        is_best = (i == 0)
        rank = i + 1
        name = get(r, "vehicle_name", "—")
        tco = get(r, "total_cost", 0)
        cost_km = get(r, "cost_per_km", 0)
        delta = tco - base_tco

        # Fuel icon — try to derive fuel from vehicle metadata if attached, else from energy_unit
        unit = get(r, "energy_unit", "")
        fuel_guess = "Elétrico" if unit == "kWh" else "Gasolina"
        # Better: caller can attach .fuel_type onto the result
        fuel = get(r, "fuel_type", fuel_guess)

        meta = get(r, "_meta", "")  # optional: caller can attach a "2024 · Elétrico · 15,2 kWh/100" string
        if not meta:
            year = get(r, "year", "")
            cons = get(r, "consumption", None)
            cons_str = ""
            if cons is not None:
                cons_unit = "kWh" if fuel == "Elétrico" else "L"
                cons_str = f" · {str(cons).replace('.', ',')} {cons_unit}/100"
            imp = get(r, "is_imported", False)
            imp_str = ' · <span class="imported">importada</span>' if imp else ""
            meta = f"{year} · {fuel}{cons_str}{imp_str}"

        delta_html = (
            '<div class="delta baseline">— baseline</div>'
            if is_best
            else f'<div class="delta over">+{_eur(delta)}</div>'
        )

        best_badge = '<span class="tco-badge-best">Best Value</span>' if is_best else ""

        card = f"""
<div class="tco-lb-card">
    <div class="tco-lb-rank {'best' if is_best else ''}">{rank}</div>
    <div>
        <div class="tco-lb-name">
            {_fuel_icon_svg(fuel)}
            <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{name}</span>
            {best_badge}
        </div>
        <div class="tco-lb-meta">{meta}</div>
    </div>
    <div class="tco-lb-tco">
        <div class="label">TCO</div>
        <div class="value">{_eur(tco)}</div>
        {delta_html}
    </div>
    <div class="tco-lb-km">
        <div class="label">€/km</div>
        <div class="value">{('%.3f' % cost_km).replace('.', ',')}</div>
    </div>
</div>
"""
        cards_html.append(card)

    base_tag = f'<div style="font-size:11px;color:var(--muted);">base: <span style="color:var(--ink);">{get(base, "vehicle_name")}</span></div>'
    block = f"""
<div class="tco-lb-header">
    <div>
        <h2>Ranking por TCO</h2>
        <div style="font-size:12px;color:var(--muted-strong);margin-top:2px;">Menor custo total no período de posse</div>
    </div>
    {base_tag}
</div>
{''.join(cards_html)}
"""
    st.markdown(block, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Heatmap helper for st.dataframe (Styler)
# ─────────────────────────────────────────────────────────────────────────────
def heatmap_styler(df, total_rows: List[str] = None, rate_rows: List[str] = None, credit_rows: List[str] = None):
    """
    Returns a pandas Styler with cell heatmap colors aligned to Mint Ledger palette.
    df: index = categories, columns = vehicles, values numeric.
    """
    total_rows = total_rows or ["TCO Total", "€/km"]
    rate_rows = rate_rows or ["€/km"]
    credit_rows = credit_rows or ["Revenda"]

    def color_row(row):
        try:
            vals = [float(v) for v in row.values]
        except Exception:
            return [""] * len(row)
        if not vals:
            return [""] * len(row)
        invert = row.name in credit_rows
        mn, mx = min(vals), max(vals)
        if mx == mn:
            return [""] * len(row)
        styles = []
        for v in vals:
            norm = (v - mn) / (mx - mn)
            if invert:
                norm = 1 - norm
            if row.name in total_rows or row.name in rate_rows:
                if v == (mx if invert else mn):
                    styles.append("background-color: rgba(167,139,250,0.13); color: #a78bfa; font-weight: 600;")
                else:
                    styles.append("color: #eaf2ee; font-weight: 600;")
            else:
                if norm < 0.34:
                    styles.append("background-color: rgba(52,211,153,0.11);")
                elif norm < 0.67:
                    styles.append("background-color: rgba(251,191,36,0.09);")
                else:
                    styles.append("background-color: rgba(248,113,113,0.11);")
        return styles

    return df.style.apply(color_row, axis=1)
