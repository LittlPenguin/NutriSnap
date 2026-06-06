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
        [data-testid="stHeader"] {{
            background: rgba(247, 250, 246, 0.92);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(229, 231, 235, 0.72);
        }}
        [data-testid="stToolbar"] {{
            right: 0.75rem;
        }}
        .block-container {{
            padding-top: 3.75rem;
            padding-bottom: 4.5rem;
            max-width: 1180px;
        }}
        .block-container,
        .block-container * {{
            box-sizing: border-box;
        }}
        .block-container,
        div[data-testid="stHorizontalBlock"],
        div[data-testid="column"],
        div[data-testid="stVerticalBlock"],
        div[data-testid="stElementContainer"] {{
            min-width: 0;
            max-width: 100%;
        }}
        .nutri-brand-row,
        .desktop-top,
        .app-header,
        .result-row,
        .input-line,
        .history-row,
        .food-row,
        .rank-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            min-width: 0;
        }}
        .result-row,
        .input-line,
        .history-row,
        .food-row,
        .rank-row {{
            flex-wrap: wrap;
        }}
        .result-row > *,
        .input-line > *,
        .history-row > *,
        .food-row > *,
        .rank-row > * {{
            min-width: 0;
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
        .desktop-nav,
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
            text-decoration: none;
        }}
        .streamlit-nav,
        div[data-testid="stElementContainer"][class*="st-key-desktop_nav_"],
        div[data-testid="stVerticalBlock"][class*="st-key-desktop_nav_container_"] {{
            margin: 10px 0 12px;
            border: none;
            padding: 0;
            background: transparent;
        }}
        .streamlit-nav [data-testid="stPills"],
        .streamlit-bottom-nav [data-testid="stPills"],
        div[data-testid="stElementContainer"][class*="st-key-desktop_nav_"] [data-testid="stPills"],
        div[data-testid="stElementContainer"][class*="st-key-bottom_nav_"] [data-testid="stPills"] {{
            width: 100%;
        }}
        .streamlit-nav [data-testid="stPills"] button,
        .streamlit-bottom-nav [data-testid="stPills"] button,
        div[data-testid="stElementContainer"][class*="st-key-desktop_nav_"] [data-testid="stPills"] button,
        div[data-testid="stElementContainer"][class*="st-key-bottom_nav_"] [data-testid="stPills"] button {{
            border: 1px solid var(--nutri-border);
            border-radius: 999px;
            background: #fff;
            color: var(--nutri-muted);
            font-weight: 700;
        }}
        .streamlit-nav [data-testid="stPills"] button[aria-pressed="true"],
        .streamlit-bottom-nav [data-testid="stPills"] button[aria-pressed="true"],
        div[data-testid="stElementContainer"][class*="st-key-desktop_nav_"]
        [data-testid="stPills"] button[aria-pressed="true"],
        div[data-testid="stElementContainer"][class*="st-key-bottom_nav_"]
        [data-testid="stPills"] button[aria-pressed="true"] {{
            border-color: rgba(92, 168, 120, 0.25);
            background: var(--nutri-good);
            color: var(--nutri-primary);
        }}
        .desktop-nav.active,
        .chip.active,
        .tag.primary {{
            border-color: rgba(92, 168, 120, 0.25);
            background: var(--nutri-good);
            color: var(--nutri-primary);
            font-weight: 700;
        }}
        .nav-item:hover {{
            color: var(--nutri-primary);
            text-decoration: none;
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
            max-width: 100%;
            min-width: 0;
            overflow-wrap: anywhere;
            word-break: break-word;
            overflow-x: hidden;
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
            grid-template-columns: minmax(0, 82px) minmax(0, 1fr) minmax(42px, 48px);
            align-items: center;
            gap: 10px;
            font-size: 0.9rem;
            min-width: 0;
        }}
        .progress-item > * {{
            min-width: 0;
        }}
        .progress-item span {{
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
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
        .stat-grid,
        .desktop-result-grid {{
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
        .desktop-result-grid {{
            grid-template-columns: repeat(2, minmax(0, 1fr));
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
        .history-list,
        .food-grid,
        .rank-list,
        .chart-shell {{
            display: grid;
            gap: 10px;
        }}
        .history-list,
        .food-grid {{
            margin-top: 10px;
        }}
        .food-grid {{
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }}
        .history-row,
        .food-row,
        .rank-row {{
            align-items: flex-start;
            min-width: 0;
            max-width: 100%;
        }}
        .history-row strong,
        .food-row strong,
        .rank-row strong {{
            display: block;
            margin-bottom: 4px;
        }}
        .history-row span,
        .food-row span,
        .rank-row span,
        .history-row small,
        .food-row small {{
            display: block;
            color: var(--nutri-muted);
            font-size: 0.82rem;
            line-height: 1.45;
        }}
        .history-row small,
        .food-row small {{
            margin-top: 5px;
            max-width: 720px;
            overflow-wrap: anywhere;
        }}
        .history-row > div,
        .food-row > div,
        .rank-row > div {{
            flex: 1 1 0;
            min-width: 0;
        }}
        .history-row .kcal-small,
        .rank-row .kcal-small {{
            flex: 0 0 auto;
            white-space: nowrap;
        }}
        .food-kcal {{
            min-width: 132px;
            text-align: right;
            flex: 0 0 auto;
        }}
        .food-kcal b,
        .rank-row b {{
            display: block;
            color: var(--nutri-accent);
        }}
        .food-kcal span {{
            margin-top: 4px;
        }}
        .boundary-card p {{
            margin: 6px 0 0;
            color: var(--nutri-muted);
            line-height: 1.55;
        }}
        .chart-shell {{
            background: var(--nutri-card);
            border: 1px solid var(--nutri-border);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: var(--nutri-shadow);
            margin-bottom: 0.75rem;
        }}
        .latest-upload-card {{
            max-width: 520px;
        }}
        .latest-upload-figure {{
            width: min(100%, 420px);
            margin: 14px auto 0;
        }}
        .latest-upload-figure img {{
            display: block;
            width: 100%;
            max-height: 260px;
            border-radius: 8px;
            object-fit: cover;
            border: 1px solid var(--nutri-border);
            background: #F1F5F2;
        }}
        .latest-upload-figure figcaption,
        .latest-upload-empty {{
            margin-top: 8px;
            color: var(--nutri-muted);
            font-size: 0.84rem;
            text-align: center;
            overflow-wrap: anywhere;
        }}
        .latest-upload-empty {{
            min-height: 120px;
            display: grid;
            place-items: center;
            border: 1px dashed rgba(92, 168, 120, 0.35);
            border-radius: 8px;
            background: #FBFDFB;
        }}
        .chart-bars {{
            min-height: 180px;
            display: grid;
            grid-template-columns: repeat(7, minmax(0, 1fr));
            gap: 10px;
            align-items: end;
            padding-top: 12px;
        }}
        .chart-bar {{
            display: grid;
            gap: 6px;
            align-items: end;
            text-align: center;
            color: var(--nutri-muted);
            font-size: 0.78rem;
        }}
        .chart-bar i {{
            display: block;
            width: 100%;
            min-height: 12px;
            border-radius: 8px 8px 3px 3px;
            background: #CFE8D8;
        }}
        .chart-bar.today i {{
            background: var(--nutri-accent);
        }}
        .upload-box {{
            min-height: 150px;
            border: 1px dashed rgba(92, 168, 120, 0.45);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            background: #FBFDFB;
            color: var(--nutri-muted);
            margin: 12px 0;
            padding: 18px;
        }}
        .preview-meta {{
            display: flex;
            justify-content: space-between;
            gap: 10px;
            margin-top: 8px;
            color: var(--nutri-muted);
            font-size: 0.85rem;
        }}
        .input-like {{
            min-width: 92px;
            margin-top: 6px;
            padding: 9px 12px;
            border-radius: 8px;
            border: 1px solid var(--nutri-border);
            background: #fff;
            font-weight: 760;
            color: var(--nutri-text);
        }}
        .state-strip {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin: 10px 0 14px;
            width: 100%;
            max-width: 100%;
            min-width: 0;
        }}
        .state-item {{
            padding: 10px;
            border-radius: 8px;
            border: 1px solid var(--nutri-border);
            background: #fff;
            min-width: 0;
            overflow-wrap: anywhere;
        }}
        .state-item strong,
        .state-item span {{
            display: block;
        }}
        .state-item span {{
            color: var(--nutri-muted);
            font-size: 0.78rem;
            margin-top: 3px;
        }}
        .loading-line {{
            display: inline-block;
            width: 72px;
            height: 8px;
            border-radius: 999px;
            background: linear-gradient(90deg, #DDEFE3, var(--nutri-primary), #DDEFE3);
            background-size: 200% 100%;
            animation: nutri-loading 1.4s infinite linear;
        }}
        @keyframes nutri-loading {{
            from {{ background-position: 200% 0; }}
            to {{ background-position: -200% 0; }}
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
        div[data-testid="stElementContainer"][class*="st-key-bottom_nav_"],
        div[data-testid="stVerticalBlock"][class*="st-key-bottom_nav_container_"] {{
            display: none !important;
        }}
        .nav-item {{
            min-width: 54px;
            text-align: center;
            color: var(--nutri-muted);
            font-size: 0.78rem;
            text-decoration: none;
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
            grid-template-columns: minmax(0, 1fr);
            gap: 6px;
            width: 100%;
            max-width: 100%;
            min-width: 0;
            overflow-x: hidden;
            contain: inline-size;
        }}
        .desktop-table > * {{
            min-width: 0;
            max-width: 100%;
        }}
        .table-row {{
            display: grid;
            grid-template-columns:
                minmax(0, 1fr)
                minmax(0, 0.56fr)
                minmax(0, 0.72fr)
                minmax(0, 0.68fr)
                minmax(0, 2fr);
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border-bottom: 1px solid var(--nutri-border);
            font-size: 0.9rem;
            width: 100%;
            box-sizing: border-box;
            min-width: 0;
            max-width: 100%;
            overflow: hidden;
        }}
        .table-row > span {{
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .table-row > span:last-child {{
            white-space: normal;
            overflow-wrap: anywhere;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
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
                padding-top: 3.25rem;
                padding-left: 1rem;
                padding-right: 1rem;
                padding-bottom: 5rem;
            }}
            .desktop-nav {{
                display: none;
            }}
            div[data-testid="stElementContainer"][class*="st-key-desktop_nav_"],
            div[data-testid="stVerticalBlock"][class*="st-key-desktop_nav_container_"] {{
                display: none !important;
            }}
            .bottom-nav {{
                display: flex;
            }}
            div[data-testid="stVerticalBlock"][class*="st-key-bottom_nav_container_"] {{
                display: block !important;
                position: fixed !important;
                left: 12px !important;
                right: auto !important;
                width: calc(100vw - 24px) !important;
                bottom: 10px !important;
                z-index: 1000 !important;
                padding: 7px !important;
                box-sizing: border-box !important;
                border: 1px solid var(--nutri-border);
                border-radius: 12px;
                background: rgba(255, 255, 255, 0.96);
                box-shadow: 0 12px 30px rgba(31, 41, 51, 0.12);
                backdrop-filter: blur(12px);
            }}
            div[data-testid="stVerticalBlock"][class*="st-key-bottom_nav_container_"]
            div[data-testid="stHorizontalBlock"] {{
                display: grid !important;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 4px;
                align-items: stretch;
            }}
            div[data-testid="stVerticalBlock"][class*="st-key-bottom_nav_container_"]
            div[data-testid="column"] {{
                min-width: 0 !important;
                width: 100% !important;
                padding: 0 !important;
            }}
            div[data-testid="stElementContainer"][class*="st-key-mobile_nav_button_"] {{
                display: block !important;
                min-width: 0 !important;
            }}
            div[data-testid="stElementContainer"][class*="st-key-mobile_nav_button_"] button {{
                min-width: 0 !important;
                width: 100% !important;
                height: 42px !important;
                padding: 5px 2px !important;
                border-radius: 8px !important;
                font-size: 0.72rem !important;
                line-height: 1.05 !important;
                white-space: normal !important;
                overflow: hidden !important;
                text-overflow: clip !important;
            }}
            .desktop-work,
            .desktop-two-col,
            .desktop-metrics,
            .food-grid,
            .desktop-result-grid,
            .state-strip {{
                grid-template-columns: 1fr;
            }}
            .table-row {{
                grid-template-columns: 1fr;
            }}
            .table-row > span,
            .table-row > span:last-child {{
                white-space: normal;
                overflow: visible;
                text-overflow: clip;
                display: block;
                -webkit-line-clamp: initial;
            }}
            .main-title {{
                font-size: 1.75rem;
            }}
            .calorie-number {{
                font-size: 2rem;
            }}
            .latest-upload-card {{
                max-width: 100%;
            }}
            .latest-upload-figure {{
                width: 100%;
            }}
            .latest-upload-figure img {{
                max-height: 220px;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
