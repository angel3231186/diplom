"""
Общие стили для всех страниц приложения CourseFind.
"""

import streamlit as st


def inject_css():
    """Внедряет общий CSS во все страницы."""
    st.markdown(
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200">',
        unsafe_allow_html=True,
    )
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700&family=Inter:wght@300;400;500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

/* ── Base ── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background-color: var(--bg) !important;
    color: var(--text);
    font-family: 'Inter', sans-serif;
}

/* ── Кнопка сворачивания сайдбара ── */
/* ── Убираем лишние отступы контента ── */
[data-testid="block-container"],
.block-container,
[data-testid="stMainBlockContainer"] {
    padding-top: 2rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 100% !important;
}

[data-testid="stSidebarCollapseButton"] button {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    overflow: hidden !important;
    width: 2.2rem !important;
    height: 2.2rem !important;
    background: rgb(19, 23, 32) !important;
    border-radius: 0.75rem !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stSidebarCollapseButton"] button * {
    position: absolute !important;
    top: -9999px !important;
    left: -9999px !important;
    pointer-events: none !important;
}
[data-testid="stSidebarCollapseButton"] button::after {
    content: url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24'><path fill='%23999' d='M17.59 18L19 16.59 14.42 12 19 7.41 17.59 6l-6 6 6 6zM11 6l-6 6 6 6 1.41-1.41L7.83 12l4.58-4.59L11 6z'/></svg>") !important;
    display: block !important;
    line-height: 0 !important;
    flex-shrink: 0 !important;
}

/* ── Sidebar ── */
[data-testid="stSidebarNav"] {
    display: none !important;
}

[data-testid="stSidebar"] {
    background-color: #13131a !important;
    border-right: 1px solid rgba(255,255,255,0.07) !important;
}
[data-testid="stSidebar"] * {
    font-family: 'Inter', sans-serif;
    color: #f0f0f5 !important;
}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: #55556a !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    gap: 0;
    padding-left: 0 !important;
    margin-left: 0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:first-child {
    padding-left: 0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent;
    border: none;
    color: #55556a;
    font-family: 'Inter', sans-serif;
    font-weight: 400;
    font-size: 0.92rem;
    padding: 10px 24px;
    border-radius: 6px 6px 0 0;
    margin-bottom: 0;
    transition: color .2s ease;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover { color: #9d8fff; }
[data-testid="stTabs"] [aria-selected="true"] {
    color: #c0baff !important;
    background: transparent !important;
    font-weight: 600 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    background: linear-gradient(90deg, #7c6bff, #a594ff) !important;
    height: 2px !important;
    border-radius: 2px 2px 0 0 !important;
    transition: all .35s cubic-bezier(.4,0,.2,1) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none !important; }

/* ── Rating card container ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(135deg, #141414 0%, #0f0f18 100%) !important;
    border: 1px solid rgba(124,107,255,0.18) !important;
    border-radius: 14px !important;
    padding: 6px 10px !important;
    box-shadow: inset 3px 0 0 #7c6bff, 0 2px 12px rgba(0,0,0,0.3) !important;
    transition: box-shadow 0.2s ease !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(124,107,255,0.35) !important;
    box-shadow: inset 3px 0 0 #7c6bff, 0 4px 20px rgba(124,107,255,0.12) !important;
}
.rating-card-wrap [data-testid="stVerticalBlockBorderWrapper"],
.rating-card-wrap [data-testid="stVerticalBlock"] { gap: 0 !important; }
.rating-card-wrap [data-testid="stFeedback"] { justify-content: flex-start !important; padding: 0 4px !important; }
.rating-card-wrap [data-testid="stMarkdownContainer"] > div { margin-bottom: 0 !important; }

/* ── Invisible star click buttons ── */
[data-testid="stButton"] button:has(p:empty),
[data-testid="stButton"] button p:empty {
    opacity: 0 !important;
    height: 2.5rem !important;
    margin-top: -2.5rem !important;
    position: relative !important;
    z-index: 10 !important;
    background: transparent !important;
    border: none !important;
    cursor: pointer !important;
}

/* ── Custom star rating buttons ── */
.star-btn-wrap button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: rgba(251,191,36,0.25) !important;
    font-size: 1.4rem !important;
    padding: 0 !important;
    min-height: 32px !important;
    height: 32px !important;
    line-height: 1 !important;
    transition: color 0.12s, transform 0.12s, filter 0.12s !important;
}
.star-btn-wrap button:hover {
    color: #fbbf24 !important;
    transform: scale(1.3) !important;
    filter: drop-shadow(0 0 5px rgba(251,191,36,0.6)) !important;
    background: transparent !important;
}
.star-btn-wrap button p { font-size: 1.4rem !important; line-height: 1 !important; }

/* ── Feedback stars ── */
[data-testid="stFeedback"] {
    display: flex !important;
    gap: 4px !important;
    align-items: center !important;
    justify-content: center !important;
}
[data-testid="stFeedback"] button,
[data-testid="stFeedback"] [role="radio"],
[data-testid="stFeedback"] [role="button"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    min-width: unset !important;
    max-width: unset !important;
    box-shadow: none !important;
    width: 34px !important;
    height: 34px !important;
    min-height: unset !important;
    position: relative !important;
    flex-shrink: 0 !important;
    transition: transform 0.15s ease !important;
}
[data-testid="stFeedback"] button:hover,
[data-testid="stFeedback"] [role="radio"]:hover,
[data-testid="stFeedback"] [role="button"]:hover {
    transform: scale(1.25) !important;
    background: transparent !important;
}
[data-testid="stFeedback"] svg {
    width: 30px !important;
    height: 30px !important;
    color: rgba(251,191,36,0.25) !important;
    fill: rgba(251,191,36,0.25) !important;
    transition: fill 0.15s ease, color 0.15s ease, filter 0.15s ease !important;
}
[data-testid="stFeedback"] svg path {
    fill: rgba(251,191,36,0.25) !important;
    transition: fill 0.15s ease !important;
}
[data-testid="stFeedback"] [aria-checked="true"] svg,
[data-testid="stFeedback"] [aria-pressed="true"] svg {
    color: #fbbf24 !important;
    fill: #fbbf24 !important;
    filter: drop-shadow(0 0 6px rgba(251,191,36,0.55)) !important;
}
[data-testid="stFeedback"] [aria-checked="true"] svg path,
[data-testid="stFeedback"] [aria-pressed="true"] svg path {
    fill: #fbbf24 !important;
}
[data-testid="stFeedback"] button:hover svg path {
    fill: rgba(251,191,36,0.65) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: transparent;
    border: 1px solid rgba(255,255,255,0.12);
    color: #8888a0;
    border-radius: 12px;
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    font-weight: 400;
    transition: all .15s;
}
.stButton > button:hover {
    background: rgba(124,107,255,0.12);
    color: #c0baff;
    border-color: rgba(124,107,255,0.4);
}
.stButton > button:active {
    background: rgba(124,107,255,0.25) !important;
    border-color: rgba(124,107,255,0.6) !important;
    color: #a594ff !important;
}
[data-testid="baseButton-primary"],
[data-testid="stBaseButton-primary"] {
    background: #3d2fa0 !important;
    border-color: transparent !important;
    color: #e0d9ff !important;
    font-weight: 500 !important;
    border-radius: 12px !important;
    box-shadow: none !important;
    letter-spacing: 0.02em !important;
    transition: all .2s !important;
}
[data-testid="baseButton-primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
    background: #4e3dbf !important;
    transform: translateY(-1px) !important;
}
[data-testid="stFormSubmitButton"] > button {
    background: #3d2fa0 !important;
    border-color: transparent !important;
    color: #e0d9ff !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
    box-shadow: none !important;
    transition: all .2s !important;
}
[data-testid="stFormSubmitButton"] > button:hover {
    background: #4e3dbf !important;
    transform: translateY(-1px) !important;
}
[data-testid="baseButton-secondary"] {
    border-radius: 50px !important;
    border: 1px solid rgba(124,107,255,0.45) !important;
    background: rgba(124,107,255,0.06) !important;
    color: #c0baff !important;
    padding: 3px 14px !important;
    min-height: 0 !important;
    line-height: 1.7 !important;
    transition: background .15s, border-color .15s !important;
}
[data-testid="baseButton-secondary"]:hover {
    background: rgba(124,107,255,0.2) !important;
    border-color: rgba(124,107,255,0.85) !important;
    color: #fff !important;
}

/* ── Кнопка submit формы (красная по умолчанию) → фиолетовая ── */
[data-testid="stFormSubmitButton"] > button {
    background: #5a4fcf !important;
    border-color: transparent !important;
    color: #fff !important;
}
[data-testid="stFormSubmitButton"] > button:hover {
    background: #7c6bff !important;
}
/* ── Чекбокс: убрать красный ── */
[data-baseweb="checkbox"] [data-checked="true"] > div,
[data-baseweb="checkbox"] div[style*="background"] {
    background-color: #7c6bff !important;
    border-color: #7c6bff !important;
}
[data-baseweb="checkbox"] div {
    border-color: rgba(255,255,255,0.25) !important;
}
input[type="checkbox"] { accent-color: #7c6bff !important; }

/* ── Красные цвета → фиолетовые ── */
[data-testid="stAlert"][data-baseweb="notification"] {
    background: rgba(124,107,255,0.12) !important;
    border-color: rgba(124,107,255,0.35) !important;
}
[data-testid="stAlert"][data-baseweb="notification"] p,
[data-testid="stAlert"][data-baseweb="notification"] svg {
    color: #a594ff !important;
    fill: #a594ff !important;
}

/* ── Sidebar nav buttons ── */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid transparent !important;
    color: #8888a0 !important;
    border-radius: 8px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    font-size: 0.855rem !important;
    padding: 9px 10px !important;
    width: 100% !important;
    font-weight: 400 !important;
    letter-spacing: 0 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #1a1a24 !important;
    color: #f0f0f5 !important;
    border-color: transparent !important;
}
[data-testid="stSidebar"] [data-testid="baseButton-primary"],
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    background: rgba(124,107,255,0.1) !important;
    border: 1px solid rgba(124,107,255,0.25) !important;
    color: #a594ff !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] [data-testid="baseButton-secondary"],
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #94a3b8 !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] [data-testid="baseButton-secondary"]:hover,
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {
    background: rgba(255,255,255,0.04) !important;
    border-color: rgba(255,255,255,0.2) !important;
    color: #f0f0f5 !important;
}

/* ── Text input ── */
[data-testid="stTextInput"] input {
    background: #13131a !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 10px !important;
    color: #f0f0f5 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
    padding: 10px 16px !important;
    transition: border .2s !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: rgba(124,107,255,0.4) !important;
    background: #1a1a24 !important;
    box-shadow: none !important;
}
[data-testid="stTextInput"] input::placeholder { color: #55556a !important; }

/* ── Selectbox ── */
[data-baseweb="select"] > div {
    background: #13131a !important;
    border-color: rgba(255,255,255,0.07) !important;
    border-radius: 8px !important;
    color: #8888a0 !important;
}
[data-baseweb="select"] > div:focus-within {
    border-color: rgba(124,107,255,0.4) !important;
}

/* ── Slider ── */
[data-testid="stSlider"] [data-testid="stThumbValue"] { color: #a594ff !important; }
[data-testid="stSlider"] [role="slider"] { background: #7c6bff !important; }

/* ── Progress ── */
[data-testid="stProgressBar"] > div { background: #1a1a24 !important; border-radius: 4px; }
[data-testid="stProgressBar"] > div > div { background: #7c6bff !important; border-radius: 4px; }

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 14px 16px !important;
}
[data-testid="stMetricLabel"] { color: #55556a !important; font-size: 0.75rem !important; }
[data-testid="stMetricValue"] { color: #f0f0f5 !important; font-size: 1.4rem !important; font-weight: 700 !important; font-family: 'Syne', sans-serif !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 8px;
}
[data-testid="stExpander"] summary { color: #8888a0; font-size: 0.85rem; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 8px;
    overflow: hidden;
}

/* ── Divider ── */
hr { border-color: rgba(255,255,255,0.07) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 2px; }

/* ══════════════════════════════════════════════════
   LOGO & PROFILE IN SIDEBAR
══════════════════════════════════════════════════ */
.sb-logo {
    font-family: 'Syne', sans-serif;
    font-size: 1.2rem;
    font-weight: 700;
    color: #f0f0f5;
    letter-spacing: -0.03em;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0 12px;
}
.sb-logo-dot {
    width: 8px; height: 8px;
    background: #7c6bff;
    border-radius: 50%;
    box-shadow: 0 0 10px #7c6bff;
    display: inline-block;
}
.sb-profile {
    background: #1a1a24;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 12px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    cursor: pointer;
    transition: background .15s;
}
.sb-profile:hover { background: #1f1f2e; border-color: rgba(255,255,255,0.12); }
.sb-avatar {
    width: 34px; height: 34px;
    border-radius: 9px;
    background: linear-gradient(135deg, #7c6bff, #b06bff);
    display: flex; align-items: center; justify-content: center;
    font-family: 'Syne', sans-serif;
    font-size: 13px; font-weight: 700;
    color: #fff;
    flex-shrink: 0;
}
.sb-name {
    font-size: 0.82rem;
    font-weight: 500;
    color: #f0f0f5;
    line-height: 1.2;
}
.sb-role {
    font-size: 0.7rem;
    color: #55556a;
    margin-top: 1px;
}
.sb-nav-label {
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: #3a3a52;
    padding: 0 4px;
    margin: 16px 0 4px;
    font-family: 'Inter', sans-serif;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding-bottom: 6px;
}

/* ── Nav кнопки сайдбара ── */
[data-testid="stSidebar"] button {
    justify-content: flex-start !important;
    padding: 7px 10px !important;
    border-radius: 10px !important;
    border: none !important;
    margin-bottom: 2px !important;
    box-shadow: none !important;
    min-height: 0 !important;
    gap: 0 !important;
}
[data-testid="stSidebar"] button p {
    font-size: 0.875rem !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 400 !important;
    text-align: left !important;
    color: inherit !important;
}
[data-testid="stSidebar"] button[kind="secondary"] {
    background: rgba(255,255,255,0.04) !important;
    color: #8888a0 !important;
}
[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.08) !important;
    color: #c0c0d8 !important;
}
[data-testid="stSidebar"] button[kind="primary"] {
    background: rgba(108,99,255,0.18) !important;
    color: #c0b8ff !important;
}
[data-testid="stSidebar"] button[kind="primary"] p {
    font-weight: 500 !important;
    color: #c0b8ff !important;
}

.sb-footer-stats {
    display: flex;
    gap: 8px;
    margin-top: 4px;
}
.sb-stat-mini {
    flex: 1;
    background: #1a1a24;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 8px;
    padding: 8px;
    text-align: center;
}
.sb-stat-val {
    font-family: 'Syne', sans-serif;
    font-size: 0.88rem;
    font-weight: 700;
    color: #f0f0f5;
}
.sb-stat-lbl {
    font-size: 0.6rem;
    color: #55556a;
    margin-top: 2px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ══════════════════════════════════════════════════
   AUTH & ONBOARDING
══════════════════════════════════════════════════ */
.auth-wrap { max-width: 440px; margin: 60px auto 0; }
.auth-logo {
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem;
    font-weight: 700;
    letter-spacing: -0.04em;
    color: #f0f0f5;
    margin-bottom: 4px;
    display: flex; align-items: center; gap: 8px;
}
.auth-logo-dot { width: 8px; height: 8px; background: #7c6bff; border-radius: 50%; box-shadow: 0 0 10px #7c6bff; display: inline-block; }
.auth-sub { font-size: 0.85rem; color: #55556a; margin-bottom: 28px; }
.auth-card {
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 28px 28px 24px;
}
.auth-card-title {
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    color: #f0f0f5;
    margin-bottom: 18px;
    letter-spacing: -0.02em;
}
.onb-wrap { max-width: 580px; margin: 48px auto 0; }
.onb-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: #f0f0f5;
    letter-spacing: -0.04em;
    margin-bottom: 6px;
}
.onb-sub { font-size: 0.85rem; color: #55556a; margin-bottom: 24px; }
.onb-card {
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 28px 28px 24px;
}
.onb-step-label {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #7c6bff;
    margin-bottom: 6px;
}

/* ══════════════════════════════════════════════════
   PAGE HEADER
══════════════════════════════════════════════════ */
.page-header {
    padding: 20px 0 28px;
    margin-bottom: 12px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
}
.page-header-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: #f0f0f5;
    letter-spacing: -0.03em;
    margin-bottom: 8px;
}
.page-header-sub { font-size: 0.82rem; color: #8888a0; line-height: 1.5; }

/* Section title */
.section-title {
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    color: #f0f0f5;
    margin: 24px 0 14px;
    letter-spacing: -0.02em;
}
.section-label {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #55556a;
    margin: 20px 0 10px;
}

/* ══════════════════════════════════════════════════
   BADGES & CHIPS
══════════════════════════════════════════════════ */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-right: 4px;
    margin-bottom: 3px;
}
.b-stepik   { background: rgba(99,179,237,0.12); color: #63b3ed; }
.b-udemy    { background: rgba(167,139,250,0.12); color: #a78bfa; }
.b-coursera { background: rgba(56,189,248,0.12); color: #38bdf8; }
.b-openedu  { background: rgba(52,211,153,0.12); color: #34d399; }
.b-free     { background: rgba(61,214,140,0.08); color: #3dd68c; }
.b-paid     { background: rgba(255,255,255,0.06); color: #8888a0; }
.b-beg      { background: rgba(52,211,153,0.08); color: #86efac; }
.b-int      { background: rgba(251,191,36,0.08); color: #fcd34d; }
.b-adv      { background: rgba(252,165,165,0.08); color: #fca5a5; }

.rating-high { color: #3dd68c; font-weight: 600; }
.rating-mid  { color: #fbbf24; font-weight: 600; }
.rating-low  { color: #f87171; font-weight: 600; }

/* Quick chips */
.qchip {
    display: inline-block;
    padding: 5px 12px;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 20px;
    font-size: 0.75rem;
    color: #8888a0;
    cursor: pointer;
    transition: all .15s;
    margin: 3px 4px 3px 0;
    background: transparent;
}
.qchip:hover {
    border-color: rgba(124,107,255,0.4);
    color: #a594ff;
    background: rgba(124,107,255,0.08);
}

/* ══════════════════════════════════════════════════
   STAT CARDS (inline stats bar)
══════════════════════════════════════════════════ */
.stat-bar {
    display: flex;
    gap: 16px;
    margin-top: 32px;
    margin-bottom: 24px;
}
.stat-card-new {
    flex: 1;
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 22px 20px;
    transition: border .2s;
}
.stat-card-new:hover { border-color: rgba(255,255,255,0.12); }
.stat-val-new {
    font-family: 'Syne', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: #f0f0f5;
    letter-spacing: -0.02em;
}
.stat-lbl-new {
    font-size: 0.65rem;
    color: #55556a;
    margin-top: 3px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* ══════════════════════════════════════════════════
   FEATURE CARDS
══════════════════════════════════════════════════ */
.feature-grid-new {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 40px;
}
.feature-card-new {
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 24px 22px;
    transition: all .2s;
}
.feature-card-new:hover {
    border-color: rgba(255,255,255,0.12);
    background: #1a1a24;
}
.feature-icon-new {
    width: 36px; height: 36px;
    border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 12px;
    font-size: 1rem;
}
.fi-purple { background: rgba(124,107,255,0.15); }
.fi-green  { background: rgba(61,214,140,0.12); }
.fi-blue   { background: rgba(99,179,237,0.12); }
.feature-title-new {
    font-family: 'Syne', sans-serif;
    font-size: 0.88rem;
    font-weight: 600;
    color: #f0f0f5;
    margin-bottom: 5px;
}
.feature-desc-new {
    font-size: 0.75rem;
    color: #8888a0;
    line-height: 1.6;
}

/* ══════════════════════════════════════════════════
   COURSE CARDS (result cards)
══════════════════════════════════════════════════ */
.course-card-new {
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    overflow: hidden;
    transition: all .2s;
    margin-bottom: 2px;
}
.course-card-new:hover {
    border-color: rgba(255,255,255,0.12);
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.course-thumb {
    height: 112px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2.6rem;
}
.ct-purple { background: linear-gradient(135deg, #1a1430, #2d2060); }
.ct-green  { background: linear-gradient(135deg, #0d2018, #1a3d2b); }
.ct-blue   { background: linear-gradient(135deg, #0d1a2e, #1a2d4a); }
.ct-orange { background: linear-gradient(135deg, #2e1a0d, #4a2d1a); }
.ct-gray   { background: linear-gradient(135deg, #1a1a1a, #2a2a2a); }
.course-card-new {
    display: flex !important;
    flex-direction: column !important;
}
.course-body-new {
    padding: 16px 16px 14px;
    height: 150px;
    min-height: 150px;
    max-height: 150px;
    overflow: hidden;
    flex: none;
}
.course-tag-new {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #a594ff;
    margin-bottom: 6px;
}
.course-title-new {
    font-size: 1rem;
    font-weight: 600;
    color: #f0f0f5;
    margin-bottom: 6px;
    line-height: 1.35;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.course-title-new a { text-decoration: none; color: inherit; }
.course-title-new a:hover { color: #a594ff; }
.course-meta-new {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.76rem;
    color: #7070a0;
}
.course-free-badge {
    font-size: 0.62rem;
    font-weight: 600;
    color: #3dd68c;
    background: rgba(61,214,140,0.10);
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: auto;
    font-size: 0.68rem;
}
.course-price-badge {
    font-size: 0.68rem;
    font-weight: 600;
    color: #8888a0;
    margin-left: auto;
}

/* Section header row */
.section-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
}
.section-header-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.95rem;
    font-weight: 600;
    color: #f0f0f5;
}
.section-header-count {
    font-size: 0.72rem;
    color: #55556a;
    background: #1a1a24;
    padding: 2px 8px;
    border-radius: 10px;
}

/* ══════════════════════════════════════════════════
   COMPACT CATALOG CARDS
══════════════════════════════════════════════════ */
.compact-card {
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 14px 14px 10px;
    height: 100%;
    transition: all .2s;
}
.compact-card:hover {
    border-color: rgba(124,107,255,0.25);
    background: #1a1a24;
    box-shadow: 0 2px 14px rgba(124,107,255,0.1);
}
.cc-title {
    font-size: 0.82rem;
    font-weight: 500;
    color: #f0f0f5;
    margin-bottom: 4px;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: 2.3em;
}
.cc-title a { text-decoration: none; color: inherit; }
.cc-title a:hover { color: #a594ff; }
.cc-org { font-size: 0.7rem; color: #55556a; margin-bottom: 8px; }
.cc-meta { font-size: 0.72rem; color: #55556a; }

/* ══════════════════════════════════════════════════
   RESULTS SUMMARY
══════════════════════════════════════════════════ */
.results-summary {
    font-size: 0.8rem;
    color: #55556a;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    margin-bottom: 18px;
}
.results-summary strong { color: #8888a0; }

/* ══════════════════════════════════════════════════
   PROFILE / ACCOUNT PANEL
══════════════════════════════════════════════════ */
.profile-hero {
    background: linear-gradient(135deg, #0f0e1a 0%, #1a1430 50%, #0f0e1a 100%);
    border: 1px solid rgba(124,107,255,0.2);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.profile-hero::before {
    content: '';
    position: absolute;
    top: -50px; right: -50px;
    width: 180px; height: 180px;
    background: radial-gradient(circle, rgba(124,107,255,0.15), transparent 70%);
    border-radius: 50%;
}
.profile-avatar {
    width: 64px; height: 64px;
    border-radius: 14px;
    background: linear-gradient(135deg, #7c6bff, #b06bff);
    display: flex; align-items: center; justify-content: center;
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem; font-weight: 700; color: #fff;
    flex-shrink: 0;
}
.profile-name {
    font-family: 'Syne', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: #f0f0f5;
    letter-spacing: -0.03em;
    line-height: 1.2;
    margin-bottom: 4px;
}
.profile-meta { font-size: 0.78rem; color: #55556a; }
.profile-meta strong { color: #8888a0; }

.interest-tag {
    display: inline-block;
    background: rgba(124,107,255,0.1);
    border: 1px solid rgba(124,107,255,0.25);
    color: #a594ff;
    font-size: 0.7rem;
    font-weight: 500;
    padding: 3px 9px;
    border-radius: 20px;
    margin: 2px 3px 2px 0;
}
.level-tag { display: inline-block; font-size: 0.7rem; font-weight: 600; padding: 3px 9px; border-radius: 20px; margin-right: 5px; }
.level-beg { background: rgba(52,211,153,0.08); color: #86efac; }
.level-int { background: rgba(251,191,36,0.08); color: #fcd34d; }
.level-adv { background: rgba(252,165,165,0.08); color: #fca5a5; }

.stat-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin: 16px 0;
}
.stat-card {
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 16px 14px 14px;
    text-align: center;
    transition: border .2s;
}
.stat-card:hover { border-color: rgba(124,107,255,0.2); }
.stat-icon { font-size: 1.2rem; margin-bottom: 6px; }
.stat-value {
    font-family: 'Syne', sans-serif;
    font-size: 1.7rem;
    font-weight: 700;
    color: #f0f0f5;
    line-height: 1.1;
    letter-spacing: -0.03em;
}
.stat-label { font-size: 0.65rem; color: #55556a; margin-top: 3px; text-transform: uppercase; letter-spacing: 0.06em; }

.settings-panel {
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 12px;
    transition: border .2s;
}
.settings-panel:hover { border-color: rgba(255,255,255,0.1); }
.settings-panel-title {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #55556a;
    margin-bottom: 14px;
}
.profile-section-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.95rem;
    font-weight: 600;
    color: #f0f0f5;
    letter-spacing: -0.02em;
    margin: 0 0 12px 0;
    display: flex; align-items: center; gap: 8px;
}
.profile-section-title span {
    font-size: 0.68rem;
    font-weight: 400;
    color: #55556a;
    background: #1a1a24;
    padding: 2px 8px;
    border-radius: 10px;
    font-family: 'Inter', sans-serif;
    letter-spacing: 0;
}

.fav-item {
    background: #0c0c0f;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 5px;
    transition: border .15s;
}
.fav-item:hover { border-color: rgba(124,107,255,0.2); }
.fav-item-title { font-size: 0.83rem; font-weight: 500; color: #f0f0f5; margin-bottom: 3px; line-height: 1.4; }
.fav-item-title a { text-decoration: none; color: inherit; }
.fav-item-title a:hover { color: #a594ff; }
.fav-item-meta { font-size: 0.7rem; color: #55556a; }

.search-chip {
    display: inline-block;
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07);
    color: #8888a0;
    font-size: 0.75rem;
    font-weight: 400;
    padding: 4px 11px;
    border-radius: 20px;
    margin: 2px 3px 2px 0;
    cursor: pointer;
    transition: all .15s;
}
.search-chip:hover { border-color: rgba(124,107,255,0.4); color: #a594ff; }

.interest-bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.interest-bar-label { font-size: 0.78rem; color: #8888a0; min-width: 160px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.interest-bar-track { flex: 1; background: #1a1a24; border-radius: 3px; height: 5px; overflow: hidden; }
.interest-bar-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #7c6bff, #b06bff); }
.interest-bar-val { font-size: 0.68rem; color: #55556a; min-width: 28px; text-align: right; }

.profile-divider { border: none; border-top: 1px solid rgba(255,255,255,0.06); margin: 14px 0; }
/* ── Загрузчик файла ── */
[data-testid="stFileUploaderDropzoneInstructions"] div:last-child small { display: none !important; }
[data-testid="stFileUploader"] > label { display: none !important; }
[data-testid="stFileUploader"] button { font-size: 0 !important; min-height: 36px; }
[data-testid="stFileUploader"] button::after { content: "Загрузить фото"; font-size: 0.82rem; font-family: 'Inter', sans-serif; }
[data-testid="stFileUploaderDropzoneInstructions"] div:first-child { font-size: 0.82rem !important; color: #55556a !important; }
[data-testid="stFileUploaderDropzoneInstructions"] svg { display: none !important; }

.account-panel {
    background: #0f0f17;
    border: 1px solid rgba(124,107,255,0.2);
    border-radius: 16px;
    padding: 24px 28px 20px;
    margin-bottom: 24px;
}

/* ══════════════════════════════════════════════════
   CHART PANELS
══════════════════════════════════════════════════ */
.chart-panel {
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 18px 18px 12px;
}
.chart-panel-title {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #55556a;
    margin-bottom: 12px;
}

/* ══════════════════════════════════════════════════
   METRIC CARDS (evaluation page)
══════════════════════════════════════════════════ */
.metric-desc-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
.metric-desc-card { background: #13131a; border: 1px solid rgba(255,255,255,0.07); border-radius: 10px; padding: 12px 14px; }
.metric-desc-name { font-size: 0.75rem; font-weight: 600; color: #a594ff; margin-bottom: 4px; }
.metric-desc-text { font-size: 0.7rem; color: #55556a; line-height: 1.5; }

/* ══════════════════════════════════════════════════
   EMPTY STATE
══════════════════════════════════════════════════ */
.empty-state {
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 40px 28px;
    text-align: center;
    margin-top: 16px;
}
.empty-state-title { font-family: 'Syne', sans-serif; font-size: 1.05rem; font-weight: 600; color: #f0f0f5; margin-bottom: 8px; }
.empty-state-text { font-size: 0.82rem; color: #55556a; line-height: 1.6; max-width: 340px; margin: 0 auto 18px; }
.empty-state-steps { display: inline-flex; flex-direction: column; gap: 8px; text-align: left; background: #0c0c0f; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 14px 18px; }
.empty-state-step { font-size: 0.78rem; color: #55556a; display: flex; align-items: center; gap: 10px; }
.empty-state-step-num { width: 18px; height: 18px; border-radius: 50%; background: rgba(124,107,255,0.12); border: 1px solid rgba(124,107,255,0.3); color: #a594ff; font-size: 0.65rem; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }

/* ══════════════════════════════════════════════════
   BACK BUTTON
══════════════════════════════════════════════════ */
.back-btn-wrap { display: inline-block; margin-bottom: 4px; }
.back-btn-wrap > div > button {
    background: transparent !important;
    border: none !important;
    color: #55556a !important;
    font-size: 0.82rem !important;
    padding: 4px 8px 4px 2px !important;
    border-radius: 6px !important;
    transition: color .15s !important;
}
.back-btn-wrap > div > button:hover { color: #8888a0 !important; background: transparent !important; }

/* ── Кнопки-бейджи в "Продолжить" ── */
.sc-badge-btn button {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #cbd5e1 !important;
    border-radius: 50px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 6px 18px !important;
    min-height: unset !important;
    height: auto !important;
    line-height: 1.4 !important;
    letter-spacing: 0.02em !important;
    transition: all .15s !important;
}
.sc-badge-btn button:hover {
    background: rgba(124,107,255,0.2) !important;
    border-color: rgba(124,107,255,0.5) !important;
    color: #c0baff !important;
}

/* ── Refresh button (Обновить подборку) ── */
.refresh-btn-wrap button {
    background: rgba(124,107,255,0.08) !important;
    border: 1px solid rgba(124,107,255,0.3) !important;
    color: #a594ff !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    transition: all .2s !important;
}
.refresh-btn-wrap button:hover {
    background: rgba(124,107,255,0.16) !important;
    border-color: rgba(124,107,255,0.55) !important;
    color: #c0baff !important;
}

/* ══════════════════════════════════════════════════
   FOOTER
══════════════════════════════════════════════════ */
.app-footer {
    margin-top: 48px;
    padding: 20px 0 14px;
    border-top: 1px solid rgba(255,255,255,0.06);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
}
.footer-brand { font-family: 'Syne', sans-serif; font-size: 0.8rem; font-weight: 700; color: #55556a; }
.footer-meta { font-size: 0.7rem; color: #55556a; }

/* ══════════════════════════════════════════════════
   SIDEBAR LABEL (legacy support)
══════════════════════════════════════════════════ */
.sidebar-label {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #55556a;
    margin: 14px 0 6px;
}

/* ── Section header (catalog) ── */
.section-header {
    font-family: 'Syne', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: #f0f0f5;
    margin: 32px 0 12px 0;
    letter-spacing: -0.03em;
    display: flex;
    align-items: center;
    gap: 12px;
}

/* Hide dataset hidden nav button */
[data-testid="stTooltipHoverTarget"][title="guide_nav_dataset"] { display: none !important; }

button[title="nav-arrow"] p,
[data-testid="stButton"] button[title="nav-arrow"] p {
    font-size: 1.4rem !important;
    margin: 0 !important;
    line-height: 1 !important;
    white-space: nowrap !important;
}
button[title="nav-arrow"]:hover {
    color: #a594ff !important;
    background: transparent !important;
    border: none !important;
}

.section-count {
    font-size: 0.72rem;
    font-weight: 400;
    color: #55556a;
    background: #1a1a24;
    padding: 2px 8px;
    border-radius: 10px;
    font-family: 'Inter', sans-serif;
}



/* ── st.feedback star widget styling (filter approach) ── */
[data-testid="stFeedback"] button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 2px 2px !important;
    min-height: 0 !important;
}
[data-testid="stFeedback"] svg {
    width: 22px !important;
    height: 22px !important;
    filter: sepia(1) saturate(3) hue-rotate(8deg) brightness(0.75) !important;
    transition: filter 0.15s, transform 0.15s !important;
}
[data-testid="stFeedback"] button:hover svg {
    filter: sepia(1) saturate(8) hue-rotate(8deg) brightness(1.3) drop-shadow(0 0 6px rgba(251,191,36,0.7)) !important;
    transform: scale(1.18) !important;
}


/* ── Claim XP button ── */
.claim-xp-btn button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #7c6bff 0%, #a78bfa 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.02em !important;
    border-radius: 12px !important;
    padding: 10px 0 !important;
    box-shadow: 0 0 18px rgba(124,107,255,0.55), 0 4px 12px rgba(0,0,0,0.3) !important;
    transition: all 0.2s !important;
    animation: claimPulse 2s ease-in-out infinite !important;
}
.claim-xp-btn button[data-testid="baseButton-primary"]:hover {
    background: linear-gradient(135deg, #9b8dff 0%, #c4b5fd 100%) !important;
    box-shadow: 0 0 28px rgba(124,107,255,0.8), 0 6px 16px rgba(0,0,0,0.35) !important;
    transform: translateY(-1px) !important;
}
@keyframes claimPulse {
    0%, 100% { box-shadow: 0 0 18px rgba(124,107,255,0.55), 0 4px 12px rgba(0,0,0,0.3); }
    50%       { box-shadow: 0 0 30px rgba(124,107,255,0.85), 0 4px 12px rgba(0,0,0,0.3); }
}


/* ── Catalog: org, students, count badge ── */
.course-org-new {
    font-size: 0.65rem;
    color: #6060a0;
    margin-bottom: 5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.course-students {
    font-size: 0.65rem;
    color: #55556a;
    white-space: nowrap;
}
.cat-count-badge {
    display: inline-block;
    font-size: 0.75rem;
    color: #a594ff;
    background: rgba(165,148,255,0.08);
    border: 1px solid rgba(165,148,255,0.18);
    border-radius: 8px;
    padding: 5px 14px;
    margin: 6px 0 12px;
}

/* ── Catalog filter segmented controls ── */
[data-testid="stSegmentedControl"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    padding: 3px !important;
}
/* Inactive pill */
[data-testid="stSegmentedControl"] label {
    border-radius: 8px !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    color: #8080b0 !important;
    padding: 6px 16px !important;
    transition: background 0.2s ease, color 0.2s ease !important;
    cursor: pointer !important;
    border: none !important;
    background: transparent !important;
}
[data-testid="stSegmentedControl"] label:hover {
    color: #c4b5fd !important;
    background: rgba(165,148,255,0.1) !important;
}
/* Active pill */
[data-testid="stSegmentedControl"] label:has(input:checked) {
    background: linear-gradient(135deg, #7c6bff 0%, #a78bfa 100%) !important;
    color: #fff !important;
    box-shadow: 0 2px 12px rgba(124,107,255,0.4) !important;
    font-weight: 600 !important;
}
[data-testid="stSegmentedControl"] label:has(input:checked) p,
[data-testid="stSegmentedControl"] label:has(input:checked) span {
    color: #fff !important;
}

/* ── Done badge (replaces disabled button) ── */
/* Remove stMarkdown extra padding so badge aligns with buttons */
.element-container:has(.cc-done-badge) {
    display: flex !important;
    align-items: center !important;
}
.element-container:has(.cc-done-badge) [data-testid="stMarkdown"] {
    width: 100% !important;
}
.cc-done-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 30px;
    font-size: 0.72rem;
    font-weight: 600;
    color: #666677;
    background: rgba(80,80,100,0.18);
    border: 1px solid rgba(100,100,130,0.22);
    border-radius: 7px;
    white-space: nowrap;
    letter-spacing: 0.02em;
    width: 100%;
    box-sizing: border-box;
}

/* ── Compact catalog card buttons ── */
/* Use div:has() without relying on .element-container class name */

/* Fixed-height button row */
div:has(> [data-testid="stMarkdown"] .cc-btns) + div [data-testid="stHorizontalBlock"],
div:has(.cc-btns) + div [data-testid="stHorizontalBlock"] {
    min-height: 38px !important;
    max-height: 38px !important;
    overflow: hidden !important;
}

/* All buttons base */
div:has(.cc-btns) ~ div [data-testid="stHorizontalBlock"] button {
    padding: 0 8px !important;
    min-height: 30px !important;
    height: 30px !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    border-radius: 7px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    line-height: 1 !important;
    letter-spacing: 0.02em !important;
    transition: all 0.15s ease !important;
}
div:has(.cc-btns) ~ div [data-testid="stHorizontalBlock"] button p {
    font-size: 0.68rem !important;
    margin: 0 !important;
    white-space: nowrap !important;
    line-height: 1 !important;
}

/* Secondary (Сохр.) — ghost */
div:has(.cc-btns) ~ div [data-testid="stHorizontalBlock"] [data-testid="baseButton-secondary"] {
    background: transparent !important;
    border: 1px solid rgba(165,148,255,0.4) !important;
    color: #a594ff !important;
    box-shadow: none !important;
}
div:has(.cc-btns) ~ div [data-testid="stHorizontalBlock"] [data-testid="baseButton-secondary"]:hover {
    border-color: rgba(165,148,255,0.7) !important;
    background: rgba(165,148,255,0.08) !important;
}

/* Primary (Начать) — filled purple */
div:has(.cc-btns) ~ div [data-testid="stHorizontalBlock"] [data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #7c6bff, #a78bfa) !important;
    border: none !important;
    color: #fff !important;
    box-shadow: 0 2px 8px rgba(124,107,255,0.3) !important;
}
div:has(.cc-btns) ~ div [data-testid="stHorizontalBlock"] [data-testid="baseButton-primary"]:hover {
    box-shadow: 0 3px 12px rgba(124,107,255,0.5) !important;
    transform: translateY(-1px) !important;
}

</style>
""", unsafe_allow_html=True)


