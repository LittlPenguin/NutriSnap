from __future__ import annotations

import streamlit as st

TOKENS = {
    "background": "#F7FAF6",
    "primary": "#5CA878",
    "accent": "#F4A261",
    "text": "#1F2933",
    "muted": "#6B7280",
    "card": "#FFFFFF",
    "border": "#E5E7EB",
    "advice": "#EEF8F1",
    "warning": "#FFF4E6",
}


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --nutri-bg: {TOKENS["background"]};
            --nutri-primary: {TOKENS["primary"]};
            --nutri-accent: {TOKENS["accent"]};
            --nutri-text: {TOKENS["text"]};
            --nutri-muted: {TOKENS["muted"]};
            --nutri-card: {TOKENS["card"]};
            --nutri-border: {TOKENS["border"]};
            --nutri-good: {TOKENS["advice"]};
            --nutri-warn: {TOKENS["warning"]};
            --nutri-shadow: 0 10px 28px rgba(31, 41, 51, 0.06);
        }}
        .stApp {{
            background: var(--nutri-bg);
            color: var(--nutri-text);
        }}
        .block-container {{
            padding-top: 1.25rem;
            padding-bottom: 4.5rem;
            max-width: 1180px;
        }}
        .nutri-brand-row,
        .desktop-top,
        .app-header,
        .result-row,
        .history-row,
        .food-row,
        .rank-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        }}
        .brand-lockup {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .brand-mark {{
            width: 40px;
            height: 40px;
            border-radius: 8px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: var(--nutri-primary);
            color: #fff;
            font-weight: 760;
        }}
        .main-title,
        .page-title h2,
        .app-header h3 {{
            margin: 0;
            letter-spacing: 0;
            color: var(--nutri-text);
        }}
        .subtle,
        .muted,
        .small-label,
        .page-title p,
        .app-header small {{
            color: var(--nutri-muted);
        }}
        .small-label {{
            font-size: 0.85rem;
        }}
        .desktop-nav,
        .chips,
        .bottom-nav {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .desktop-nav span,
        .chip,
        .tag {{
            border: 1px solid var(--nutri-border);
            border-radius: 999px;
            background: #fff;
            color: var(--nutri-muted);
            padding: 6px 10px;
            font-size: 0.82rem;
            line-height: 1;
            white-space: nowrap;
        }}
        .desktop-nav span.active,
        .chip.active,
        .tag.primary {{
            border-color: rgba(92, 168, 120, 0.25);
            background: var(--nutri-good);
            color: var(--nutri-primary);
            font-weight: 700;
        }}
        .tag.warn {{
            border-color: rgba(244, 162, 97, 0.28);
            background: var(--nutri-warn);
            color: #B76B20;
            font-weight: 700;
        }}
        .nutri-card,
        .phone-card,
        .desktop-card,
        .result-card,
        .metric-card,
        .history-row,
        .food-row,
        .info-block,
        .desktop-stat,
        .stat-box {{
            background: var(--nutri-card);
            border: 1px solid var(--nutri-border);
            border-radius: 8px;
            box-shadow: var(--nutri-shadow);
        }}
        .nutri-card,
        .phone-card,
        .desktop-card,
        .result-card,
        .metric-card,
        .info-block {{
            padding: 1rem;
            margin-bottom: 0.75rem;
        }}
        .advice-card {{
            background: var(--nutri-good);
            border-color: #D8EBDD;
        }}
        .warning-card {{
            background: var(--nutri-warn);
            border-color: #F8D5A8;
        }}
        .calorie-number,
        .big-kcal,
        .kcal-small {{
            color: var(--nutri-accent);
            font-weight: 780;
        }}
        .calorie-number {{
            font-size: 2.3rem;
            line-height: 1.08;
        }}
        .progress-list {{
            display: grid;
            gap: 10px;
            margin-top: 10px;
        }}
        .progress-item {{
            display: grid;
            grid-template-columns: 82px 1fr 48px;
            align-items: center;
            gap: 10px;
            font-size: 0.9rem;
        }}
        .bar {{
            height: 9px;
            border-radius: 999px;
            overflow: hidden;
            background: #EAF0EC;
        }}
        .bar span {{
            display: block;
            height: 100%;
            border-radius: inherit;
            background: linear-gradient(90deg, var(--nutri-primary), #86C99B);
        }}
        .desktop-work,
        .desktop-two-col,
        .desktop-metrics,
        .stat-grid {{
            display: grid;
            gap: 14px;
        }}
        .desktop-work,
        .desktop-two-col {{
            grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
        }}
        .desktop-metrics {{
            grid-template-columns: repeat(4, minmax(0, 1fr));
            margin-bottom: 14px;
        }}
        .stat-grid {{
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }}
        .desktop-stat,
        .stat-box {{
            padding: 14px;
        }}
        .desktop-stat span,
        .stat-box span {{
            display: block;
            color: var(--nutri-muted);
            font-size: 0.82rem;
            margin-bottom: 6px;
        }}
        .desktop-stat strong,
        .stat-box strong {{
            font-size: 1.25rem;
            color: var(--nutri-text);
        }}
        .bottom-nav {{
            display: none;
            position: sticky;
            bottom: 8px;
            z-index: 20;
            justify-content: space-between;
            padding: 8px;
            border: 1px solid var(--nutri-border);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.94);
            box-shadow: 0 12px 30px rgba(31, 41, 51, 0.12);
            backdrop-filter: blur(12px);
        }}
        .nav-item {{
            min-width: 54px;
            text-align: center;
            color: var(--nutri-muted);
            font-size: 0.78rem;
        }}
        .nav-item.active {{
            color: var(--nutri-primary);
            font-weight: 750;
        }}
        .nav-icon {{
            display: block;
            margin: 0 auto 2px;
            width: 24px;
            height: 24px;
            border-radius: 8px;
            line-height: 24px;
            background: #F1F5F2;
            font-size: 0.75rem;
        }}
        .nav-item.active .nav-icon {{
            background: var(--nutri-good);
        }}
        .desktop-table {{
            display: grid;
            gap: 6px;
        }}
        .table-row {{
            display: grid;
            grid-template-columns: 1fr 0.7fr 0.8fr 0.7fr 2fr;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border-bottom: 1px solid var(--nutri-border);
            font-size: 0.9rem;
        }}
        .table-head {{
            color: var(--nutri-muted);
            font-size: 0.8rem;
            font-weight: 700;
        }}
        div.stButton > button {{
            width: 100%;
            border-radius: 8px;
            border: 1px solid var(--nutri-primary);
            background: var(--nutri-primary);
            color: white;
            font-weight: 700;
        }}
        div.stButton > button:hover {{
            border-color: #4B9367;
            background: #4B9367;
            color: white;
        }}
        @media (max-width: 760px) {{
            .block-container {{
                padding-left: 1rem;
                padding-right: 1rem;
                padding-bottom: 5rem;
            }}
            .desktop-nav {{
                display: none;
            }}
            .bottom-nav {{
                display: flex;
            }}
            .desktop-work,
            .desktop-two-col,
            .desktop-metrics {{
                grid-template-columns: 1fr;
            }}
            .table-row {{
                grid-template-columns: 1fr;
            }}
            .main-title {{
                font-size: 1.75rem;
            }}
            .calorie-number {{
                font-size: 2rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
