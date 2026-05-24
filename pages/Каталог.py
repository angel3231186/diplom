import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd

import main as _main
from personalization import profile_manager
from styles import inject_css, inject_chat_widget


st.set_page_config(
    page_title="Каталог — IT Курсы",
    page_icon="★",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""<style>[data-testid="stSidebarNav"]{display:none!important}</style>""", unsafe_allow_html=True)

inject_css()
inject_chat_widget(user_id=st.session_state.get("username", "default"))

st.markdown("""
<style>
/* ── Hero каталога ── */
.catalog-hero {
    padding: 32px 0 24px 0;
    border-bottom: 1px solid #1e1e2e;
    margin-bottom: 8px;
}
.catalog-hero h1 {
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: #f1f5f9;
    margin-bottom: 6px;
}
.catalog-hero p { color: #64748b; font-size: 0.95rem; margin: 0; }

</style>
""", unsafe_allow_html=True)

@st.cache_resource(show_spinner="Загружаем данные...")
def load_catalog():
    df = _main.load_data(_main.DATA_PATH)
    df = _main.add_bayes(df)
    return df

df = load_catalog()

USER_ID = "web_user"

for key, default in [
    ("active_section", "all"),
    ("cat_filter",     "all"),
]:
    if key not in st.session_state:
        st.session_state[key] = default

_SOURCE_CLS = {"stepik": "b-stepik", "udemy": "b-udemy",
               "coursera": "b-coursera", "openedu": "b-openedu"}
_DIFF_CLS   = {"Beginner": "b-beg", "Intermediate": "b-int", "Advanced": "b-adv"}
_DIFF_RU    = {"Beginner": "Начинающий", "Intermediate": "Средний", "Advanced": "Продвинутый"}


def _badge(text: str, cls: str) -> str:
    return f'<span class="badge {cls}">{text}</span>'


def _rating_html(r: float) -> str:
    cls = "cc-rating-high" if r >= 4.7 else ("cc-rating-mid" if r >= 4.3 else "cc-rating-low")
    return f'<span class="{cls}">★ {r:.2f}</span>'


def render_compact_card(row, card_key: str):
    title    = str(row.get("title",    "—"))
    url      = str(row.get("url",      "") or "")
    src      = str(row.get("source",   "")).lower()
    diff     = str(row.get("difficulty","—"))
    org      = str(row.get("organization", "") or "")
    is_free  = int(row.get("is_free",  0)  or 0)
    price    = float(row.get("price",  0)  or 0)
    lang     = str(row.get("language", "—"))
    dur      = str(row.get("duration_category", "—"))
    r        = float(row.get("weighted_rating", 0) or 0)
    students = int(row.get("students_count", 0) or 0)

    price_str  = "Бесплатно" if (is_free == 1 or price == 0) else f"{int(price):,} тг"
    lang_str   = "RU" if lang == "ru" else ("EN" if lang == "en" else lang.upper())
    src_cls    = _SOURCE_CLS.get(src, "b-paid")
    diff_cls   = _DIFF_CLS.get(diff, "b-paid")
    price_cls  = "b-free" if (is_free == 1 or price == 0) else "b-paid"
    title_html = f'<a href="{url}" target="_blank">{title}</a>' if url else title
    org_html   = f'<div class="cc-org">{org}</div>' if org else '<div class="cc-org"> </div>'
    stu_html   = f' · <strong>{students:,}</strong>' if students > 0 else ""

    st.markdown(f"""
    <div class="compact-card">
      <div class="cc-badges">
        {_badge(src.capitalize() or "?", src_cls)}
        {_badge(diff, diff_cls)}
        {_badge(price_str, price_cls)}
      </div>
      <div class="cc-title">{title_html}</div>
      {org_html}
      <div class="cc-meta">
        {_rating_html(r)}&nbsp;&nbsp;
        <span>{lang_str} · {dur}{stu_html}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("👍 Нравится", key=f"like_cat_{card_key}"):
            profile_manager.track_like(USER_ID, row.to_dict())
            st.toast("Добавлено в избранное")
    with cb2:
        if st.button("🔖 Сохранить", key=f"save_cat_{card_key}"):
            profile_manager.track_save(USER_ID, row.to_dict())
            st.toast("Сохранено в список для изучения")


def render_section(title: str, section_df: pd.DataFrame,
                   section_key: str, max_cols: int = 5):
    count = len(section_df)
    st.markdown(
        f'<div class="section-header">'
        f'{title}'
        f'<span class="section-count">{count} курсов</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    top = section_df.head(max_cols)
    cols = st.columns(max_cols)
    for i, (_, row) in enumerate(top.iterrows()):
        with cols[i]:
            render_compact_card(row, f"{section_key}_{i}")

    btn_col, _ = st.columns([2, 6])
    with btn_col:
        if st.button(f"Показать все → {title}", key=f"expand_{section_key}"):
            st.session_state.active_section = section_key
            st.rerun()


def apply_base_filters(source, language, difficulty, price_filter, sort_by) -> pd.DataFrame:
    result = df.copy()

    if source != "all":
        result = result[result["source"] == source]
    if language != "all":
        result = result[result["language"] == language]
    if difficulty != "any":
        result = result[result["difficulty"] == difficulty]
    if price_filter == "free":
        result = result[result["is_free"] == 1]
    elif price_filter == "paid":
        result = result[result["is_free"] == 0]

    if sort_by == "rating":
        result = result.sort_values("weighted_rating", ascending=False)
    elif sort_by == "popularity":
        result = result.sort_values("students_count", ascending=False)
    else:
        result = result.sort_values("hybrid_score", ascending=False)

    return result


with st.sidebar:
    st.markdown("## CourseFind")
    st.caption("Каталог IT-курсов")
    st.divider()

    st.page_link("app.py", label="Поиск и рекомендации", icon="🔍")
    st.divider()

    st.markdown('<div class="sidebar-label">Фильтры</div>', unsafe_allow_html=True)

    sort_by = st.selectbox(
        "Сортировка",
        ["hybrid", "rating", "popularity"],
        format_func=lambda x: {
            "hybrid": "По качеству", "rating": "По рейтингу", "popularity": "По популярности"
        }[x],
    )

    language = st.selectbox(
        "Язык", ["all", "ru", "en"],
        format_func=lambda x: {"all": "Все языки", "ru": "Русский", "en": "English"}[x],
    )

    difficulty = st.selectbox(
        "Уровень", ["any", "Beginner", "Intermediate", "Advanced"],
        format_func=lambda x: {
            "any": "Любой", "Beginner": "Начинающий",
            "Intermediate": "Средний", "Advanced": "Продвинутый",
        }[x],
    )

    price_filter = st.selectbox(
        "Цена", ["any", "free", "paid"],
        format_func=lambda x: {"any": "Любая", "free": "Бесплатно", "paid": "Платные"}[x],
    )

    source_opts = ["all"] + sorted(df["source"].dropna().unique().tolist())
    source = st.selectbox(
        "Платформа", source_opts,
        format_func=lambda x: "Все платформы" if x == "all" else x.capitalize(),
    )

    st.divider()

    st.markdown('<div class="sidebar-label">Разделы</div>', unsafe_allow_html=True)

    sections = sorted(df["top_category"].dropna().unique().tolist())
    if st.button("Все разделы", key="nav_all",
                 type="primary" if st.session_state.active_section == "all" else "secondary"):
        st.session_state.active_section = "all"
        st.rerun()

    for sec in sections:
        n = (df["top_category"] == sec).sum()
        label = f"{sec}  ({n})"
        is_active = st.session_state.active_section == sec
        if st.button(label, key=f"nav_{sec}",
                     type="primary" if is_active else "secondary"):
            st.session_state.active_section = sec
            st.rerun()

    st.divider()
    st.caption(f"{len(df):,} курсов в базе")

filtered_df = apply_base_filters(source, language, difficulty, price_filter, sort_by)

active = st.session_state.active_section
section_label = active if active != "all" else "все разделы"

st.markdown(f"""
<div class="catalog-hero">
  <h1>Каталог IT-курсов</h1>
  <p>
    {len(filtered_df):,} курсов · Stepik · Udemy · Coursera · OpenEdu
  </p>
</div>
""", unsafe_allow_html=True)

if "quick_chip" not in st.session_state:
    st.session_state.quick_chip = None

quick_filters = [
    ("Бесплатные",  "free"),
    ("Топ рейтинг", "rating"),
    ("Популярные",  "popularity"),
    ("Начинающий",  "Beginner"),
    ("Продвинутый", "Advanced"),
]
chips_row = st.columns(5)
for i, (chip_label, chip_val) in enumerate(quick_filters):
    is_active = st.session_state.quick_chip == chip_val
    with chips_row[i]:
        if st.button(chip_label, key=f"qchip_{chip_val}",
                     type="primary" if is_active else "secondary",
                     use_container_width=True):
            st.session_state.quick_chip = None if is_active else chip_val
            st.rerun()

st.write("")

chip = st.session_state.quick_chip
if chip == "free":
    filtered_df = filtered_df[filtered_df["is_free"] == 1]
elif chip == "rating":
    filtered_df = filtered_df.sort_values("weighted_rating", ascending=False)
elif chip == "popularity":
    filtered_df = filtered_df.sort_values("students_count", ascending=False)
elif chip == "Beginner":
    filtered_df = filtered_df[filtered_df["difficulty"] == "Beginner"]
elif chip == "Advanced":
    filtered_df = filtered_df[filtered_df["difficulty"] == "Advanced"]

if active == "all":
    for section in sections:
        section_data = (
            filtered_df[filtered_df["top_category"] == section]
            .head(5)
        )
        if section_data.empty:
            continue
        render_section(section, section_data, section_key=section)
        st.write("")

else:
    section_data = filtered_df[filtered_df["top_category"] == active]

    if st.button("← Все разделы", type="secondary"):
        st.session_state.active_section = "all"
        st.rerun()

    st.markdown(
        f'<div class="section-header">'
        f'{active}'
        f'<span class="section-count">{len(section_data)} курсов</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if section_data.empty:
        st.info("Нет курсов по выбранным фильтрам.")
    else:
        COLS = 4
        items = list(section_data.iterrows())
        for row_start in range(0, len(items), COLS):
            cols = st.columns(COLS, gap="medium")
            for col_i, (_, row) in enumerate(items[row_start: row_start + COLS]):
                with cols[col_i]:
                    render_compact_card(row, f"{active}_{row_start + col_i}")
            st.write("")

st.markdown("---")
st.caption(f"CourseFind · Каталог IT-курсов · {len(df):,} курсов")
