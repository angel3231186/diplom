import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
from datetime import datetime

from personalization import profile_manager
from styles import inject_css, inject_chat_widget


st.set_page_config(
    page_title="Мой список — IT Курсы",
    page_icon="🔖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""<style>[data-testid="stSidebarNav"]{display:none!important}</style>""", unsafe_allow_html=True)

inject_css()
inject_chat_widget(user_id=st.session_state.get("username", "default"))

st.markdown("""
<style>
/* ── Hero списка ── */
.list-hero {
    padding: 32px 0 24px 0;
    border-bottom: 1px solid #1e1e2e;
    margin-bottom: 24px;
}
.list-hero h1 {
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: #f1f5f9;
    margin-bottom: 6px;
}
.list-hero p { color: #64748b; font-size: 0.95rem; margin: 0; }

/* ── Карточка сохранённого курса ── */
.saved-card {
    background: #16161f;
    border: 1px solid #1e1e2e;
    border-radius: 12px;
    padding: 18px 20px 14px 20px;
    margin-bottom: 2px;
    transition: border-color .2s, background .2s, box-shadow .2s;
}
.saved-card:hover {
    border-color: #3b5bdb;
    background: #1c1c2e;
    box-shadow: 0 2px 14px rgba(59, 91, 219, .15);
}
.saved-title { font-size: 1rem; font-weight: 700; color: #e2e8f0; margin-bottom: 4px; line-height: 1.4; }
.saved-title a { text-decoration: none; color: inherit; }
.saved-title a:hover { color: #60a5fa; }
.saved-org { font-size: 0.8rem; color: #475569; margin-bottom: 8px; }
.saved-meta { font-size: 0.83rem; color: #64748b; display: flex; flex-wrap: wrap; gap: 12px; }
.saved-meta strong { color: #cbd5e1; }
.saved-date { font-size: 0.75rem; color: #475569; margin-top: 6px; }

/* ── Пустой список ── */
.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: #475569;
}
.empty-state h2 { font-size: 1.4rem; color: #64748b; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

USER_ID = "web_user"

_SOURCE_CLS = {"stepik": "b-stepik", "udemy": "b-udemy",
               "coursera": "b-coursera", "openedu": "b-openedu"}
_DIFF_CLS   = {"Beginner": "b-beg", "Intermediate": "b-int", "Advanced": "b-adv"}
_DIFF_RU    = {"Beginner": "Начинающий", "Intermediate": "Средний", "Advanced": "Продвинутый"}


def _badge(text, cls):
    return f'<span class="badge {cls}">{text}</span>'


def _rating_html(r):
    cls = "rating-high" if r >= 4.7 else ("rating-mid" if r >= 4.3 else "rating-low")
    return f'<span class="{cls}">★ {r:.2f}</span>' if r > 0 else ""


with st.sidebar:
    st.markdown("## CourseFind")
    st.caption("Мой список")
    st.divider()
    st.page_link("app.py",           label="Поиск и рекомендации", icon="🔍")
    st.page_link("pages/Каталог.py", label="Каталог курсов",        icon="🗂")
    st.divider()

    st.markdown('<div class="sidebar-label">Фильтры</div>', unsafe_allow_html=True)

    sort_opt = st.selectbox(
        "Сортировка",
        ["newest", "oldest", "rating", "title"],
        format_func=lambda x: {
            "newest": "Сначала новые",
            "oldest": "Сначала старые",
            "rating": "По рейтингу",
            "title":  "По названию",
        }[x],
    )

    filter_source = st.selectbox(
        "Платформа",
        ["all", "stepik", "udemy", "coursera", "openedu"],
        format_func=lambda x: "Все платформы" if x == "all" else x.capitalize(),
    )

    filter_lang = st.selectbox(
        "Язык",
        ["all", "ru", "en"],
        format_func=lambda x: {"all": "Все языки", "ru": "Русский", "en": "English"}[x],
    )

    filter_price = st.selectbox(
        "Цена",
        ["all", "free", "paid"],
        format_func=lambda x: {"all": "Любая", "free": "Бесплатно", "paid": "Платные"}[x],
    )

profile  = profile_manager.get(USER_ID)
saved    = profile.get_saved()

if not saved:
    st.markdown("""
    <div class="empty-state">
      <h2>Список пуст</h2>
      <p>Нажмите 🔖 Сохранить на любом курсе — он появится здесь.</p>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("app.py",           label="Найти курсы",    icon="🔍")
    st.page_link("pages/Каталог.py", label="Открыть каталог", icon="🗂")
    st.stop()

saved_df = pd.DataFrame(saved)

if filter_source != "all":
    saved_df = saved_df[saved_df.get("source", pd.Series()) == filter_source]
if filter_lang != "all":
    saved_df = saved_df[saved_df.get("language", pd.Series()) == filter_lang]
if filter_price == "free":
    saved_df = saved_df[saved_df.get("is_free", pd.Series(0)) == 1]
elif filter_price == "paid":
    saved_df = saved_df[saved_df.get("is_free", pd.Series(0)) == 0]

if sort_opt == "newest":
    saved_df = saved_df.sort_values("ts", ascending=False)
elif sort_opt == "oldest":
    saved_df = saved_df.sort_values("ts", ascending=True)
elif sort_opt == "rating":
    saved_df = saved_df.sort_values("weighted_rating", ascending=False)
elif sort_opt == "title":
    saved_df = saved_df.sort_values("title", ascending=True)

st.markdown(f"""
<div class="list-hero">
  <h1>🔖 Мой список</h1>
  <p>Курсы, сохранённые для изучения · {len(saved)} сохранено</p>
</div>
""", unsafe_allow_html=True)

total_saved = len(saved)
free_count  = int((saved_df.get("is_free", pd.Series(0)) == 1).sum()) if not saved_df.empty else 0
avg_r = round(
    saved_df["weighted_rating"].replace(0, float("nan")).mean(), 2
) if "weighted_rating" in saved_df.columns and not saved_df.empty else 0

dur_map = {"До 1 месяца": 3, "1–3 месяца": 8, "3+ месяца": 16}
total_weeks = 0
if "duration_category" in saved_df.columns:
    total_weeks = saved_df["duration_category"].map(dur_map).fillna(0).sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Сохранено",      total_saved)
c2.metric("Бесплатных",     free_count)
c3.metric("Средний рейтинг", f"{avg_r}" if avg_r else "—")
c4.metric("Примерно недель", f"~{int(total_weeks)}" if total_weeks else "—")

st.divider()

col_exp_csv, col_exp_xl, col_clear, _ = st.columns([1.4, 1.6, 1.6, 4])

export_df = saved_df.copy()
if "ts" in export_df.columns:
    export_df = export_df.rename(columns={"ts": "дата_сохранения"})

with col_exp_csv:
    csv_data = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Скачать CSV",
        data=csv_data,
        file_name="my_courses.csv",
        mime="text/csv",
    )

with col_exp_xl:
    import io
    xl_buf = io.BytesIO()
    with pd.ExcelWriter(xl_buf, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Мой список")
    xl_buf.seek(0)
    st.download_button(
        "Скачать Excel",
        data=xl_buf.getvalue(),
        file_name="my_courses.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with col_clear:
    if st.button("Очистить список", type="secondary"):
        for item in saved:
            profile.remove_saved(item["title"])
        st.rerun()

st.divider()

if saved_df.empty:
    st.info("Нет курсов по выбранным фильтрам.")
    st.stop()

st.markdown(f"Показано: **{len(saved_df)}** из {total_saved}")
st.write("")

for _, row in saved_df.iterrows():
    title   = str(row.get("title",    "—"))
    url     = str(row.get("url",      "") or "")
    src     = str(row.get("source",   "")).lower()
    diff    = str(row.get("difficulty","—"))
    org     = str(row.get("organization", "") or "")
    is_free = int(row.get("is_free",  0)  or 0)
    price   = float(row.get("price",  0)  or 0)
    lang    = str(row.get("language", "—"))
    dur     = str(row.get("duration_category", "—"))
    r       = float(row.get("weighted_rating",  0) or 0)
    cat     = str(row.get("category", "—"))
    ts      = str(row.get("ts", ""))[:10]

    price_str  = "Бесплатно" if (is_free == 1 or price == 0) else f"{int(price):,} тг"
    lang_str   = "RU" if lang == "ru" else ("EN" if lang == "en" else lang.upper())
    src_cls    = _SOURCE_CLS.get(src, "b-paid")
    diff_cls   = _DIFF_CLS.get(diff, "b-paid")
    price_cls  = "b-free" if (is_free == 1 or price == 0) else "b-paid"
    title_html = f'<a href="{url}" target="_blank">{title}</a>' if url else title
    org_html   = f'<div class="saved-org">{org}</div>' if org else ""

    col_card, col_del = st.columns([10, 1])

    with col_card:
        st.markdown(f"""
        <div class="saved-card">
          <div class="saved-title">{title_html}</div>
          {org_html}
          <div style="margin-bottom:8px;">
            {_badge(src.capitalize() or "?", src_cls)}
            {_badge(diff, diff_cls)}
            {_badge(price_str, price_cls)}
            <span style="font-size:.75rem;color:#475569">{lang_str}</span>
          </div>
          <div class="saved-meta">
            {_rating_html(r)}
            <span><strong>{cat}</strong></span>
            <span>{dur}</span>
          </div>
          <div class="saved-date">Сохранено: {ts}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_del:
        st.write("")
        st.write("")
        if st.button("✕", key=f"del_saved_{hash(title)}"):
            profile.remove_saved(title)
            st.rerun()

st.markdown("---")
st.caption("CourseFind · Мой список · IT-курсы для изучения")
