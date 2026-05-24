"""
Рекомендательная система IT-курсов — Streamlit Web App
"""

import sys
import os
import importlib.util as _ilu

# Явная загрузка main.py по пути — обход конфликта имён в Streamlit MPA
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

def _load_local(name, relpath):
    _path = os.path.join(_APP_DIR, relpath)
    _cached = sys.modules.get(name)
    if _cached is not None and hasattr(_cached, "load_data"):
        return _cached
    sys.modules.pop(name, None)
    _spec = _ilu.spec_from_file_location(name, _path)
    _mod  = _ilu.module_from_spec(_spec)
    sys.modules[name] = _mod
    try:
        _spec.loader.exec_module(_mod)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return _mod

import streamlit as st
import streamlit.components.v1 as _st_components
import pandas as pd
import numpy as np
from datetime import datetime

import chat_history_server as _chat_srv; _chat_srv.ensure_running()
import auth
_main = _load_local("_coursefind_main", "main.py")
from personalization import profile_manager, recommend_by_onboarding, recommend_by_embeddings
from evaluation import run_evaluation, DISPLAY_COLS, TEST_CASES
import styles as _styles_mod
import gamification as gam

# ─── НАСТРОЙКИ СТРАНИЦЫ ────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Рекомендации IT-курсов",
    page_icon="★",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── ТЕМА И СТИЛИ ──────────────────────────────────────────────────────────────

# Скрываем дефолтный Streamlit multipage nav сразу
st.markdown("""<style>
[data-testid="stSidebarNav"]{display:none!important}
</style>""", unsafe_allow_html=True)

import importlib; importlib.reload(_styles_mod); _styles_mod.inject_css()


st.markdown("""
<style>
/* ── Course card (full result) ── */
.course-card {
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 18px 20px 14px;
    margin-bottom: 2px;
    transition: all .2s;
    height: 100%;
}
.course-card:hover {
    border-color: rgba(255,255,255,0.12);
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.course-title { font-size: 0.95rem; font-weight: 500; line-height: 1.5; margin-bottom: 5px; color: #f0f0f5; }
.course-title a { text-decoration: none; color: inherit; }
.course-title a:hover { color: #a594ff; }
.course-org { font-size: 0.75rem; color: #55556a; margin-bottom: 10px; }
.meta-row { display: flex; flex-wrap: wrap; gap: 10px; font-size: 0.78rem; color: #55556a; margin: 8px 0 5px; }
.meta-row strong { color: #8888a0; font-weight: 500; }
.explain-text { font-size: 0.75rem; color: #a594ff; margin-top: 5px; font-style: italic; }
.results-summary { font-size: 0.78rem; color: #55556a; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.07); margin-bottom: 16px; }
.results-summary strong { color: #8888a0; }

/* ── Pagination buttons ── */
.pagination-row { margin: 20px 0 8px; }
.pagination-row [data-testid="stButton"] button {
    background: rgba(124, 107, 255, 0.08) !important;
    border: 1px solid rgba(124, 107, 255, 0.3) !important;
    border-radius: 8px !important;
    color: #a594ff !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    padding: 8px 0 !important;
    transition: background .2s, border-color .2s, color .2s !important;
}
.pagination-row [data-testid="stButton"] button:hover:not(:disabled) {
    background: rgba(124, 107, 255, 0.18) !important;
    border-color: rgba(124, 107, 255, 0.6) !important;
    color: #c4b8ff !important;
}
.pagination-row [data-testid="stButton"] button:disabled {
    background: rgba(255,255,255,0.03) !important;
    border-color: rgba(255,255,255,0.08) !important;
    color: rgba(255,255,255,0.2) !important;
    cursor: default !important;
}

/* Убираем курсор из selectbox — выглядит как кнопка, не как input */
[data-baseweb="select"] input {
    caret-color: transparent !important;
    cursor: pointer !important;
}
[data-baseweb="select"] * {
    cursor: pointer !important;
}

/* Золотые звёзды в st.feedback */
[data-testid="stFeedback"] svg,
[data-testid="stFeedback"] svg path,
[data-testid="stButtonGroup"] svg,
[data-testid="stButtonGroup"] svg path,
[data-baseweb="button-group"] svg,
[data-baseweb="button-group"] svg path,
[class*="feedback"] svg,
[class*="feedback"] svg path {
    fill: #b8860b !important;
    color: #b8860b !important;
    stroke: #b8860b !important;
}

</style>
""", unsafe_allow_html=True)

# ─── ЗАГРУЗКА СИСТЕМЫ ──────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Загружаем модель и данные...")
def load_system(_v=12):  # увеличь _v чтобы сбросить кэш
    df = _main.load_data(_main.DATA_PATH)
    df = _main.add_bayes(df)
    embeddings, knn, df = _main.get_model(df, force_rebuild=False)
    return df, embeddings, knn

df, _embeddings, _knn = load_system(_v=11)

# Устанавливаем глобальные переменные при каждом запуске скрипта,
# а не только внутри кэшированной функции
_main.df         = df
_main.embeddings = _embeddings
_main.knn        = _knn

# ─── ПРЕДВАРИТЕЛЬНЫЕ ВЫЧИСЛЕНИЯ ────────────────────────────────────────────────

@st.cache_data
def compute_stats(_df: pd.DataFrame):
    source_counts = (
        _df.groupby("source").size().rename("Курсов").sort_values(ascending=False)
    )
    top_categories = (
        _df.groupby("top_category").size().rename("Курсов")
           .sort_values(ascending=False).head(12)
    )
    diff_counts = (
        _df[_df["difficulty"].notna()]
           .groupby("difficulty").size().rename("Курсов")
           .reindex(["Beginner", "Intermediate", "Advanced"]).dropna().astype(int)
    )
    lang_counts = _df.groupby("language").size().rename("Курсов")
    free_counts = (
        _df["is_free"].map({1: "Бесплатные", 0: "Платные"})
           .value_counts().rename("Курсов")
    )
    total      = len(_df)
    free_pct   = int((_df["is_free"] == 1).mean() * 100)
    avg_rating = round(_df[_df["weighted_rating"] > 0]["weighted_rating"].mean(), 2)
    platforms  = _df["source"].nunique()
    return (
        source_counts, top_categories, diff_counts, lang_counts, free_counts,
        total, free_pct, avg_rating, platforms,
    )

(
    source_counts, top_categories, diff_counts, lang_counts, free_counts,
    TOTAL, FREE_PCT, AVG_RATING, PLATFORMS,
) = compute_stats(df)

# ─── СОСТОЯНИЕ СЕССИИ ──────────────────────────────────────────────────────────

for key, default in [
    ("logged_in",      False),
    ("username",       ""),
    ("session_token",  ""),
    ("results",        None),
    ("last_query",     ""),
    ("run_query",      None),
    ("cat_section",    "all"),
    ("cat_chip",       None),
    ("show_account",   False),
    ("show_profile_menu", False),
    ("page",           "home"),
    ("about_tab",       0),
    ("catalog_filter", "all"),
    ("q_text",         ""),
    ("toast_queue",    []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

for _tq in st.session_state.toast_queue:
    st.toast(_tq["text"])
st.session_state.toast_queue = []

# ─── АВТОВХОД ПО ТОКЕНУ В URL ──────────────────────────────────────────────────
# При входе с "Запомнить меня" токен кладётся в ?t=TOKEN.
# Streamlit сохраняет query_params между перезагрузками страницы.

if not st.session_state.logged_in:
    _url_token = st.query_params.get("t", "")
    if _url_token:
        _auto_user = auth.validate_session(_url_token)
        if _auto_user:
            st.session_state.logged_in     = True
            st.session_state.username      = _auto_user
            st.session_state.session_token = _url_token
        else:
            # Токен истёк — убираем из URL
            st.query_params.clear()

# Защита: logged_in=True, но username пустой → сброс
if st.session_state.logged_in and not st.session_state.username:
    st.session_state.logged_in = False



# ─── ЭКРАН АВТОРИЗАЦИИ ─────────────────────────────────────────────────────────

if not st.session_state.logged_in:
    st.markdown("""
    <style>
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    _, auth_col, _ = st.columns([1, 2, 1])
    with auth_col:
        st.markdown("""
        <div style="padding:60px 0 24px">
          <div class="auth-logo">
            <span class="auth-logo-dot"></span>
            Course<span style="color:#7c6bff">Find</span>
          </div>
          <div class="auth-sub">Рекомендательная система IT-курсов</div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.get("reg_success"):
            st.success("Аккаунт создан — войдите")
            st.session_state.reg_success = False

        auth_tab_login, auth_tab_reg = st.tabs(["Войти", "Зарегистрироваться"])

        with auth_tab_login:
            st.write("")
            st.markdown('<div class="auth-card-title">Вход в аккаунт</div>', unsafe_allow_html=True)
            with st.form("login_form"):
                log_user     = st.text_input("Логин", key="login_username",
                                             label_visibility="collapsed", placeholder="Логин")
                log_pass     = st.text_input("Пароль", type="password", key="login_password",
                                             label_visibility="collapsed", placeholder="Пароль")
                log_remember = st.checkbox("Запомнить меня", value=True, key="login_remember")
                st.write("")
                if st.form_submit_button("Войти", type="primary", use_container_width=True):
                    ok, msg = auth.login(log_user, log_pass)
                    if ok:
                        _uname = log_user.strip().lower()
                        st.session_state.logged_in = True
                        st.session_state.username  = _uname
                        if log_remember:
                            _token = auth.create_session(_uname)
                            st.session_state.session_token = _token
                            st.query_params["t"] = _token
                        st.rerun()
                    else:
                        st.error(msg)

        with auth_tab_reg:
            st.write("")
            st.markdown('<div class="auth-card-title">Создать аккаунт</div>', unsafe_allow_html=True)
            with st.form("reg_form"):
                reg_user  = st.text_input("Логин", key="reg_username",
                                          label_visibility="collapsed",
                                          placeholder="Логин (3–20 символов, a-z, 0-9, _)")
                reg_pass  = st.text_input("Пароль", type="password", key="reg_password",
                                          label_visibility="collapsed", placeholder="Пароль")
                st.caption("Минимум 6 символов")
                reg_pass2 = st.text_input("Повторите пароль", type="password", key="reg_password2",
                                          label_visibility="collapsed", placeholder="Повторите пароль")
                st.write("")
                if st.form_submit_button("Зарегистрироваться", type="primary",
                                         use_container_width=True):
                    if reg_pass != reg_pass2:
                        st.error("Пароли не совпадают")
                    else:
                        ok, msg = auth.register(reg_user, reg_pass)
                        if ok:
                            st.session_state.reg_success = True
                            st.rerun()
                        else:
                            st.error(msg)

    import streamlit.components.v1 as _auth_comp
    _auth_comp.html("", height=0)
    st.stop()

# ─── ЭКРАН ОНБОРДИНГА ──────────────────────────────────────────────────────────

_current_profile = profile_manager.get(st.session_state.username)
if not _current_profile.is_onboarded():
    st.markdown("""<style>
    section[data-testid="stSidebar"] { display: none !important; }
    </style>""", unsafe_allow_html=True)
    _, onb_col, _ = st.columns([1, 2, 1])
    with onb_col:
        st.markdown('<div style="padding:48px 0 24px"><div class="auth-logo"><span class="auth-logo-dot"></span>Course<span style="color:#7c6bff">Find</span></div><div class="auth-sub">Ответь на несколько вопросов — подберём курсы именно для тебя</div></div>', unsafe_allow_html=True)

        LANG_OPTIONS = [
            "Python", "Java", "JavaScript", "Go", "SQL", "HTML/CSS",
            "Frontend", "Backend", "Fullstack", "DevOps", "Linux",
            "AI", "Data Science", "Cybersecurity", "Mobile", "Blockchain",
            "Embedded", "Database", "Web", "WordPress", "Game Design",
            "TypeScript", "Rust", "C++", "Kotlin", "Swift",
            "React", "Angular", "Django", "Flask", "FastAPI",
            "Docker", "Kubernetes", "Spring", "Android", "iOS",
        ]
        GOAL_OPTIONS = [
            "Веб-разработка", "Data Science / ML", "Мобильная разработка",
            "DevOps", "Системное программирование", "Базы данных", "Кибербезопасность",
        ]

        st.markdown('<div class="onb-step-label">Шаг 1 — Уровень</div>', unsafe_allow_html=True)
        onb_level = st.selectbox(
            "level", label_visibility="collapsed",
            options=["Beginner", "Intermediate", "Advanced"],
            format_func=lambda x: {
                "Beginner":     "Начинающий",
                "Intermediate": "Средний",
                "Advanced":     "Продвинутый",
            }[x],
        )

        st.write("")
        st.markdown('<div class="onb-step-label">Шаг 2 — Технологии</div>', unsafe_allow_html=True)
        onb_langs = st.multiselect(
            "langs", label_visibility="collapsed",
            options=LANG_OPTIONS,
            placeholder="Выбери один или несколько языков / инструментов...",
        )

        st.write("")
        st.markdown('<div class="onb-step-label">Шаг 3 — Направление (необязательно)</div>',
                    unsafe_allow_html=True)
        onb_goals = st.multiselect(
            "goals", label_visibility="collapsed",
            options=GOAL_OPTIONS,
            placeholder="Выбери направление...",
        )

        st.write("")
        if st.button("Начать", type="primary", use_container_width=True):
            if not onb_langs:
                st.warning("Выбери хотя бы одну технологию")
            else:
                _current_profile.set_onboarding(onb_level, onb_langs, onb_goals)
                st.session_state.page = "about"
                st.rerun()

    import streamlit.components.v1 as _onb_comp
    _onb_comp.html("", height=0)
    st.stop()

# ─── ИИ-чат виджет (только для авторизованных и прошедших онбординг) ──────────
_styles_mod.inject_chat_widget(user_id=st.session_state.get("username", "default"))

USER_ID = st.session_state.username

# Одноразовая синхронизация: добавить начатые курсы в список если их там нет
if USER_ID and "_started_synced" not in st.session_state:
    _sync_profile = profile_manager.get(USER_ID)
    _sync_saved_titles = {s.get("title") for s in _sync_profile.get_saved()}
    for _sc in _sync_profile.get_started():
        if _sc.get("title") and _sc["title"] not in _sync_saved_titles:
            profile_manager.track_save(USER_ID, _sc)
    st.session_state["_started_synced"] = True

# Если после всех проверок username всё равно пустой — перезапускаем.
# Это случается когда CookieManager делает внутренний rerun до восстановления state.
if not USER_ID:
    st.session_state.logged_in = False
    st.rerun()

# ─── ОЧЕРЕДЬ УВЕДОМЛЕНИЙ ───────────────────────────────────────────────────────

def _queue_toast(text: str):
    """Queue a toast to show on next rerun."""
    st.session_state.toast_queue.append({"text": text})

def _queue_achievement_toasts(new_achievements: list):
    """Queue toasts for a list of new achievement IDs."""
    for aid in new_achievements:
        _ach = gam.ACHIEVEMENT_MAP.get(aid, {})
        if _ach:
            _queue_toast(f"{_ach.get('title', '')} разблокировано!")

def _queue_xp_toasts(xp_before: int, xp_after: int):
    """Queue a toast if user leveled up."""
    _lvl_t = [0, 100, 250, 500, 1000, 2000, 5000]
    _lvl_n = ["Новичок", "Студент", "Знаток", "Эксперт", "Мастер", "Гуру", "Легенда"]
    _before = sum(1 for t in _lvl_t if xp_before >= t) - 1
    _after  = sum(1 for t in _lvl_t if xp_after  >= t) - 1
    if _after > _before:
        _queue_toast(f"Новый уровень: {_lvl_n[_after]}!")

# ─── КНОПКА НАЗАД ──────────────────────────────────────────────────────────────

def _back_btn(key: str, label: str = "← Назад") -> bool:
    st.markdown('<div class="back-btn-wrap">', unsafe_allow_html=True)
    clicked = st.button(label, key=f"back_{key}")
    st.markdown('</div>', unsafe_allow_html=True)
    return clicked

# ─── КАРТОЧКИ КУРСОВ ───────────────────────────────────────────────────────────

_SOURCE_CLS = {
    "stepik": "b-stepik", "udemy": "b-udemy",
    "coursera": "b-coursera", "openedu": "b-openedu",
}
_DIFF_CLS = {"Beginner": "b-beg", "Intermediate": "b-int", "Advanced": "b-adv"}
_DIFF_RU  = {"Beginner": "Начинающий", "Intermediate": "Средний", "Advanced": "Продвинутый"}


def _badge(text: str, cls: str) -> str:
    return f'<span class="badge {cls}">{text}</span>'


def _rating_html(r: float) -> str:
    cls = "rating-high" if r >= 4.7 else ("rating-mid" if r >= 4.3 else "rating-low")
    return f'<span class="{cls}">★ {r:.2f}</span>'


def render_course_card(row, idx: int, show_sim: bool = True, tab: str = ""):
    src      = str(row.get("source", "")).lower()
    title    = str(row.get("title", "—"))
    url      = str(row.get("url", "") or "")
    r        = float(row.get("weighted_rating", 0) or 0)
    diff     = str(row.get("difficulty", "—"))
    lang     = str(row.get("language", "—"))
    cat      = str(row.get("category", "—"))
    top_cat  = str(row.get("top_category", "") or "")
    desc     = str(row.get("description", "") or "")
    is_free  = int(row.get("is_free", 0) or 0)
    price    = float(row.get("price", 0) or 0)
    sim      = float(row.get("similarity", 0) or 0)
    expl     = str(row.get("объяснение", "") or "")

    lang_str   = "RU" if lang == "ru" else ("EN" if lang == "en" else lang.upper())
    diff_ru    = {"Beginner": "Нач", "Intermediate": "Средн", "Advanced": "Проф"}.get(diff, "")
    tag        = " · ".join(filter(None, [src.capitalize(), lang_str, diff_ru]))
    price_str  = "Бесплатно" if (is_free == 1 or price == 0) else f"{int(price):,} тг"
    price_color = "#34d399" if (is_free == 1 or price == 0) else "#94a3b8"
    tlink      = f'<a href="{url}" target="_blank" style="color:#f1f5f9;text-decoration:none">{title}</a>' if url else title
    r_str      = f'<span style="color:#fbbf24;font-weight:600">★ {r:.2f}</span>' if r > 0 else ""
    expl_str   = f'<div style="font-size:0.7rem;color:#7c6bff;margin-top:4px">{expl}</div>' if expl and expl not in ("—", "") else ""
    thumb_cls  = _thumb_cls(row)
    thumb_icon = _thumb_icon(row)

    st.markdown(f'<div style="background:#141414;border:1px solid rgba(255,255,255,0.07);border-radius:12px;overflow:hidden;transition:border-color .2s,transform .15s,box-shadow .2s" onmouseover="this.style.borderColor=\'rgba(255,255,255,0.14)\';this.style.transform=\'translateY(-2px)\';this.style.boxShadow=\'0 8px 24px rgba(0,0,0,0.4)\'" onmouseout="this.style.borderColor=\'rgba(255,255,255,0.07)\';this.style.transform=\'translateY(0)\';this.style.boxShadow=\'none\'"><div class="course-thumb {thumb_cls}" style="border-radius:0;margin:0;height:76px">{thumb_icon}</div><div style="padding:12px 16px 14px"><div style="font-size:0.63rem;color:#7c6bff;font-weight:700;letter-spacing:.07em;text-transform:uppercase;margin-bottom:5px">{tag}</div><div style="font-size:0.9rem;font-weight:600;color:#f1f5f9;line-height:1.4;margin-bottom:6px;min-height:2.8em">{tlink}</div>{expl_str}<div style="display:flex;justify-content:space-between;align-items:center;border-top:1px solid rgba(255,255,255,0.05);padding-top:8px;margin-top:8px"><span style="font-size:0.72rem">{r_str}</span><span style="font-size:0.71rem;color:{price_color};font-weight:600">{price_str}</span></div></div></div>', unsafe_allow_html=True)

    if show_sim and sim > 0:
        st.markdown(f'<div style="font-size:0.68rem;color:#475569;margin:3px 0 6px;text-align:right">Совпадение: {sim:.0%}</div>', unsafe_allow_html=True)

    if desc and len(desc) > 10:
        with st.expander("Описание"):
            st.write(desc[:1200] + ("..." if len(desc) > 1200 else ""))

    st.markdown('<div style="height:2px"></div>', unsafe_allow_html=True)
    uid = f"{tab}_{idx}_{hash(title)}"
    _profile_now     = profile_manager.get(USER_ID)
    _already_saved   = any(s["title"] == title for s in _profile_now.get_saved())
    _already_started = any(s["title"] == title for s in _profile_now.get_started())

    ca, cb, cc, cd = st.columns(4)
    with ca:
        _save_lbl = "✓ Сохранено" if _already_saved else "Сохранить"
        if st.button(_save_lbl, key=f"save_{uid}", use_container_width=True,
                     disabled=_already_saved, type="secondary"):
            profile_manager.track_save(USER_ID, row.to_dict())
            profile_manager.track_like(USER_ID, row.to_dict())
            gam.track_weekly_course_saved(USER_ID)
            _queue_toast("Сохранено в список")
            st.rerun()
    with cb:
        _start_lbl = "✓ Начато" if _already_started else "▶ Начать"
        if st.button(_start_lbl, key=f"start_{uid}", use_container_width=True,
                     disabled=_already_started):
            profile_manager.get(USER_ID).add_started(title, url, src)
            if not _already_saved:
                profile_manager.track_save(USER_ID, row.to_dict())
                gam.track_weekly_course_saved(USER_ID)
            _wq_new_ach = gam.track_weekly_course_opened(USER_ID)
            _xp_before_s = gam.get_xp(USER_ID)
            _xp_start = gam.add_xp(USER_ID, "start_course")
            _started_count = len(profile_manager.get(USER_ID).get_started())
            _start_new_ach = list(_xp_start["new_achievements"]) + _wq_new_ach
            if _started_count >= 1 and gam.unlock_achievement(USER_ID, "started_1"):
                _start_new_ach.append("started_1")
            if _started_count >= 5 and gam.unlock_achievement(USER_ID, "started_5"):
                _start_new_ach.append("started_5")
            _started_cats = {s.get("source","") for s in profile_manager.get(USER_ID).get_started()}
            if len(_started_cats) >= 3 and gam.unlock_achievement(USER_ID, "explorer"):
                _start_new_ach.append("explorer")
            _queue_toast("Добавлено в начатые")
            _queue_achievement_toasts(_start_new_ach)
            _queue_xp_toasts(_xp_before_s, _xp_start["xp"])
            if tab.startswith("personal"):
                st.session_state.page = "my"
            st.rerun()
    with cc:
        if st.button("Не интересно", key=f"dis_{uid}", use_container_width=True, type="secondary"):
            profile_manager.track_dislike(USER_ID, title)
            st.session_state.pop("_pers_recs_cache", None)
            if "_pers_similar_results" in st.session_state:
                _sim_df = st.session_state["_pers_similar_results"]
                st.session_state["_pers_similar_results"] = _sim_df[_sim_df["title"] != title].reset_index(drop=True)
            if st.session_state.get("results") is not None:
                st.session_state.results = st.session_state.results[st.session_state.results["title"] != title].reset_index(drop=True)
            _queue_toast("Больше не будем показывать")
            st.rerun()
    with cd:
        if st.button("Похожие", key=f"sim_{uid}", use_container_width=True, type="secondary"):
            _stop = {"и","в","на","с","по","для","из","от","к","а","или","это","как","что",
                     "the","of","and","for","to","in","with","an","a","part","курс","курсы",
                     "основы","введение","полный","практический","профессиональный","stepik",
                     "udemy","coursera","задачи","часть","уровень","начинающих","продвинутый"}
            _kw = [w for w in title.lower().replace("—","-").replace("+"," ").split()
                   if len(w) > 2 and w.strip(".,:-+()") not in _stop]
            _query = " ".join(_kw[:4]) if _kw else (cat or top_cat)
            if tab.startswith("personal"):
                with st.spinner("Ищем похожие..."):
                    _sim_res = _main.recommend(query=_query, user_id=USER_ID,
                                               top_k=10, sort_by="relevance", language="all",
                                               difficulty="any", category="all", top_cat="all",
                                               source="all", price_filter="any", duration="any",
                                               min_rating=0.0)
                st.session_state["_pers_similar_results"] = _sim_res
                st.session_state["_pers_similar_title"]   = title
            else:
                st.session_state.run_query = _query
                st.session_state.page = "search"
            st.rerun()
    st.write("")


# ─── КАРТОЧКИ КАТАЛОГА И СПИСКА ────────────────────────────────────────────────

def _thumb_cls(row) -> str:
    cats = (str(row.get("top_category", "")) + str(row.get("category", ""))).lower()
    if any(k in cats for k in ("python", "data", "machine", "нейро", "ml", "ai")):
        return "ct-purple"
    if any(k in cats for k in ("java", "kotlin", "android", "mobile", "spring")):
        return "ct-orange"
    if any(k in cats for k in ("web", "javascript", "react", "frontend", "css")):
        return "ct-blue"
    if any(k in cats for k in ("devops", "linux", "docker", "kubernetes", "cloud")):
        return "ct-green"
    return "ct-gray"

def _thumb_icon(row) -> str:
    cat = str(row.get("category", "")).lower()
    top = str(row.get("top_category", "")).lower()
    s   = cat + " " + top + " " + str(row.get("title", "")).lower()

    if "data science" in cat or "ml" in cat or "machine" in s or "нейрон" in s: return "📚"
    if "python"      in cat: return "🐍"
    if "fullstack"   in cat: return "🧩"
    if "frontend"    in cat or "javascript" in cat: return "⚡"
    if "java / kotlin" in cat or ("java" in s and "script" not in s): return "☕"
    if "go / golang" in cat or "golang" in s: return "🐹"
    if "c++"         in cat: return "⚙️"
    if "c#"          in cat: return "🔷"
    if "devops"      in cat or "cloud" in cat: return "🐳"
    if "mobile"      in cat or "android" in s or "ios" in s: return "📱"
    if "sql"         in cat: return "🗄️"
    if "excel"       in cat: return "📊"
    if "git"         in cat: return "🔀"
    if "cybersecur"  in cat or "security" in top: return "🔒"
    if "ui/ux"       in cat or "design"   in cat: return "🎨"
    if "testing"     in cat or "qa"       in s: return "🔍"
    if "иностранн"   in cat: return "🌍"
    if "business & management" in cat or "business" in cat or "management" in cat or "soft skills" in cat: return "💼"
    if "marketing"   in cat: return "📣"
    if "finance"     in cat: return "💰"
    if "soft skills" in cat: return "🤝"
    if "project"     in cat: return "📋"
    if "general it" in cat or "computer science" in cat: return "💻"
    return "📚"


def render_compact_card(row, card_key: str):
    import html as _html
    import math as _math
    def _safe_float(v, default=0.0):
        try:
            f = float(v)
            return default if _math.isnan(f) or _math.isinf(f) else f
        except (TypeError, ValueError):
            return default
    def _safe_int(v, default=0):
        try:
            f = float(v)
            return default if _math.isnan(f) or _math.isinf(f) else int(f)
        except (TypeError, ValueError):
            return default

    title    = str(row.get("title",    "—") or "—")
    url      = str(row.get("url",      "") or "")
    src      = str(row.get("source",   "")).lower()
    diff     = str(row.get("difficulty","—"))
    is_free  = _safe_int(row.get("is_free",  0))
    price    = _safe_float(row.get("price",  0))
    lang     = str(row.get("language", "—"))
    r        = _safe_float(row.get("weighted_rating", 0))
    org      = str(row.get("organization", "") or "")
    if org.strip().lower() in ("unknown", "nan", "none", ""):
        org = str(row.get("source", "") or "").capitalize()
    students = _safe_int(row.get("students_count", 0))

    lang_str    = "RU" if lang == "ru" else ("EN" if lang == "en" else lang.upper())
    title_safe  = _html.escape(title)
    org_safe    = _html.escape(org)
    title_html  = f'<a href="{url}" target="_blank">{title_safe}</a>' if url else title_safe
    thumb_cls   = _thumb_cls(row)
    thumb_icon  = _thumb_icon(row)
    diff_ru     = {"Beginner": "Нач", "Intermediate": "Средн", "Advanced": "Проф"}.get(diff, diff)
    price_badge = (
        '<span class="course-free-badge">Бесплатно</span>'
        if (is_free == 1 or price == 0)
        else f'<span class="course-price-badge">{int(price):,} тг</span>'
    )

    _org_html  = f'<div class="course-org-new">{org_safe}</div>' if org_safe else ""
    _stu_str   = (f"{students/1000:.0f}k" if students >= 1000 else str(students)) if students > 0 else ""
    _stu_html  = f'<span class="course-students">\U0001f465 {_stu_str}</span>' if _stu_str else ""
    st.markdown(
        f'<div class="course-card-new"><div class="course-thumb {thumb_cls}">{thumb_icon}</div>'
        f'<div class="course-body-new"><div class="course-tag-new">{src.capitalize() or "?"} \u00b7 {lang_str} \u00b7 {diff_ru}</div>'
        f'<div class="course-title-new">{title_html}</div>{_org_html}'
        f'<div class="course-meta-new"><span>\u2605 {r:.2f}</span>{_stu_html}{price_badge}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    _cc_prof    = profile_manager.get(USER_ID)
    _cc_saved   = any(s.get("title") == title for s in _cc_prof.get_saved())
    _cc_started = any(s.get("title") == title for s in _cc_prof.get_started())
    st.markdown('<div class="cc-btns"></div>', unsafe_allow_html=True)
    _cc1, _cc2  = st.columns(2)
    with _cc1:
        if _cc_saved:
            st.markdown('<div class="cc-done-badge">✓ Сохр.</div>', unsafe_allow_html=True)
        else:
            if st.button("Сохр.", key=f"save_cc_{card_key}",
                         use_container_width=True, type="secondary"):
                profile_manager.track_save(USER_ID, row.to_dict())
                profile_manager.track_like(USER_ID, row.to_dict())
                gam.track_weekly_course_saved(USER_ID)
                st.toast("Сохранено в список")
                st.rerun()
    with _cc2:
        if _cc_started:
            st.markdown('<div class="cc-done-badge">✓ Начато</div>', unsafe_allow_html=True)
        else:
            if st.button("Начать", key=f"start_cc_{card_key}",
                         use_container_width=True, type="primary"):
                _cc_prof.add_started(title, url, src)
                if not _cc_saved:
                    profile_manager.track_save(USER_ID, row.to_dict())
                    gam.track_weekly_course_saved(USER_ID)
                gam.track_weekly_course_opened(USER_ID)
                gam.add_xp(USER_ID, "start_course")
                st.toast("Добавлено в начатые")
                st.rerun()


def render_catalog_section(title: str, section_df: pd.DataFrame, section_key: str):
    n = len(section_df)
    st.markdown(
        f'<div class="section-header">{title}'
        f'<span class="section-count">{n} курсов</span></div>',
        unsafe_allow_html=True,
    )
    _card_cols = st.columns(5)
    for i, (_, row) in enumerate(section_df.head(5).iterrows()):
        with _card_cols[i]:
            render_compact_card(row, f"{section_key}_{i}")
    _, _btn_col = st.columns([7, 3])
    with _btn_col:
        if st.button(f"Показать все {title} →", key=f"show_{section_key}",
                     type="secondary", use_container_width=True):
            st.session_state.cat_section = section_key
            st.session_state[f"cat_page_{section_key}"] = 0
            st.rerun()
    st.write("")


def results_summary_html(recs: pd.DataFrame) -> str:
    avg_r   = recs["weighted_rating"].mean() if "weighted_rating" in recs else 0
    free_n  = int((recs.get("is_free", pd.Series(dtype=int)) == 1).sum())
    sources = recs["source"].value_counts().to_dict() if "source" in recs else {}
    src_str = "  ·  ".join(
        f"{s.capitalize()}: <strong>{n}</strong>"
        for s, n in sorted(sources.items(), key=lambda x: -x[1])
    )
    return (
        f'<div class="results-summary">'
        f'<strong>{len(recs)}</strong> курсов  ·  '
        f'Средний рейтинг: <strong>{avg_r:.2f}</strong>  ·  '
        f'Бесплатных: <strong>{free_n}</strong>  ·  {src_str}'
        f'</div>'
    )


def run_search(query: str, **filters) -> None:
    if not query.strip():
        return
    profile_manager.track_search(USER_ID, query)
    _xp_res = gam.add_xp(USER_ID, "search")
    _queue_achievement_toasts(_xp_res["new_achievements"])
    with st.spinner("Поиск..."):
        recs = _main.recommend(query=query, user_id=USER_ID, **filters)
    st.session_state.results    = recs
    st.session_state.last_query = query


def render_card_grid(recs: pd.DataFrame, show_sim: bool, tab: str):
    """Карточки в сетке 2 колонки."""
    items = list(recs.iterrows())
    for i in range(0, len(items), 2):
        col_a, col_b = st.columns(2, gap="medium")
        with col_a:
            _, row = items[i]
            render_course_card(row, i + 1, show_sim=show_sim, tab=tab)
            if tab == "search":
                profile_manager.track_view(USER_ID, row.to_dict())
        if i + 1 < len(items):
            with col_b:
                _, row = items[i + 1]
                render_course_card(row, i + 2, show_sim=show_sim, tab=tab)
                if tab == "search":
                    profile_manager.track_view(USER_ID, row.to_dict())


# ─── БОКОВАЯ ПАНЕЛЬ ────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"""
    <div class="sb-logo">
      <span class="sb-logo-dot"></span>
      CourseFind
    </div>
    """, unsafe_allow_html=True)

    _sb_profile = profile_manager.get(USER_ID)
    _sb_onb     = _sb_profile.get_onboarding()
    _sb_saved_n = len(_sb_profile.get_saved())
    _sb_is_new  = not _sb_profile.has_history()
    _sb_lvl_ru  = {"Beginner":"Начинающий","Intermediate":"Средний","Advanced":"Продвинутый"}
    _sb_lvl     = _sb_lvl_ru.get(_sb_onb.get("level",""), "")
    _sb_av      = _sb_profile.get_profile_meta().get("avatar", "")

    _gam_result = gam.update_streak(USER_ID)
    _streak     = _gam_result["streak"]
    _xp_info    = gam.xp_level(gam.get_xp(USER_ID))
    if _gam_result["new_achievements"]:
        for _ach_id in _gam_result["new_achievements"]:
            _ach = gam.ACHIEVEMENT_MAP.get(_ach_id, {})
            st.toast(f'{_ach.get("icon","🏆")} Достижение: {_ach.get("title","")}', icon="🎉")

    if "streak_warned" not in st.session_state:
        st.session_state.streak_warned = False
    if not st.session_state.streak_warned and gam.check_streak_warning(USER_ID):
        _queue_toast(f"Стрик {_streak} дн. под угрозой — зайди сегодня!")
        st.session_state.streak_warned = True

    if _sb_av.startswith("data:"):
        _sb_av_html = (f'<img src="{_sb_av}" '
                       f'style="width:38px;height:38px;border-radius:50%;object-fit:cover">')
    elif _sb_av:
        _sb_av_html = (f'<div class="sb-avatar" '
                       f'style="font-size:1.4rem;display:flex;align-items:center;'
                       f'justify-content:center">{_sb_av}</div>')
    else:
        _sb_av_html = f'<div class="sb-avatar">{(_sb_profile.get_profile_meta().get("display_name") or USER_ID)[0].upper() if (_sb_profile.get_profile_meta().get("display_name") or USER_ID) else "?"}</div>'

    st.markdown(
        f'<div class="sb-profile">'
        f'{_sb_av_html}'
        f'<div>'
        f'<div class="sb-name">{_sb_profile.get_profile_meta().get("display_name") or USER_ID}</div>'
        f'<div class="sb-role">{_sb_lvl if _sb_lvl else "Настройки профиля"}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    _xp_pct = int(_xp_info["progress"] * 100)
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin:8px 0 4px">
      <span style="font-size:1.1rem">{"🔥" if _streak > 0 else "💤"} <b>{_streak}</b>
        <span style="font-size:0.75rem;color:#888"> дн.</span>
      </span>
      <span style="font-size:0.75rem;color:#a594ff">{_xp_info["title"]} · {_xp_info["xp"]} XP</span>
    </div>
    <div style="background:#1e1e2e;border-radius:6px;height:6px;overflow:hidden;margin-bottom:10px">
      <div style="background:linear-gradient(90deg,#7c6bff,#a594ff);width:{_xp_pct}%;height:100%;border-radius:6px;transition:width .4s"></div>
    </div>
    """, unsafe_allow_html=True)

    _acct_lbl = "✕  Закрыть настройки" if st.session_state.show_account else "Настройки профиля"
    if st.button(_acct_lbl, key="sb_open_acct", use_container_width=True,
                 type="primary" if st.session_state.show_account else "secondary"):
        st.session_state.show_account = not st.session_state.show_account
        st.rerun()

    st.divider()

    if st.button("Главная", key="nav_home", use_container_width=True,
                 type="primary" if st.session_state.page == "home" else "secondary"):
        st.session_state.page = "home"
        st.session_state.show_account = False
        st.rerun()

    _sb_unread = gam.unread_count(USER_ID)
    _notif_lbl = f"Уведомления  {_sb_unread}" if _sb_unread else "Уведомления"
    if st.button(_notif_lbl, key="nav_notifs", use_container_width=True,
                 type="primary" if st.session_state.page == "notifications" else "secondary"):
        st.session_state.page = "notifications"
        st.session_state.show_account = False
        st.rerun()

    st.markdown('<div class="sb-nav-label">Поиск</div>', unsafe_allow_html=True)
    if st.button("Найти курс", key="nav_search", use_container_width=True,
                 type="primary" if st.session_state.page == "search" else "secondary"):
        st.session_state.page = "search"
        st.session_state.show_account = False
        st.rerun()

    _dla_label = "Для вас" if not _sb_is_new else "Для вас  ●"
    if st.button(_dla_label, key="nav_personal", use_container_width=True,
                 type="primary" if st.session_state.page == "personal" else "secondary"):
        st.session_state.page = "personal"
        st.session_state.show_account = False
        st.rerun()

    st.markdown('<div class="sb-nav-label">Моё</div>', unsafe_allow_html=True)
    _my_active = st.session_state.page in ("mylist", "started", "myratings", "my")
    _sb_started_n = len(_sb_profile.get_started())
    _my_lbl = f"Мой прогресс  {_sb_started_n}" if _sb_started_n else "Мой прогресс"
    if st.button(_my_lbl, key="nav_my", use_container_width=True, type="primary"):
        st.session_state.page = "my"
        st.session_state.show_account = False
        st.rerun()

    st.markdown('<div class="sb-nav-label">Библиотека</div>', unsafe_allow_html=True)
    if st.button("Каталог", key="nav_catalog", use_container_width=True,
                 type="primary" if st.session_state.page == "catalog" else "secondary"):
        st.session_state.page = "catalog"
        st.session_state.cat_section = "all"
        st.session_state.show_account = False
        st.rerun()

    st.markdown('<div class="sb-nav-label">Данные</div>', unsafe_allow_html=True)
    if st.button("Датасет", key="nav_stats", use_container_width=True,
                 type="primary" if st.session_state.page == "stats" else "secondary"):
        st.session_state.page = "stats"
        st.session_state.show_account = False
        st.rerun()

    if st.button("Оценка", key="nav_eval", use_container_width=True,
                 type="primary" if st.session_state.page == "eval" else "secondary"):
        st.session_state.page = "eval"
        st.session_state.show_account = False
        st.rerun()

    if st.button("О системе", key="nav_about", use_container_width=True,
                 type="primary" if st.session_state.page == "about" else "secondary"):
        st.session_state.page = "about"
        st.session_state.show_account = False
        st.rerun()

    st.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);margin:8px 0 12px 0">', unsafe_allow_html=True)

    _wq_list  = gam.get_weekly_progress(USER_ID)
    _wq_done_n = sum(1 for q in _wq_list if q["done"])
    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><span style="font-size:0.7rem;color:#55556a;letter-spacing:.07em;font-weight:600">ЗАДАНИЯ НЕДЕЛИ</span><span style="font-size:0.68rem;color:#7c6bff;font-weight:600">{_wq_done_n}/{len(_wq_list)}</span></div>', unsafe_allow_html=True)
    for _wq in _wq_list:
        _wq_pct   = int(_wq["progress"] / _wq["target"] * 100)
        _wq_done  = _wq["done"]
        _wq_clmd  = _wq["claimed"]
        if _wq_clmd:
            _wq_color = "#334155"; _wq_bar = "#334155"; _wq_badge = "✓"
        elif _wq_done:
            _wq_color = "#22c55e"; _wq_bar = "#22c55e"; _wq_badge = "🎁"
        else:
            _wq_color = "#94a3b8"; _wq_bar = "#7c6bff"; _wq_badge = ""
        st.markdown(
            f'<div style="background:rgba(124,107,255,0.1);border:1px solid rgba(124,107,255,0.25);border-radius:10px;padding:10px 12px;margin-bottom:8px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
            f'<span style="font-size:0.75rem;color:{_wq_color};font-weight:500">{_wq["title"]}</span>'
            f'<span style="font-size:0.7rem;font-weight:700;color:{"#22c55e" if _wq_done else "#7c6bff"}">{_wq["progress"]}/{_wq["target"]}</span>'
            f'</div>'
            f'<div style="background:#1e293b;border-radius:4px;height:3px">'
            f'<div style="background:{_wq_bar};width:{_wq_pct}%;height:100%;border-radius:4px;transition:width .4s"></div>'
            f'</div></div>',
            unsafe_allow_html=True
        )
        if _wq_done and not _wq_clmd:
            st.markdown('<div class="claim-xp-btn">', unsafe_allow_html=True)
            if st.button(f"Забрать {_wq['xp']} XP", key=f"claim_{_wq['id']}", use_container_width=True, type="primary"):
                gam.claim_weekly_quest(USER_ID, _wq["id"])
                _queue_toast(f"Получено {_wq['xp']} XP!")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="sb-footer-stats">
      <div class="sb-stat-mini">
        <div class="sb-stat-val">{TOTAL:,}</div>
        <div class="sb-stat-lbl">Курсов</div>
      </div>
      <div class="sb-stat-mini">
        <div class="sb-stat-val">{FREE_PCT}%</div>
        <div class="sb-stat-lbl">Бесплатно</div>
      </div>
      <div class="sb-stat-mini">
        <div class="sb-stat-val">{PLATFORMS}</div>
        <div class="sb-stat-lbl">Платформ</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    if st.button("Выйти", key="nav_logout", use_container_width=True, type="secondary"):
        if st.session_state.session_token:
            auth.revoke_session(st.session_state.session_token)
        st.session_state.logged_in     = False
        st.session_state.username      = ""
        st.session_state.session_token = ""
        st.session_state.results       = None
        st.query_params.clear()
        st.rerun()


# Значения фильтров по умолчанию
top_k        = 5
sort_by      = "relevance"
language     = "all"
difficulty   = "any"
price_filter = "any"
duration     = "any"
min_rating   = 0.0
source       = "all"
top_cat      = "all"
filter_kwargs = dict(
    top_k=top_k, sort_by=sort_by, language=language,
    difficulty=difficulty, category="all", top_cat=top_cat,
    source=source, price_filter=price_filter, duration=duration,
    min_rating=min_rating,
)

# ─── ПАНЕЛЬ АККАУНТА ───────────────────────────────────────────────────────────

if st.session_state.show_account:
    import io as _io_acct

    _ap = profile_manager.get(USER_ID)
    _ap_onb     = _ap.get_onboarding()
    _ap_stats   = profile_manager.get_stats(USER_ID)
    _ap_data    = _ap.data
    _ap_prefs   = _ap.get_preferences()
    _LVL_RU_AP  = {"Beginner": "Начинающий", "Intermediate": "Средний", "Advanced": "Продвинутый"}
    _LVL_CLS_AP = {"Beginner": "level-beg", "Intermediate": "level-int", "Advanced": "level-adv"}
    _ap_level   = _ap_onb.get("level", "")
    _ap_langs   = _ap_onb.get("languages", [])
    _ap_goals   = _ap_onb.get("goals", [])
    _ap_created = auth.get_created_at(USER_ID)
    _ap_initial = USER_ID[0].upper()
    _ap_meta    = _ap.get_profile_meta()
    _ap_bio          = _ap_meta.get("bio",          "")
    _ap_goal         = _ap_meta.get("goal",         "")
    _ap_avatar       = _ap_meta.get("avatar",       "")
    _ap_display_name = _ap_meta.get("display_name", "")

    _close_col, _title_col = st.columns([1, 9])
    with _close_col:
        if st.button("✕", key="close_acct"):
            st.session_state.show_account = False
            st.rerun()
    with _title_col:
        st.markdown("""
            <div style="display:inline-block;border:1.5px solid rgba(124,107,255,0.4);
                        border-radius:10px;padding:5px 18px;margin:2px 0">
              <span style="font-size:1.1rem;font-weight:700;color:#c0baff;letter-spacing:.03em">Аккаунт</span>
            </div>""", unsafe_allow_html=True)

    _ap_lang_tags = "".join(f'<span class="interest-tag">{l}</span>' for l in _ap_langs)
    _ap_lvl_badge = (f'<span class="level-tag {_LVL_CLS_AP.get(_ap_level, "level-beg")}">'
                     f'{_LVL_RU_AP.get(_ap_level, _ap_level)}</span>') if _ap_level else ""
    _ap_created_str = f'<strong>С</strong> {_ap_created}' if _ap_created else ""

    if _ap_avatar.startswith("data:"):
        _av_html = (f'<img src="{_ap_avatar}" '
                    f'style="width:56px;height:56px;border-radius:50%;object-fit:cover;'
                    f'flex-shrink:0">')
    elif _ap_avatar:
        _av_html = (f'<div class="profile-avatar" '
                    f'style="width:56px;height:56px;font-size:1.8rem;display:flex;'
                    f'align-items:center;justify-content:center;flex-shrink:0">'
                    f'{_ap_avatar}</div>')
    else:
        _av_html = (f'<div class="profile-avatar" '
                    f'style="width:56px;height:56px;font-size:1.4rem;flex-shrink:0">'
                    f'{_ap_initial}</div>')

    _ap_bio_html  = (f'<div style="font-size:0.82rem;color:#94a3b8;margin:3px 0 4px;'
                     f'font-style:italic">{_ap_bio}</div>') if _ap_bio else ""
    _ap_goal_html = (f'<span style="font-size:0.72rem;background:#1e1e3a;color:#a594ff;'
                     f'border-radius:20px;padding:2px 10px;display:inline-block;margin-top:4px">'
                     f'🎯 {_ap_goal}</span>') if _ap_goal else ""

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:18px;margin:14px 0 16px">'
        f'{_av_html}'
        f'<div>'
        f'<div style="font-size:1.2rem;font-weight:800;color:#f1f5f9;letter-spacing:-0.02em">{_ap_display_name or USER_ID}</div>'
        f'<div style="font-size:0.75rem;color:#475569;margin:1px 0 2px">@{USER_ID}</div>'
        f'<div style="font-size:0.8rem;color:#64748b;margin:2px 0 4px">{_ap_created_str}</div>'
        f'{_ap_bio_html}'
        f'<div style="margin-top:4px">{_ap_lvl_badge}{_ap_lang_tags}{_ap_goal_html}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(f"""
    <div style="display:flex;gap:20px;padding:12px 0;border-top:1px solid #1a1a2a;border-bottom:1px solid #1a1a2a;margin-bottom:20px">
      <div><div style="font-size:1.3rem;font-weight:800;color:#e2e8f0">{_ap_stats['searches']}</div><div style="font-size:0.7rem;color:#475569;text-transform:uppercase;letter-spacing:.06em">Поисков</div></div>
      <div><div style="font-size:1.3rem;font-weight:800;color:#e2e8f0">{_ap_stats['views']}</div><div style="font-size:0.7rem;color:#475569;text-transform:uppercase;letter-spacing:.06em">Просмотров</div></div>
      <div><div style="font-size:1.3rem;font-weight:800;color:#e2e8f0">{_ap_stats['saves']}</div><div style="font-size:0.7rem;color:#475569;text-transform:uppercase;letter-spacing:.06em">Сохранено</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── График активности ──────────────────────────────────────────────────────
    import datetime as _dt
    _act_weights = [
        ("searches", 1),
        ("views",    1),
        ("likes",    2),
        ("saved",    2),
        ("started",  3),
    ]
    _act_events = []
    for _key, _w in _act_weights:
        for _ev in _ap_data.get(_key, []):
            _ts = _ev.get("ts") or _ev.get("started_at", "")
            if _ts:
                try:
                    _d = pd.to_datetime(_ts).date()
                    _act_events.append({"date": _d, "points": _w})
                except Exception:
                    pass

    _all_days = [(_dt.date.today() - _dt.timedelta(days=i)) for i in range(13, -1, -1)]
    _cutoff   = _all_days[0]
    if _act_events:
        _act_df   = pd.DataFrame(_act_events)
        _act_df   = _act_df[_act_df["date"] >= _cutoff]
        _day_pts  = _act_df.groupby("date")["points"].sum() if not _act_df.empty else pd.Series(dtype=int)
    else:
        _day_pts = pd.Series(dtype=int)

    _act_counts = pd.Series(
        {d.strftime("%d %b"): int(_day_pts.get(d, 0)) for d in _all_days},
        name="Активность"
    )
    st.markdown('<div class="settings-panel-title" style="margin-bottom:6px">Активность за 2 недели</div>',
                unsafe_allow_html=True)
    st.bar_chart(_act_counts, height=130, use_container_width=True)

    # ── Редактировать профиль ──────────────────────────────────────────────────
    st.markdown('<div class="settings-panel-title">Редактировать профиль</div>',
                unsafe_allow_html=True)

    _PRESET_AVS = ["👩‍💻","🧑‍💻","👨‍💻","🦊","🐱","🦁","🐉","🚀","⭐","💻","🎯","🔥"]

    _ep_l, _ep_r = st.columns([4, 5], gap="large")

    with _ep_l:
        st.caption("Выбери аватар")
        _av_row1 = st.columns(6)
        _av_row2 = st.columns(6)
        for _ei, _emo in enumerate(_PRESET_AVS):
            _col = (_av_row1 if _ei < 6 else _av_row2)[_ei % 6]
            _is_cur = _ap_avatar == _emo
            if _col.button(_emo, key=f"av_emo_{_ei}",
                           type="primary" if _is_cur else "secondary"):
                _ap.set_profile_meta(_ap_bio, _ap_goal, _emo)
                st.rerun()

        _uploaded_av = st.file_uploader(
            "Или загрузи фото", type=["png", "jpg", "jpeg"],
            key="ap_avatar_upload", label_visibility="collapsed",
        )
        if _uploaded_av is not None:
            import base64 as _b64
            _b64_data = _b64.b64encode(_uploaded_av.read()).decode()
            _new_av_up = f"data:{_uploaded_av.type};base64,{_b64_data}"
            if st.button("Установить фото", key="ap_set_photo", type="primary",
                         use_container_width=True):
                _ap.set_profile_meta(_ap_bio, _ap_goal, _new_av_up)
                st.rerun()
        st.caption("PNG / JPG · до 2 МБ")

    with _ep_r:
        _GOAL_OPT_AP = [
            "", "Сменить работу", "Повысить квалификацию",
            "Хобби / интерес", "Подготовка к собеседованию",
        ]
        # Cooldown 14 дней на смену ника
        _dn_changed_at = _ap_meta.get("display_name_changed_at", "")
        _dn_cooldown_days = 14
        _dn_locked = False
        _dn_days_left = 0
        if _dn_changed_at:
            try:
                from datetime import date as _date_cls, timedelta as _td_cls
                _dn_last = _date_cls.fromisoformat(_dn_changed_at[:10])
                _dn_days_left = _dn_cooldown_days - (_date_cls.today() - _dn_last).days
                _dn_locked = _dn_days_left > 0
            except Exception:
                pass
        if _dn_locked:
            st.text_input(
                "Отображаемое имя",
                value=_ap_display_name,
                max_chars=30,
                key="ap_display_inp",
                placeholder=USER_ID,
                disabled=True,
            )
            st.caption(f"Следующая смена через {_dn_days_left} дн.")
            _new_display_ap = _ap_display_name
        else:
            _new_display_ap = st.text_input(
                "Отображаемое имя",
                value=_ap_display_name,
                max_chars=30,
                key="ap_display_inp",
                placeholder=USER_ID,
            )
            if _ap_display_name:
                st.caption("Можно менять раз в 14 дней")
        _new_bio_ap = st.text_area(
            "О себе",
            value=_ap_bio,
            max_chars=150,
            key="ap_bio_inp",
            placeholder="Пара слов о тебе…",
            height=80,
        )
        _new_goal_ap = st.selectbox(
            "Цель обучения",
            _GOAL_OPT_AP,
            index=_GOAL_OPT_AP.index(_ap_goal) if _ap_goal in _GOAL_OPT_AP else 0,
            format_func=lambda x: "Не указана" if x == "" else x,
            key="ap_goal_sel",
        )
        if st.button("Сохранить", type="primary", key="ap_save_meta",
                     use_container_width=True):
            _dn_new = _new_display_ap.strip()
            _dn_ts  = datetime.now().isoformat() if (_dn_new != _ap_display_name and not _dn_locked) else ""
            _ap.set_profile_meta(_new_bio_ap, _new_goal_ap, _ap_avatar, _dn_new, _dn_ts)
            if _new_goal_ap and _new_goal_ap != _ap_goal:
                _xp_before_g = gam.get_xp(USER_ID)
                _goal_xp = gam.add_xp(USER_ID, "set_goal")
                _goal_new_ach = list(_goal_xp["new_achievements"])
                if gam.unlock_achievement(USER_ID, "goal_set"):
                    _goal_new_ach.append("goal_set")
                _queue_achievement_toasts(_goal_new_ach)
                _queue_xp_toasts(_xp_before_g, _goal_xp["xp"])
            _queue_toast("Профиль обновлён")
            st.rerun()

    st.markdown('<hr class="profile-divider">', unsafe_allow_html=True)

    _set_l, _set_r = st.columns(2, gap="medium")

    with _set_l:
        st.markdown('<div class="settings-panel-title">Безопасность</div>', unsafe_allow_html=True)

        _show_cp_ap = st.session_state.get("ap_show_cp", False)
        if st.button("Сменить пароль", use_container_width=True, key="ap_toggle_cp"):
            st.session_state["ap_show_cp"] = not _show_cp_ap
            st.rerun()

        if st.session_state.get("ap_show_cp"):
            st.write("")
            _old_p  = st.text_input("Текущий пароль",  type="password", key="ap_cp_old")
            _new_p  = st.text_input("Новый пароль",    type="password", key="ap_cp_new")
            _new_p2 = st.text_input("Повторите новый", type="password", key="ap_cp_new2")
            if st.button("Сохранить пароль", type="primary", key="ap_save_pass"):
                if _new_p != _new_p2:
                    st.error("Пароли не совпадают")
                else:
                    _ok, _msg = auth.change_password(USER_ID, _old_p, _new_p)
                    if _ok:
                        _queue_toast("🔒 Пароль успешно изменён")
                        st.session_state["ap_show_cp"] = False
                        st.rerun()
                    else:
                        st.error(_msg)

    with _set_r:
        st.markdown('<div class="settings-panel-title">Интересы и уровень</div>', unsafe_allow_html=True)

        _show_onb_ap = st.session_state.get("ap_show_onb", False)
        if st.button("Обновить интересы", use_container_width=True, key="ap_toggle_onb"):
            st.session_state["ap_show_onb"] = not _show_onb_ap
            st.rerun()

        if st.session_state.get("ap_show_onb"):
            st.write("")
            _LANG_OPT = [
                "Python","Java","JavaScript","Go","SQL","HTML/CSS",
                "Frontend","Backend","Fullstack","DevOps","Linux",
                "AI","Data Science","Cybersecurity","Mobile","Blockchain",
                "Embedded","Database","Web","WordPress","Game Design",
                "TypeScript","Rust","C++","Kotlin","Swift",
                "React","Angular","Django","Flask","FastAPI",
                "Docker","Kubernetes","Spring","Android","iOS",
            ]
            _GOAL_OPT = ["Веб-разработка","Data Science / ML","Мобильная разработка","DevOps",
                         "Системное программирование","Базы данных","Кибербезопасность"]
            _new_lvl = st.selectbox("Уровень", ["Beginner","Intermediate","Advanced"],
                index=["Beginner","Intermediate","Advanced"].index(_ap_level or "Beginner"),
                format_func=lambda x: _LVL_RU_AP[x], key="ap_uo_level")
            _new_langs = st.multiselect("Языки / технологии", _LANG_OPT,
                default=_ap_langs, key="ap_uo_langs")
            _new_goals = st.multiselect("Цели", _GOAL_OPT,
                default=_ap_goals, key="ap_uo_goals")
            if st.button("Сохранить интересы", type="primary", key="ap_save_interests"):
                if not _new_langs:
                    st.warning("Выбери хотя бы одну технологию")
                else:
                    _ap.set_onboarding(_new_lvl, _new_langs, _new_goals)
                    st.success("Интересы обновлены")
                    st.session_state["ap_show_onb"] = False
                    st.rerun()

    # ── Рекомендации на основе профиля ────────────────────────────────────────
    st.markdown('<hr class="profile-divider">', unsafe_allow_html=True)
    st.markdown('<div class="settings-panel-title">Подобрано для вас</div>', unsafe_allow_html=True)
    _prof_recs = recommend_by_onboarding(_ap, df, top_k=3)
    if not _prof_recs.empty and "Сообщение" not in _prof_recs.columns:
        _rec_cols = st.columns(3)
        for _ri, (___, _rec_row) in enumerate(
                _prof_recs.head(3).iterrows()):
            with _rec_cols[_ri]:
                _rec_url  = _rec_row.get("url", "") or ""
                _rec_t    = _rec_row.get("title", "—")
                _rec_src  = str(_rec_row.get("source", "")).capitalize()
                _rec_diff = {"Beginner":"Начинающий","Intermediate":"Средний",
                             "Advanced":"Продвинутый"}.get(
                             _rec_row.get("difficulty",""), "")
                _rec_free = "Бесплатно" if _rec_row.get("is_free") == 1 else ""
                _rec_lnk  = f'<a href="{_rec_url}" target="_blank" style="color:#a594ff;text-decoration:none">{_rec_t}</a>' if _rec_url else _rec_t
                st.markdown(
                    f'<div style="background:#13131a;border:1px solid rgba(255,255,255,0.07);'
                    f'border-radius:10px;padding:12px 14px;height:100%">'
                    f'<div style="font-size:0.82rem;font-weight:500;line-height:1.4;margin-bottom:6px">{_rec_lnk}</div>'
                    f'<div style="font-size:0.72rem;color:#475569">{_rec_src}'
                    f'{"  ·  "+_rec_diff if _rec_diff else ""}'
                    f'{"  ·  "+_rec_free if _rec_free else ""}</div>'
                    f'</div>',
                    unsafe_allow_html=True)
    else:
        st.caption("Заполни интересы и уровень — подберём курсы")

    _ap_saved = _ap.get_saved()
    _ap_started_count = len(_ap.get_started())
    _ap_rated_count = len(_ap.get_ratings())
    st.markdown('<hr class="profile-divider">', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="display:flex;gap:12px;margin-bottom:8px">
      <div style="flex:1;background:rgba(124,107,255,0.07);border:1px solid rgba(124,107,255,0.18);
                  border-radius:12px;padding:14px 16px;text-align:center">
        <div style="font-size:1.3rem;font-weight:700;color:#c0baff">{len(_ap_saved)}</div>
        <div style="font-size:0.72rem;color:#64748b;margin-top:2px;text-transform:uppercase;letter-spacing:.06em">Сохранено</div>
      </div>
      <div style="flex:1;background:rgba(124,107,255,0.07);border:1px solid rgba(124,107,255,0.18);
                  border-radius:12px;padding:14px 16px;text-align:center">
        <div style="font-size:1.3rem;font-weight:700;color:#c0baff">{_ap_started_count}</div>
        <div style="font-size:0.72rem;color:#64748b;margin-top:2px;text-transform:uppercase;letter-spacing:.06em">Начато</div>
      </div>
      <div style="flex:1;background:rgba(124,107,255,0.07);border:1px solid rgba(124,107,255,0.18);
                  border-radius:12px;padding:14px 16px;text-align:center">
        <div style="font-size:1.3rem;font-weight:700;color:#c0baff">{_ap_rated_count}</div>
        <div style="font-size:0.72rem;color:#64748b;margin-top:2px;text-transform:uppercase;letter-spacing:.06em">Оценено</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Перейти в Моё →", key="ap_goto_my", use_container_width=True, type="secondary"):
        st.session_state.page = "my"
        st.session_state.show_account = False
        st.rerun()

    # ── Начатые курсы ─────────────────────────────────────────────────────────
    _ap_searches = _ap_data.get("searches", [])
    if _ap_searches:
        st.markdown('<hr class="profile-divider">', unsafe_allow_html=True)
        _sph, _spc = st.columns([5, 1])
        _sph.markdown(
            f'<div class="profile-section-title">История поиска <span>{len(_ap_searches)} запросов</span></div>',
            unsafe_allow_html=True)
        if _spc.button("Очистить", key="ap_clear_s", type="secondary"):
            _ap.clear_searches()
            st.rerun()

        _seen_q = set()
        _unique_q = []
        for _shi in reversed(_ap_searches):
            _q = _shi.get("query", "").strip()
            if _q and _q.lower() not in _seen_q:
                _seen_q.add(_q.lower())
                _unique_q.append(_q)
            if len(_unique_q) >= 20:
                break

        _picked = st.pills("История", _unique_q, selection_mode="single",
                           key="ap_hist_pills", label_visibility="collapsed")
        if _picked:
            st.session_state.run_query = _picked
            st.session_state.show_account = False
            st.session_state.page = "search"
            st.rerun()

    # ── Геймификация ──────────────────────────────────────────────────────────
    st.markdown('<hr class="profile-divider">', unsafe_allow_html=True)
    st.markdown('<div class="settings-panel-title">Прогресс</div>', unsafe_allow_html=True)

    _gam_streak  = gam.get_streak(USER_ID)
    _gam_xp_info = gam.xp_level(gam.get_xp(USER_ID))
    _gam_xp_pct  = int(_gam_xp_info["progress"] * 100)

    _gc1, _gc2, _gc3 = st.columns(3)
    _gc1.metric("🔥 Стрик", f"{_gam_streak} дн.")
    _gc2.metric("⚡ XP", _gam_xp_info["xp"])
    _gc3.metric("🎖 Уровень", _gam_xp_info["title"])

    st.markdown(f"""
    <div style="margin:4px 0 14px">
      <div style="display:flex;justify-content:space-between;font-size:0.75rem;color:#888;margin-bottom:4px">
        <span>До следующего уровня</span>
        <span>{_gam_xp_info["xp"]} / {_gam_xp_info["next_xp"]} XP</span>
      </div>
      <div style="background:#1e1e2e;border-radius:8px;height:8px;overflow:hidden">
        <div style="background:linear-gradient(90deg,#7c6bff,#a594ff);width:{_gam_xp_pct}%;height:100%;border-radius:8px"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:0.8rem;color:#888;margin-bottom:10px">Достижения</div>', unsafe_allow_html=True)
    _ach_list = gam.get_achievements(USER_ID)
    _ach_rows = [_ach_list[i:i+4] for i in range(0, len(_ach_list), 4)]
    for _ach_row in _ach_rows:
        _acols = st.columns(4)
        for _ai, _ach in enumerate(_ach_row):
            with _acols[_ai]:
                _opacity = "1" if _ach["unlocked"] else "0.3"
                _bg = "rgba(124,107,255,0.15)" if _ach["unlocked"] else "rgba(255,255,255,0.03)"
                _border = "rgba(124,107,255,0.4)" if _ach["unlocked"] else "rgba(255,255,255,0.07)"
                st.markdown(f"""
                <div style="background:{_bg};border:1px solid {_border};border-radius:12px;
                            padding:12px 8px;text-align:center;opacity:{_opacity};margin-bottom:8px">
                  <div style="font-size:1.6rem">{_ach["icon"]}</div>
                  <div style="font-size:0.72rem;font-weight:600;color:#f0f0f5;margin-top:4px">{_ach["title"]}</div>
                  <div style="font-size:0.65rem;color:#888;margin-top:2px">{_ach["desc"]}</div>
                </div>
                """, unsafe_allow_html=True)

    _ap_dislikes = _ap_data.get("dislikes", [])
    if _ap_dislikes or _ap_data.get("views") or _ap_data.get("likes"):
        st.markdown('<hr class="profile-divider">', unsafe_allow_html=True)
        _dz, _ = st.columns([3, 5])
        with _dz:
            st.markdown('<div class="settings-panel-title">Управление данными</div>', unsafe_allow_html=True)
            if _ap_dislikes:
                if "hidden_exp_open" not in st.session_state:
                    st.session_state["hidden_exp_open"] = False
                with st.expander(f"Скрытые курсы ({len(_ap_dislikes)})", expanded=st.session_state["hidden_exp_open"]):
                    st.session_state["hidden_exp_open"] = True
                    st.markdown('<div style="font-size:0.72rem;color:#475569;margin-bottom:10px">Эти курсы не показываются в рекомендациях</div>', unsafe_allow_html=True)
                    for _dl in _ap_dislikes:
                        _dl_t = _dl["title"]
                        _dlc1, _dlc2 = st.columns([7, 1])
                        _dlc1.markdown(f'<div style="font-size:0.88rem;font-weight:500;color:#94a3b8;padding:8px 0">{_dl_t}</div>', unsafe_allow_html=True)
                        _dlc2.markdown('<div style="height:2px"></div>', unsafe_allow_html=True)
                        if _dlc2.button("✕", key=f"undis_{hash(_dl_t)}", use_container_width=True, type="secondary"):
                            _ap.remove_dislike(_dl_t)
                            _queue_toast("Курс возвращён в рекомендации")
                            st.rerun()
            if st.button("Очистить историю активности", type="secondary",
                         use_container_width=True, key="ap_clear_hist"):
                _ap.clear_history()
                st.session_state.results    = None
                st.session_state.last_query = ""
                st.success("История очищена")
                st.rerun()

    st.markdown('<hr class="profile-divider">', unsafe_allow_html=True)
    if st.button("Выйти из аккаунта", use_container_width=True, key="ap_logout", type="secondary"):
        if st.session_state.session_token:
            auth.revoke_session(st.session_state.session_token)
        st.session_state.logged_in     = False
        st.session_state.username      = ""
        st.session_state.session_token = ""
        st.session_state.results       = None
        st.session_state.show_account  = False
        st.query_params.clear()
        st.rerun()

    st.stop()

# ─── МАРШРУТИЗАЦИЯ СТРАНИЦ ─────────────────────────────────────────────────────

_rate_title = st.query_params.get("rate_title", "")
_rate_stars = st.query_params.get("rate_stars", "")
if _rate_title and _rate_stars and USER_ID:
    try:
        _rs = int(_rate_stars)
        if 1 <= _rs <= 5:
            _rp = profile_manager.get(USER_ID)
            _rc = next((c for c in _rp.get_started() if c.get("title") == _rate_title), {})
            _rp.add_rating(_rate_title, _rs, _rc.get("url", ""), _rc.get("source", ""))
            gam.add_xp(USER_ID, "set_goal")
            st.toast(f"Оценка {'★' * _rs} сохранена!", icon="⭐")
    except Exception:
        pass
    del st.query_params["rate_title"]
    del st.query_params["rate_stars"]
    st.rerun()


_page = st.session_state.page

# ══════════════════════════════ PAGE: УВЕДОМЛЕНИЯ ════════════════════════════

if _page == "notifications":
    _notifs = gam.get_notifications(USER_ID)
    _unread_n = sum(1 for n in _notifs if not n.get("read"))

    _nh, _nc = st.columns([6, 1])
    _nh.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px">
      <span style="font-size:1.5rem;font-weight:800;color:#f1f5f9">Уведомления</span>
      {"" if not _unread_n else f'<span style="background:#7c6bff;color:#fff;border-radius:50px;padding:2px 10px;font-size:0.8rem;font-weight:700">{_unread_n} новых</span>'}
    </div>
    """, unsafe_allow_html=True)
    with _nc:
        if _notifs and st.button("Очистить", key="notif_clear", type="secondary"):
            gam.clear_notifications(USER_ID)
            st.rerun()

    if _unread_n:
        gam.mark_all_read(USER_ID)

    if not _notifs:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#475569">
          <div style="font-size:2.5rem;margin-bottom:12px">🔔</div>
          <div style="font-size:1rem">Уведомлений пока нет</div>
          <div style="font-size:0.85rem;margin-top:6px;color:#334155">Они появятся когда ты получишь достижение или выполнишь цель</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        _CAT_COLORS = {
            "achievement": ("rgba(124,107,255,0.1)", "rgba(124,107,255,0.3)"),
            "level":       ("rgba(34,197,94,0.1)",   "rgba(34,197,94,0.3)"),
            "streak":      ("rgba(249,115,22,0.1)",  "rgba(249,115,22,0.3)"),
            "info":        ("rgba(59,130,246,0.1)",  "rgba(59,130,246,0.3)"),
        }
        for _n in _notifs:
            _n_cat = _n.get("category", "info")
            _n_bg, _n_border = _CAT_COLORS.get(_n_cat, _CAT_COLORS["info"])
            _n_ts = _n.get("ts", "")
            _n_time = ""
            if _n_ts:
                try:
                    _n_time = datetime.fromisoformat(_n_ts).strftime("%d %b, %H:%M")
                except Exception:
                    pass
            _n_icon = _n.get("icon", "") or {"achievement": "🏆", "level": "⬆️", "streak": "🔥", "info": "ℹ️"}.get(_n_cat, "🔔")
            _n_text = _n.get("text", "")
            _n_dot = "" if _n.get("read") else '<span style="width:8px;height:8px;background:#7c6bff;border-radius:50%;display:inline-block;margin-left:8px"></span>'
            _n_icon_html = f'<div style="font-size:1.3rem;line-height:1;flex-shrink:0">{_n_icon}</div>' if _n_icon else ''
            st.markdown(f'<div style="background:{_n_bg};border:1px solid {_n_border};border-radius:12px;padding:14px 18px;margin-bottom:10px;display:flex;align-items:flex-start;gap:12px">{_n_icon_html}<div style="flex:1"><div style="display:flex;align-items:center;gap:4px"><span style="font-size:0.92rem;color:#f1f5f9;font-weight:500">{_n_text}</span>{_n_dot}</div><div style="font-size:0.75rem;color:#475569;margin-top:4px">{_n_time}</div></div></div>', unsafe_allow_html=True)

    st.stop()

# ══════════════════════════════ PAGE: ГЛАВНАЯ ════════════════════════════════

if _page == "home":

    _cod_action = st.query_params.get("cod_action", "")
    if _cod_action in ("save", "start"):
        _cod_act_course = gam.get_course_of_day(df, profile=profile_manager.get(USER_ID))
        _cod_act_title  = _cod_act_course.get("title", "")[:70]
        _cod_act_url    = _cod_act_course.get("url", "#")
        _cod_act_src    = _cod_act_course.get("source", "")
        _cod_act_prof   = profile_manager.get(USER_ID)
        if _cod_action == "save":
            if not any(s["title"] == _cod_act_title for s in _cod_act_prof.get_saved()):
                profile_manager.track_save(USER_ID, dict(_cod_act_course))
                _queue_toast("Сохранено в список")
        elif _cod_action == "start":
            if not any(s["title"] == _cod_act_title for s in _cod_act_prof.get_started()):
                _cod_act_prof.add_started(_cod_act_title, _cod_act_url, _cod_act_src)
                gam.track_weekly_course_opened(USER_ID)
                _xp_bef_cod = gam.get_xp(USER_ID)
                _xp_cod = gam.add_xp(USER_ID, "start_course")
                _queue_toast("Добавлено в начатые")
                _queue_achievement_toasts(_xp_cod["new_achievements"])
                _queue_xp_toasts(_xp_bef_cod, _xp_cod["xp"])
            st.session_state.page = "started"
        del st.query_params["cod_action"]
        st.rerun()

    _home_profile  = profile_manager.get(USER_ID)
    _home_gam      = gam.update_streak(USER_ID)
    _home_streak   = _home_gam["streak"]
    _home_xp_info  = gam.xp_level(gam.get_xp(USER_ID))
    _home_xp       = _home_xp_info["xp"]
    _home_xp_pct   = int(_home_xp_info["progress"] * 100)
    _home_title    = _home_xp_info["title"]
    _home_name     = _home_profile.get_profile_meta().get("display_name") or USER_ID

    # ── Приветствие ──────────────────────────────────────────────────────────
    _hr = datetime.now().hour
    _greeting = "Доброе утро" if _hr < 12 else ("Добрый день" if _hr < 18 else "Добрый вечер")
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
                background:linear-gradient(135deg,rgba(124,107,255,0.14),rgba(124,107,255,0.04));
                border:1px solid rgba(124,107,255,0.22);border-radius:16px;
                padding:22px 28px;margin-bottom:24px">
      <div>
        <div style="font-size:1.5rem;font-weight:700;color:#f1f5f9">{_greeting}, {_home_name}! 👋</div>
        <div style="font-size:0.9rem;color:#94a3b8;margin-top:4px">{_home_title} · {_home_xp} XP</div>
        <div style="background:#1e293b;border-radius:8px;height:6px;width:200px;margin-top:10px;overflow:hidden">
          <div style="background:linear-gradient(90deg,#7c6bff,#a594ff);height:100%;width:{_home_xp_pct}%;border-radius:8px"></div>
        </div>
      </div>
      <div style="text-align:center">
        <div style="font-size:2.4rem">🔥</div>
        <div style="font-size:1.4rem;font-weight:800;color:#f97316">{_home_streak}</div>
        <div style="font-size:0.75rem;color:#94a3b8">дней подряд</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Курс дня ─────────────────────────────────────────────────────────────
    _cod = gam.get_course_of_day(df, profile=_home_profile)
    _cod_title   = _cod.get("title", "")[:70]
    _cod_src     = _cod.get("source", "").capitalize()
    _cod_rating  = _cod.get("weighted_rating", 0)
    _cod_url     = _cod.get("url", "#")
    def _clean(v): s = str(v or ""); return "" if s.lower() in ("nan", "none", "") else s
    _cod_diff    = _clean(_cod.get("difficulty", ""))
    _cod_lang    = _clean(_cod.get("programming_language", ""))
    _cod_stars   = "⭐" * min(int(round(_cod_rating)), 5) if _cod_rating else ""
    _cod_badges  = " · ".join(filter(None, [_cod_src, _cod_diff, _cod_lang]))

    st.markdown("### Курс дня")

    _cod_already_saved   = any(s["title"] == _cod_title for s in _home_profile.get_saved())
    _cod_already_started = any(s["title"] == _cod_title for s in _home_profile.get_started())

    _cod_token  = st.session_state.get("session_token", "")
    _cod_tparam = f"&t={_cod_token}" if _cod_token else ""
    _btn_style = "background:rgba(124,107,255,0.22);color:#c0baff;border-radius:50px;padding:7px 20px;font-size:0.85rem;font-weight:600;border:1px solid rgba(124,107,255,0.35);display:inline-block;cursor:pointer;text-decoration:none"
    _btn_done  = "background:rgba(34,197,94,0.15);color:#86efac;border-radius:50px;padding:7px 20px;font-size:0.85rem;font-weight:600;border:1px solid rgba(34,197,94,0.3);display:inline-block;text-decoration:none"
    _save_html = f'<span style="{_btn_done}">✓ Сохранено</span>' if _cod_already_saved else f'<a href="?cod_action=save{_cod_tparam}" style="text-decoration:none"><div style="{_btn_style}">Сохранить</div></a>'
    _start_html = f'<span style="{_btn_done}">✓ Начато</span>' if _cod_already_started else f'<a href="?cod_action=start{_cod_tparam}" style="text-decoration:none"><div style="{_btn_style}">▶ Начать</div></a>'
    st.markdown(f'<div style="background:linear-gradient(135deg,rgba(124,107,255,0.18),rgba(99,102,241,0.08));border:1.5px solid rgba(124,107,255,0.35);border-radius:18px;padding:24px 28px 20px 28px"><div style="font-size:0.72rem;color:#a594ff;letter-spacing:.1em;margin-bottom:8px">ОТКРОЙТЕ СЕГОДНЯ</div><a href="{_cod_url}" target="_blank" style="text-decoration:none;color:inherit"><div style="font-size:1.2rem;font-weight:700;color:#f1f5f9;margin-bottom:10px;line-height:1.4;cursor:pointer;transition:color .15s" onmouseover="this.style.color=\'#a594ff\'" onmouseout="this.style.color=\'#f1f5f9\'">{_cod_title} ↗</div></a><div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px"><span style="font-size:0.85rem;color:#94a3b8">{_cod_badges}</span><span style="font-size:0.9rem">{_cod_stars}</span><span style="font-size:0.82rem;color:#a594ff;font-weight:600">{round(_cod_rating,1) if _cod_rating else ""}</span></div><div style="display:flex;gap:10px;flex-wrap:wrap">{_save_html}{_start_html}</div></div>', unsafe_allow_html=True)

    if "home_cod_marked" not in st.session_state:
        _new_ach = gam.mark_course_of_day_opened(USER_ID)
        st.session_state.home_cod_marked = True
        for _ach_id in _new_ach:
            _ach = gam.ACHIEVEMENT_MAP.get(_ach_id, {})
            st.toast(f"{_ach.get('icon','')} {_ach.get('title','')}", icon="🎉")

    _left_col, _right_col = st.columns([1, 1], gap="large")

    # ── Продолжить ───────────────────────────────────────────────────────────
    _STATUS_CFG = {
        0:   ("Начат",    "#ffffff", "rgba(255,255,255,0.08)"),
        50:  ("Изучаю",   "#ffffff", "rgba(255,255,255,0.08)"),
        100: ("Завершён", "#22c55e", "rgba(34,197,94,0.15)"),
    }

    with _left_col:
        st.markdown('<div style="margin-top:24px"></div>', unsafe_allow_html=True)
        st.markdown("### Продолжить")
        _started = _home_profile.get_started()
        if _started:
            for _sc in list(reversed(_started))[:4]:
                _sc_title  = _sc.get("title",    "")[:48]
                _sc_url    = _sc.get("url", "#")
                _sc_prog   = _sc.get("progress", 0)
                _sc_src    = _sc.get("source", "").capitalize()
                _sc_label, _sc_color, _sc_bg = _STATUS_CFG.get(_sc_prog, _STATUS_CFG[0])
                _sc_prog_color = "#22c55e" if _sc_prog >= 50 else "#16a34a"
                st.markdown(f'<a href="{_sc_url}" target="_blank" style="text-decoration:none;color:inherit"><div style="background:#1e293b;border:1px solid rgba(124,107,255,0.18);border-radius:12px;padding:14px 16px;margin-bottom:10px"><div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px"><div style="flex:1;min-width:0"><div style="font-size:0.9rem;font-weight:600;color:#f1f5f9;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{_sc_title} ↗</div><div style="font-size:0.75rem;color:#64748b">{_sc_src}</div></div><span style="background:rgba(255,255,255,0.08);color:#cbd5e1;border-radius:50px;padding:3px 10px;font-size:0.72rem;font-weight:600;white-space:nowrap">{_sc_label}</span></div><div style="background:#0f172a;border-radius:4px;height:2px;overflow:hidden"><div style="background:{_sc_prog_color};height:100%;width:{_sc_prog}%;border-radius:4px;transition:width .3s"></div></div></div></a>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#1e293b;border:1px dashed rgba(124,107,255,0.2);
                        border-radius:12px;padding:20px;text-align:center;color:#64748b;font-size:0.9rem">
              Начни первый курс — он появится здесь
            </div>
            """, unsafe_allow_html=True)

    # ── Рекомендации для тебя ────────────────────────────────────────────────
    with _right_col:
        st.markdown('<div style="margin-top:24px"></div>', unsafe_allow_html=True)
        st.markdown("### Для тебя сегодня")
        # Эмбеддинги только если у пользователя достаточно истории (3+ курса), иначе по онбордингу
        _home_saved_n   = len(_home_profile.get_saved())
        _home_started_n = len(_home_profile.get_started())
        _home_use_emb   = _home_saved_n + _home_started_n >= 3
        if _home_use_emb:
            _home_recs = recommend_by_embeddings(_home_profile, df, _embeddings, _knn, top_k=4, seed=0)
        else:
            _home_recs = recommend_by_onboarding(_home_profile, df, top_k=4)

        _onb_data   = _home_profile.get_onboarding()
        _onb_langs  = _onb_data.get("languages", [])
        _onb_goals  = _onb_data.get("goals", [])
        if _home_use_emb:
            _rec_reason = "На основе твоей истории"
        elif _onb_langs or _onb_goals:
            _parts = _onb_langs[:2] + _onb_goals[:1]
            _rec_reason = "Потому что ты выбрал: " + ", ".join(_parts)
        else:
            _rec_reason = ""
        if _rec_reason:
            st.markdown(f'<div style="font-size:0.75rem;color:#475569;margin-bottom:10px">{_rec_reason}</div>', unsafe_allow_html=True)

        if not _home_recs.empty:
            for _, _rr in _home_recs.iterrows():
                _rr_title  = str(_rr.get("title", ""))[:45]
                _rr_src    = str(_rr.get("source", "")).capitalize()
                _rr_url    = str(_rr.get("url", "#"))
                _rr_rat    = _rr.get("weighted_rating", 0)
                _rr_diff   = str(_rr.get("difficulty", "") or "")
                _rr_diff   = "" if _rr_diff.lower() in ("nan", "none") else _rr_diff
                _rr_badge  = " · ".join(filter(None, [_rr_src, _rr_diff]))
                st.markdown(f'<a href="{_rr_url}" target="_blank" style="text-decoration:none;color:inherit"><div style="background:#1e293b;border:1px solid rgba(124,107,255,0.18);border-radius:12px;padding:14px 16px;margin-bottom:10px;display:flex;align-items:center;justify-content:space-between"><div style="flex:1;min-width:0"><div style="font-size:0.9rem;font-weight:600;color:#f1f5f9;margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{_rr_title}</div><div style="font-size:0.75rem;color:#64748b">{_rr_badge}</div></div><div style="font-size:0.85rem;color:#fbbf24;font-weight:600;margin-left:12px;white-space:nowrap">★ {round(_rr_rat,1) if _rr_rat else "—"}</div></div></a>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#1e293b;border:1px dashed rgba(124,107,255,0.2);
                        border-radius:12px;padding:20px;text-align:center;color:#64748b;font-size:0.9rem">
              Заполни анкету для рекомендаций
            </div>
            """, unsafe_allow_html=True)

    # ── Быстрый поиск ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Быстрый поиск")
    _hq_cols = st.columns([5, 1])
    with _hq_cols[0]:
        _home_q = st.text_input("Поиск курсов", placeholder="Python, machine learning, веб-разработка…",
                                key="home_search_input", label_visibility="collapsed")
    with _hq_cols[1]:
        if st.button("Найти", key="home_search_btn", use_container_width=True, type="primary"):
            if _home_q.strip():
                st.session_state.page = "search"
                st.session_state.run_query = _home_q.strip()
                st.session_state.q_text = _home_q.strip()
                st.rerun()

    st.stop()

# ══════════════════════════════ PAGE: ПОИСК ═══════════════════════════════════

if _page == "search":

    if "sc" in st.query_params:
        _sc = st.query_params["sc"]
        del st.query_params["sc"]
        st.session_state.run_query = _sc
        st.session_state.q_text   = _sc
        st.rerun()

    results = st.session_state.results

    if results is not None and _back_btn("search"):
        st.session_state.results    = None
        st.session_state.last_query = ""
        st.rerun()

    if results is None:
        st.markdown(f"""
        <div class="page-header">
          <div class="page-header-title">Найди свой IT-курс</div>
          <div class="page-header-sub">{TOTAL:,} курсов с Stepik, Udemy, Coursera и OpenEdu — умный поиск на русском и английском</div>
        </div>
        """, unsafe_allow_html=True)

        _cod = gam.get_course_of_day(df, profile=profile_manager.get(USER_ID))
        _cod_title  = _cod.get("title", "")[:60]
        _cod_src    = _cod.get("source", "").capitalize()
        _cod_rating = _cod.get("weighted_rating", 0)
        _cod_url    = _cod.get("url", "#")
        _cod_stars  = "⭐" * min(int(round(_cod_rating)), 5) if _cod_rating else ""
        st.markdown(f'<a href="{_cod_url}" target="_blank" style="text-decoration:none;color:inherit"><div style="background:linear-gradient(135deg,rgba(124,107,255,0.12),rgba(124,107,255,0.04));border:1px solid rgba(124,107,255,0.25);border-radius:14px;padding:20px 24px;margin:0 0 24px;cursor:pointer;transition:border-color .15s" onmouseover="this.style.borderColor=\'rgba(124,107,255,0.6)\'" onmouseout="this.style.borderColor=\'rgba(124,107,255,0.25)\'"><div style="font-size:0.72rem;color:#a594ff;letter-spacing:.08em;margin-bottom:8px">📅 КУРС ДНЯ</div><div style="font-size:1.05rem;font-weight:600;color:#f0f0f5;margin-bottom:6px">{_cod_title} ↗</div><div style="font-size:0.8rem;color:#888">{_cod_src} &nbsp;·&nbsp; {_cod_stars} {_cod_rating:.1f}</div></div></a>', unsafe_allow_html=True)
        gam.mark_course_of_day_opened(USER_ID)

    if st.session_state.run_query:
        st.session_state.q_text = st.session_state.run_query
    elif st.session_state.get("_pending_q_text"):
        st.session_state.q_text = st.session_state.pop("_pending_q_text")

    with st.form("search_form", clear_on_submit=False):
        col_q, col_btn = st.columns([6, 1])
        with col_q:
            query_input = st.text_input(
                "q",
                placeholder="Python, нейросети, Docker, Kotlin, machine learning...",
                label_visibility="collapsed",
                key="q_text",
            )
        with col_btn:
            search_btn = st.form_submit_button("Найти", use_container_width=True)

    CHIPS = [
        "Python", "Java", "JavaScript", "SQL", "Go",
        "React", "Docker", "DevOps", "Linux", "Kotlin",
        "ML", "Data Science", "AI", "Deep Learning", "Cybersecurity",
        "Frontend", "Backend", "Fullstack", "Mobile", "C++",
        "C#", "UI/UX", "Project Management", "Testing", "Blockchain",
        "Excel", "ChatGPT", "Statistics", "TensorFlow", "Analytics",
    ]
    _active = st.session_state.get("last_query", "").strip()
    # Сбрасываем пилл только если last_query изменился на что-то отличное от выбранного пилла
    _lq_prev = st.session_state.get("_lq_for_pills", "")
    if _active != _lq_prev:
        st.session_state["_lq_for_pills"] = _active
        _cur_pill = st.session_state.get("_chip_pills")
        if _cur_pill and _active != _cur_pill:
            st.session_state["_chip_pills"] = None
    st.markdown("""<style>
    [data-testid="stPills"] { gap: 14px !important; flex-wrap: wrap; row-gap: 12px !important; margin-top: -16px !important; }
    [data-testid="stPills"] button { padding: 10px 22px !important; font-size: 0.95rem !important; margin: 0 !important; }
    [data-testid="stForm"] { border: none !important; padding: 0 !important; background: transparent !important; }
    </style>""", unsafe_allow_html=True)
    _selected = st.pills(
        "Быстрые запросы",
        CHIPS,
        selection_mode="single",
        key="_chip_pills",
        label_visibility="collapsed",
    )
    if _selected and _selected != _active:
        st.session_state.run_query = _selected
        st.session_state["_pending_q_text"] = _selected

    with st.expander("Фильтры"):
        _fc1, _fc2, _fc3 = st.columns(3)
        with _fc1:
            top_k = st.slider("Результатов", 3, 50, 20, key="f_topk")
            sort_by = st.selectbox("Сортировка", ["relevance","rating","popularity"],
                format_func=lambda x: {"relevance":"По релевантности","rating":"По рейтингу","popularity":"По популярности"}[x], key="f_sort")
        with _fc2:
            language = st.selectbox("Язык", ["all","ru","en"], format_func=lambda x: {"all":"Все языки","ru":"Русский","en":"English"}[x], key="f_lang")
            difficulty = st.selectbox("Уровень", ["any","Beginner","Intermediate","Advanced"],
                format_func=lambda x: {"any":"Любой","Beginner":"Начинающий","Intermediate":"Средний","Advanced":"Продвинутый"}[x], key="f_diff")
            price_filter = st.selectbox("Цена", ["any","free","paid","cheap","mid","expensive"],
                format_func=lambda x: {"any":"Любая","free":"Бесплатно","paid":"Платные","cheap":"До 5 000 тг","mid":"5 000–20 000 тг","expensive":"Дороже 20 000 тг"}[x], key="f_price")
        with _fc3:
            duration = st.selectbox("Длительность", ["any","short","medium","long"],
                format_func=lambda x: {"any":"Любая","short":"До 1 месяца","medium":"1–3 месяца","long":"3+ месяца"}[x], key="f_dur")
            min_rating = st.select_slider("Мин. рейтинг", options=[0.0,4.0,4.3,4.5,4.7,4.8], value=0.0, key="f_rat")
            _src_opts = ["all"] + sorted(df["source"].dropna().unique().tolist())
            source = st.selectbox("Платформа", _src_opts, format_func=lambda x: "Все платформы" if x=="all" else x.capitalize(), key="f_src")
        filter_kwargs = dict(
            top_k=top_k, sort_by=sort_by, language=language,
            difficulty=difficulty, category="all", top_cat="all",
            source=source, price_filter=price_filter, duration=duration,
            min_rating=min_rating,
        )

    _f_snapshot = str(filter_kwargs)
    if st.session_state.get("_f_snapshot_prev") != _f_snapshot:
        st.session_state["_f_snapshot_prev"] = _f_snapshot
        if st.session_state.get("last_query") and st.session_state.results is not None:
            run_search(st.session_state.last_query, **filter_kwargs)
            st.rerun()

    if st.session_state.run_query:
        q = st.session_state.run_query
        st.session_state.run_query = None
        run_search(q, **filter_kwargs)
        st.rerun()
    elif search_btn and query_input:
        run_search(query_input, **filter_kwargs)
        st.rerun()

    results = st.session_state.results
    if results is not None:
        if "Сообщение" in results.columns:
            st.warning(results["Сообщение"].iloc[0])
        else:
            norm = _main.normalize_query(st.session_state.last_query)
            if norm.strip() != st.session_state.last_query.lower().strip():
                st.caption(f"Запрос распознан как: {norm}")

            st.markdown(results_summary_html(results), unsafe_allow_html=True)
            render_card_grid(results, show_sim=True, tab="search")

    elif results is None:
        st.markdown('<div style="margin-top:12px"></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="stat-bar">
          <div class="stat-card-new">
            <div class="stat-val-new">{TOTAL:,}</div>
            <div class="stat-lbl-new">Курсов в базе</div>
          </div>
          <div class="stat-card-new">
            <div class="stat-val-new">{FREE_PCT}%</div>
            <div class="stat-lbl-new">Бесплатных</div>
          </div>
          <div class="stat-card-new">
            <div class="stat-val-new">{AVG_RATING}</div>
            <div class="stat-lbl-new">Средний рейтинг</div>
          </div>
          <div class="stat-card-new">
            <div class="stat-val-new">{PLATFORMS}</div>
            <div class="stat-lbl-new">Платформ</div>
          </div>
        </div>
        <div class="feature-grid-new">
          <div class="feature-card-new">
            <div class="feature-icon-new fi-purple">⌕</div>
            <div class="feature-title-new">Умный поиск</div>
            <div class="feature-desc-new">Понимает русский и английский, синонимы и транслит — «пайтон», «нейросети», «девопс».</div>
          </div>
          <div class="feature-card-new">
            <div class="feature-icon-new fi-blue">◈</div>
            <div class="feature-title-new">Гибридный алгоритм</div>
            <div class="feature-desc-new">Семантические эмбеддинги + точный поиск + байесовский рейтинг + MMR-разнообразие.</div>
          </div>
          <div class="feature-card-new">
            <div class="feature-icon-new fi-green">◎</div>
            <div class="feature-title-new">Персонализация</div>
            <div class="feature-desc-new">Отмечай понравившиеся курсы — система запомнит предпочтения и улучшит рекомендации.</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════ PAGE: ДЛЯ ВАС ════════════════════════════════

elif _page == "personal":

    _pers_profile = profile_manager.get(USER_ID)
    _pers_onb     = _pers_profile.get_onboarding()
    _LVL_RU_P     = {"Beginner": "Начинающий", "Intermediate": "Средний", "Advanced": "Продвинутый"}

    if not _pers_profile.has_history():
        if _pers_onb:
            _lvl_str = _LVL_RU_P.get(_pers_onb.get("level", ""), "")
            _lang_str = "  ·  ".join(_pers_onb.get("languages", []))
            st.markdown(f"""
            <div class="page-header">
              <div class="page-header-title">Для вас</div>
              <div class="page-header-sub">Уровень: {_lvl_str}  ·  {_lang_str}</div>
            </div>
            """, unsafe_allow_html=True)
            with st.spinner("Подбираем курсы..."):
                onb_recs = recommend_by_onboarding(_pers_profile, df, top_k=top_k)
            if not onb_recs.empty:
                st.markdown(results_summary_html(onb_recs), unsafe_allow_html=True)
                render_card_grid(onb_recs, show_sim=False, tab="personal_onb")
            st.markdown("""
            <div class="empty-state" style="margin-top:24px;padding:24px 28px;text-align:left">
              <div class="empty-state-text" style="max-width:100%;margin:0">
                Отмечай понравившиеся курсы — рекомендации станут точнее с каждым лайком
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="page-header">
              <div class="page-header-title">Для вас</div>
            </div>
            <div class="empty-state">
              <div class="empty-state-title">Здесь появятся персональные рекомендации</div>
              <div class="empty-state-text">Начни искать курсы и отмечать понравившиеся — система подберёт похожие</div>
              <div class="empty-state-steps">
                <div class="empty-state-step">
                  <div class="empty-state-step-num">1</div>
                  Найдите курсы на вкладке «Поиск»
                </div>
                <div class="empty-state-step">
                  <div class="empty-state-step-num">2</div>
                  Нажмите «Нравится» на понравившихся
                </div>
                <div class="empty-state-step">
                  <div class="empty-state-step-num">3</div>
                  Вернитесь сюда — система подберёт похожие
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="page-header">
          <div class="page-header-title">Для вас</div>
        </div>
        """, unsafe_allow_html=True)

        _pb, _ = st.columns([1.4, 6.6])
        if _pb.button("Обновить подборку", key="refresh_p", use_container_width=True):
            st.session_state["pers_seed"] = st.session_state.get("pers_seed", 0) + 1
            st.session_state.pop("_pers_recs_cache", None)
            st.rerun()
        _pers_seed = st.session_state.get("pers_seed", 0)

        _has_saves = bool(_pers_profile.get_saved()) or bool(_pers_profile.data.get("likes", []))
        if not _has_saves:
            st.markdown("""
            <div style="font-size:0.75rem;color:#475569;margin-bottom:12px;padding:10px 14px;
                        background:rgba(124,107,255,0.08);border-radius:8px;border-left:3px solid #7c6bff">
              Сохраняй курсы — рекомендации станут точнее
            </div>""", unsafe_allow_html=True)

        if "_pers_recs_cache" not in st.session_state:
            with st.spinner("Подбираем курсы..."):
                # Основная подборка — по onboarding профилю
                _onb_recs = recommend_by_onboarding(_pers_profile, df, top_k=8, seed=_pers_seed)
                # 2-3 курса по сохранённым (если есть)
                _saved_recs = recommend_by_embeddings(
                    _pers_profile, df, _embeddings, _knn, top_k=3, seed=_pers_seed
                ) if bool(_pers_profile.get_saved()) else None
                st.session_state["_pers_recs_cache"] = (_onb_recs, _saved_recs)
        personal_recs, saved_recs = st.session_state["_pers_recs_cache"]

        if st.session_state.get("_pers_similar_results") is not None:
            _sim_title = st.session_state.get("_pers_similar_title", "")
            _bc, _ = st.columns([2, 6])
            if _bc.button("← К рекомендациям", key="back_similar", type="secondary"):
                st.session_state.pop("_pers_similar_results", None)
                st.session_state.pop("_pers_similar_title", None)
                st.rerun()
            st.markdown(f'<div style="font-size:0.8rem;color:#8888a0;margin:8px 0 12px">Похожие на: <strong style="color:#f0f0f5">{_sim_title[:50]}</strong></div>', unsafe_allow_html=True)
            _sim_df = st.session_state["_pers_similar_results"]
            if "Сообщение" not in _sim_df.columns:
                st.markdown(results_summary_html(_sim_df), unsafe_allow_html=True)
                render_card_grid(_sim_df, show_sim=False, tab="personal_sim")
        elif "Сообщение" in personal_recs.columns:
            st.markdown("""
            <div class="empty-state">
              <div class="empty-state-title">Пока не хватает данных</div>
              <div class="empty-state-text">Заполни профиль — укажи цель и технологии</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(results_summary_html(personal_recs), unsafe_allow_html=True)
            render_card_grid(personal_recs, show_sim=False, tab="personal")
            if saved_recs is not None and "Сообщение" not in saved_recs.columns and not saved_recs.empty:
                st.markdown(
                    '<div style="font-size:0.85rem;font-weight:600;color:#8888a0;'
                    'margin:28px 0 10px;letter-spacing:0.04em">На основе сохранённых курсов</div>',
                    unsafe_allow_html=True,
                )
                render_card_grid(saved_recs, show_sim=False, tab="personal_saved")

# ══════════════════════════════ PAGE: КАТАЛОГ ════════════════════════════════

elif _page == "catalog":
    st.markdown("""
    <div class="page-header">
      <div class="page-header-title">Каталог IT-курсов</div>
      <div class="page-header-sub">Все курсы по категориям — фильтруй, выбирай, сохраняй</div>
    </div>
    """, unsafe_allow_html=True)

    _ALL_OPTS   = ["Бесплатные", "Топ рейтинг", "Популярные", "На русском", "На английском", "Udemy", "Coursera", "Stepik", "OpenEdu"]
    _OPT_TO_VAL = {
        "Бесплатные":"free","Топ рейтинг":"rating","Популярные":"popularity","На русском":"ru","На английском":"en",
        "Udemy":"udemy","Coursera":"coursera","Stepik":"stepik","OpenEdu":"openedu",
    }
    _VAL_TO_OPT = {v: k for k, v in _OPT_TO_VAL.items()}
    if st.session_state.cat_section == "all":
        _cur_opt    = _VAL_TO_OPT.get(st.session_state.cat_chip)
        _sel_opt    = st.segmented_control(
            "Фильтр", options=_ALL_OPTS,
            default=_cur_opt,
            label_visibility="collapsed",
            key="cat_seg",
        )
        _sel_val = _OPT_TO_VAL.get(_sel_opt)
        if _sel_val != st.session_state.cat_chip:
            st.session_state.cat_chip    = _sel_val
            st.session_state.cat_section = "all"
            st.rerun()

    cat_df = df.copy()
    chip = st.session_state.cat_chip
    if chip == "free":
        cat_df = cat_df[cat_df["is_free"] == 1]
    elif chip == "rating":
        cat_df = cat_df.sort_values("weighted_rating", ascending=False)
    elif chip == "popularity":
        cat_df = cat_df.sort_values("students_count", ascending=False)
    elif chip == "ru":
        cat_df = cat_df[cat_df["language"] == "ru"]
    elif chip == "en":
        cat_df = cat_df[cat_df["language"] == "en"]
    elif chip in ("udemy", "coursera", "stepik", "openedu"):
        cat_df = cat_df[cat_df["source"] == chip]
    else:
        cat_df = cat_df.sort_values("hybrid_score", ascending=False)

    if chip:
        st.markdown(
            f'<div class="cat-count-badge">Найдено {len(cat_df):,} курсов — {_VAL_TO_OPT.get(chip, chip)}</div>',
            unsafe_allow_html=True,
        )

    _CATEGORY_ORDER = [
        # IT / Dev — по количеству курсов
        "Data Science / ML / AI",
        "General IT / Computer Science",
        "Git / GitHub",
        "Python",
        "DevOps / Cloud",
        "Programming",
        "Frontend / JavaScript",
        "Fullstack",
        "SQL",
        "Excel",
        "Java / Kotlin",
        "Go / Golang",
        "C++",
        "C#",
        "UI/UX Design",
        "Cybersecurity / Ethical Hacking",
        "Mobile Development",
        "Testing / QA",
        "Иностранные языки",
        # Бизнес / Остальное
        "Business & Management",
        "Finance",
        "Marketing",
        "Project Management",
        "Other",
    ]
    _existing = set(df["category"].dropna().unique())
    sections = [c for c in _CATEGORY_ORDER if c in _existing]
    # Добавляем категории которых нет в списке (на случай новых)
    for c in sorted(_existing):
        if c not in sections:
            sections.append(c)
    active_sec = st.session_state.cat_section

    if active_sec == "all":
        for sec in sections:
            if sec in ("Other", "Другое / Не определено"):
                continue
            sec_data = cat_df[cat_df["category"] == sec]
            if not sec_data.empty:
                render_catalog_section(sec, sec_data, sec)
        # Other — всегда последним
        other_data = cat_df[cat_df["category"] == "Other"]
        if not other_data.empty:
            render_catalog_section("Other", other_data, "Other")
    else:
        c_back, _ = st.columns([2, 8])
        with c_back:
            if st.button("← Все разделы", type="secondary", key="cat_back"):
                st.session_state.cat_section = "all"
                st.rerun()

        sec_data = cat_df[cat_df["category"] == active_sec].sort_values("hybrid_score", ascending=False)
        n = len(sec_data)
        st.markdown(
            f'<div class="section-header">{active_sec}'
            f'<span class="section-count">{n} курсов</span></div>',
            unsafe_allow_html=True,
        )
        if sec_data.empty:
            st.info("Нет курсов по выбранным фильтрам.")
        else:
            _PAGE_SIZE = 48
            _page_key  = f"cat_page_{active_sec}"
            if _page_key not in st.session_state:
                st.session_state[_page_key] = 0
            _cur_page  = st.session_state[_page_key]
            _total     = len(sec_data)
            _total_pages = (_total - 1) // _PAGE_SIZE + 1
            items = list(sec_data.iloc[_cur_page * _PAGE_SIZE : (_cur_page + 1) * _PAGE_SIZE].iterrows())
            for row_i in range(0, len(items), 4):
                cols = st.columns(4, gap="medium")
                for ci, (_, row) in enumerate(items[row_i: row_i + 4]):
                    with cols[ci]:
                        render_compact_card(row, f"sec_{active_sec}_{_cur_page}_{row_i + ci}")
                st.write("")
            if _total_pages > 1:
                st.markdown('<div class="pagination-row">', unsafe_allow_html=True)
                p_cols = st.columns([1, 2, 1])
                with p_cols[0]:
                    if st.button("← Назад", key=f"cat_prev_{active_sec}",
                                 disabled=(_cur_page == 0),
                                 use_container_width=True):
                        st.session_state[_page_key] -= 1; st.rerun()
                with p_cols[1]:
                    st.markdown(
                        f'<div style="text-align:center;color:#94a3b8;padding-top:10px;font-size:0.85rem">'
                        f'Страница {_cur_page+1} из {_total_pages}</div>',
                        unsafe_allow_html=True)
                with p_cols[2]:
                    if st.button("Вперёд →", key=f"cat_next_{active_sec}",
                                 disabled=(_cur_page >= _total_pages - 1),
                                 use_container_width=True):
                        st.session_state[_page_key] += 1; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════ PAGE: МОЁ ════════════════════════════════════════

elif _page in ("my", "mylist", "started", "myratings"):
    import io as _io_my

    _my_profile = profile_manager.get(USER_ID)
    _my_started_all = _my_profile.get_started()
    _my_st_cnt   = len(_my_started_all)
    _my_sv_cnt   = len(_my_profile.get_saved())
    _my_rt_cnt   = len(_my_profile.get_ratings())

    st.markdown('<div style="font-size:1.7rem;font-weight:800;color:#f1f5f9;line-height:1.1;margin-bottom:20px;margin-top:8px">Моё</div>', unsafe_allow_html=True)

    _tab2, _tab1, _tab4 = st.tabs(["Начатые курсы", "Мой список", "Мои оценки"])

    # ── Вкладка: Мой список ───────────────────────────────────────────────────
    with _tab1:
        _ml_saved = _my_profile.get_saved()
        if not _ml_saved:
            st.markdown("""
            <div class="empty-state">
              <div class="empty-state-title">Список пуст</div>
              <div class="empty-state-text">Нажимай «Сохранить» на понравившихся курсах — они появятся здесь</div>
            </div>""", unsafe_allow_html=True)
        else:
            _ml_df = pd.DataFrame(_ml_saved)

            _ml_started_titles = {s.get("title") for s in _my_profile.get_started()}
            if "ml_status_sel" not in st.session_state:
                st.session_state["ml_status_sel"] = "Все"
            _mlb1, _mlb2, _mlb3 = st.columns(3)
            for _mlcol, _mlopt in zip([_mlb1, _mlb2, _mlb3], ["Все", "Начатые", "Сохраненные"]):
                if _mlcol.button(_mlopt, key=f"ml_sf_{_mlopt}", use_container_width=True,
                                 type="primary" if st.session_state["ml_status_sel"] == _mlopt else "secondary"):
                    st.session_state["ml_status_sel"] = _mlopt
                    st.rerun()
            _ml_status = st.session_state["ml_status_sel"]

            _ml_s1, _ml_s2, _ml_s3, _ml_s4 = st.columns([3, 1.5, 1.5, 1.5])
            _ml_query = _ml_s1.text_input("Поиск", placeholder="Найти курс...", label_visibility="collapsed", key="ml_search")
            _ml_src_opts = ["Все"] + sorted({c.get("source","").capitalize() for c in _ml_saved if c.get("source")})
            _ml_src = _ml_s2.selectbox("Платформа", _ml_src_opts, label_visibility="collapsed", key="ml_src")
            _ml_lang_opts = ["Любой язык", "RU", "EN"]
            _ml_lang = _ml_s3.selectbox("Язык", _ml_lang_opts, label_visibility="collapsed", key="ml_lang")
            _ml_sort_opts = ["По дате", "По рейтингу", "По цене"]
            _ml_sort = _ml_s4.selectbox("Сортировка", _ml_sort_opts, label_visibility="collapsed", key="ml_sort")

            _ml_filtered = _ml_saved
            if _ml_status == "Начатые":
                _ml_filtered = [c for c in _ml_filtered if c.get("title") in _ml_started_titles]
            elif _ml_status == "Сохраненные":
                _ml_filtered = [c for c in _ml_filtered if c.get("title") not in _ml_started_titles]
            if _ml_query:
                _ml_filtered = [c for c in _ml_filtered if _ml_query.lower() in c.get("title","").lower()]
            if _ml_src != "Все":
                _ml_filtered = [c for c in _ml_filtered if c.get("source","").capitalize() == _ml_src]
            if _ml_lang == "RU":
                _ml_filtered = [c for c in _ml_filtered if c.get("language","") == "ru"]
            elif _ml_lang == "EN":
                _ml_filtered = [c for c in _ml_filtered if c.get("language","") == "en"]
            if _ml_sort == "По дате":
                _ml_filtered = list(reversed(_ml_filtered))
            elif _ml_sort == "По рейтингу":
                _ml_filtered = sorted(_ml_filtered, key=lambda x: float(x.get("weighted_rating",0) or 0), reverse=True)
            elif _ml_sort == "По цене":
                _ml_filtered = sorted(_ml_filtered, key=lambda x: float(x.get("price",0) or 0))

            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;margin:8px 0 4px">
              <span style="font-size:0.72rem;color:#475569;background:rgba(255,255,255,0.06);
                           border-radius:20px;padding:2px 10px">{len(_ml_filtered)} из {len(_ml_saved)} курсов</span>
            </div>""", unsafe_allow_html=True)

            if not _ml_filtered:
                st.markdown("""
                <div class="empty-state">
                  <div class="empty-state-title">Ничего не найдено</div>
                  <div class="empty-state-text">Попробуй изменить запрос или фильтры</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.write("")
                _ml_items = list(enumerate(_ml_filtered))
                for _row_i in range(0, len(_ml_items), 3):
                    _cols = st.columns(3, gap="medium")
                    for _col, (_idx, _svi) in zip(_cols, _ml_items[_row_i:_row_i + 3]):
                        with _col:
                            _sv_t    = _svi.get("title","—")
                            _sv_url  = _svi.get("url","") or ""
                            _sv_src  = _svi.get("source","").lower()
                            _sv_diff = _svi.get("difficulty","—")
                            _sv_lang = _svi.get("language","—")
                            _sv_r    = float(_svi.get("weighted_rating",0) or 0)
                            _sv_free = int(_svi.get("is_free",0) or 0)
                            _sv_p_raw = _svi.get("price_raw", _svi.get("price", 0))
                            try: _sv_p = float(_sv_p_raw or 0)
                            except (ValueError, TypeError): _sv_p = 0.0
                            _sv_lang_str = "RU" if _sv_lang=="ru" else ("EN" if _sv_lang=="en" else _sv_lang.upper())
                            _sv_diff_ru  = {"Beginner":"Нач","Intermediate":"Средн","Advanced":"Проф"}.get(_sv_diff, "")
                            _sv_tag = " · ".join(filter(None, [_sv_src.capitalize(), _sv_lang_str, _sv_diff_ru]))
                            _sv_tlink = f'<a href="{_sv_url}" target="_blank" style="color:#f1f5f9;text-decoration:none">{_sv_t}</a>' if _sv_url else _sv_t
                            _sv_thumb = _thumb_cls(_svi)
                            _sv_icon  = _thumb_icon(_svi)
                            _sv_price_str = ("Бесплатно" if (_sv_free==1 or _sv_p==0) else f"{int(_sv_p):,} тг")
                            _sv_price_color = "#34d399" if (_sv_free==1 or _sv_p==0) else "#94a3b8"
                            _sv_r_str = f'★ {_sv_r:.2f}' if _sv_r > 0 else "—"
                            st.markdown(f"""
                            <div style="background:#141414;border:1px solid rgba(255,255,255,0.07);
                                        border-radius:12px;overflow:hidden;
                                        transition:border-color .2s,transform .15s,box-shadow .2s"
                                 onmouseover="this.style.borderColor='rgba(255,255,255,0.14)';this.style.transform='translateY(-2px)';this.style.boxShadow='0 8px 24px rgba(0,0,0,0.4)'"
                                 onmouseout="this.style.borderColor='rgba(255,255,255,0.07)';this.style.transform='translateY(0)';this.style.boxShadow='none'">
                              <div class="course-thumb {_sv_thumb}" style="border-radius:0;margin:0;height:76px">{_sv_icon}</div>
                              <div style="padding:11px 14px 13px;min-height:90px;display:flex;flex-direction:column;justify-content:space-between">
                                <div>
                                  <div style="font-size:0.63rem;color:#7c6bff;font-weight:700;letter-spacing:.07em;
                                              text-transform:uppercase;margin-bottom:5px">{_sv_tag}</div>
                                  <div style="font-size:0.87rem;font-weight:600;color:#f1f5f9;line-height:1.4;
                                              margin-bottom:8px;min-height:3.9em">{_sv_tlink}</div>
                                </div>
                                <div style="display:flex;justify-content:space-between;align-items:center;
                                            border-top:1px solid rgba(255,255,255,0.05);padding-top:8px">
                                  <span style="font-size:0.74rem;color:#fbbf24;font-weight:600">{_sv_r_str}</span>
                                  <span style="font-size:0.71rem;color:{_sv_price_color};font-weight:600">{_sv_price_str}</span>
                                </div>
                              </div>
                            </div>""", unsafe_allow_html=True)
                            st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
                            _already_started = any(s["title"] == _sv_t for s in _my_profile.get_started())
                            _btn_start, _btn_del = st.columns([3, 2])
                            if not _already_started:
                                if _btn_start.button("▶ Начать", key=f"ml_go_{_idx}_{hash(_sv_t)}",
                                                     use_container_width=True, type="primary"):
                                    _my_profile.add_started(_sv_t, _sv_url, _sv_src)
                                    gam.track_weekly_course_opened(USER_ID)
                                    _xp_bef_ml = gam.get_xp(USER_ID)
                                    _xp_ml = gam.add_xp(USER_ID, "start_course")
                                    _ach_ml = list(_xp_ml["new_achievements"])
                                    if len(_my_profile.get_started()) == 1:
                                        if gam.unlock_achievement(USER_ID, "started_1"): _ach_ml.append("started_1")
                                    elif len(_my_profile.get_started()) >= 5:
                                        if gam.unlock_achievement(USER_ID, "started_5"): _ach_ml.append("started_5")
                                    _queue_toast("Добавлено в начатые")
                                    _queue_achievement_toasts(_ach_ml)
                                    _queue_xp_toasts(_xp_bef_ml, _xp_ml["xp"])
                                    st.rerun()
                            else:
                                _btn_start.button("Уже начат", key=f"ml_go_{_idx}_{hash(_sv_t)}",
                                                  use_container_width=True, disabled=True)
                            if _btn_del.button("Удалить", key=f"ml_rm_{_idx}_{hash(_sv_t)}",
                                               use_container_width=True, type="secondary"):
                                _my_profile.remove_saved(_sv_t)
                                _my_profile.remove_started(_sv_t)
                                st.rerun()
                    st.write("")

    # ── Вкладка: Начатые курсы ────────────────────────────────────────────────
    with _tab2:
        _st_list = _my_profile.get_started()
        _PROG_LABELS = {0: "Начат", 50: "Изучаю", 100: "Завершён"}
        _PROG_COLOR  = {0: "#94a3b8", 50: "#a594ff", 100: "#c0baff"}
        _PROG_BG     = {0: "rgba(148,163,184,0.08)", 50: "rgba(124,107,255,0.15)", 100: "rgba(124,107,255,0.25)"}
        _PROG_BORDER = {0: "rgba(148,163,184,0.2)", 50: "rgba(124,107,255,0.4)", 100: "rgba(165,148,255,0.5)"}

        if not _st_list:
            st.markdown("""
            <div class="empty-state">
              <div class="empty-state-title">Здесь пока пусто</div>
              <div class="empty-state-text">Нажми «Начать» на карточке курса — он появится здесь</div>
            </div>""", unsafe_allow_html=True)
        else:
            _cnt = {0: 0, 50: 0, 100: 0}
            for _s in _st_list:
                _cnt[_s.get("progress", 0)] += 1

            st.markdown(f"""
            <div style="display:flex;gap:10px;margin:16px 0 22px">
              <div style="flex:1;padding:14px 18px;border:1px solid rgba(124,107,255,0.2);
                          border-radius:12px;background:#141414;text-align:center">
                <div style="font-size:1.5rem;font-weight:700;color:#94a3b8;line-height:1">{_cnt[0]}</div>
                <div style="font-size:0.68rem;color:#7c6bff88;margin-top:5px;letter-spacing:.06em;text-transform:uppercase">Начат</div>
              </div>
              <div style="flex:1;padding:14px 18px;border:1px solid rgba(124,107,255,0.4);
                          border-radius:12px;background:#141414;text-align:center">
                <div style="font-size:1.5rem;font-weight:700;color:#a594ff;line-height:1">{_cnt[50]}</div>
                <div style="font-size:0.68rem;color:#7c6bff99;margin-top:5px;letter-spacing:.06em;text-transform:uppercase">Изучаю</div>
              </div>
              <div style="flex:1;padding:14px 18px;border:1px solid rgba(124,107,255,0.6);
                          border-radius:12px;background:rgba(124,107,255,0.18);text-align:center">
                <div style="font-size:1.5rem;font-weight:700;color:#e0d9ff;line-height:1">{_cnt[100]}</div>
                <div style="font-size:0.68rem;color:#c0baff;margin-top:5px;letter-spacing:.06em;text-transform:uppercase">Завершён</div>
              </div>
            </div>""", unsafe_allow_html=True)

            if "st_status_sel" not in st.session_state:
                st.session_state["st_status_sel"] = "Все"
            _sb1, _sb2, _sb3, _sb4 = st.columns(4)
            for _scol, _sopt in zip([_sb1, _sb2, _sb3, _sb4], ["Все", "Начатые", "Изучаемые", "Завершённые"]):
                if _scol.button(_sopt, key=f"st_sf_{_sopt}", use_container_width=True,
                                type="primary" if st.session_state["st_status_sel"] == _sopt else "secondary"):
                    st.session_state["st_status_sel"] = _sopt
                    st.rerun()
            _st_status = st.session_state["st_status_sel"]

            _st_fc1, _st_fc2, _st_fc3 = st.columns([1, 1, 1])
            _st_src_opts = ["Все платформы"] + sorted({c.get("source", "").capitalize() for c in _st_list if c.get("source")})
            _st_src = _st_fc1.selectbox("Платформа", _st_src_opts, label_visibility="collapsed", key="st_src")
            _st_period = _st_fc2.selectbox("Период", ["За всё время", "За неделю", "За месяц"], label_visibility="collapsed", key="st_period")
            _st_sort = _st_fc3.selectbox("Сортировка", ["По дате", "По прогрессу", "По названию А-Я"], label_visibility="collapsed", key="st_sort")

            from datetime import datetime, timedelta
            _now = datetime.now()
            _st_filtered = _st_list
            if _st_status == "Начатые":
                _st_filtered = [c for c in _st_filtered if c.get("progress", 0) == 0]
            elif _st_status == "Изучаемые":
                _st_filtered = [c for c in _st_filtered if c.get("progress", 0) == 50]
            elif _st_status == "Завершённые":
                _st_filtered = [c for c in _st_filtered if c.get("progress", 0) == 100]
            if _st_src != "Все платформы":
                _st_filtered = [c for c in _st_filtered if c.get("source", "").capitalize() == _st_src]
            if _st_period == "За неделю":
                _st_filtered = [c for c in _st_filtered if c.get("started_at") and datetime.fromisoformat(c["started_at"]) >= _now - timedelta(days=7)]
            elif _st_period == "За месяц":
                _st_filtered = [c for c in _st_filtered if c.get("started_at") and datetime.fromisoformat(c["started_at"]) >= _now - timedelta(days=30)]

            _PROG_WIDTH  = {0: "5%", 50: "50%", 100: "100%"}
            _PROG_PCT    = {0: "", 50: "50%", 100: "100%"}
            _PROG_TRACK  = {0: "rgba(255,255,255,0.06)", 50: "rgba(124,107,255,0.2)", 100: "rgba(124,107,255,0.3)"}
            _PROG_FILL   = {0: "#475569", 50: "#7c6bff", 100: "#a594ff"}
            _ACCENT_LEFT = {0: "#2d3748", 50: "#7c6bff", 100: "#1e293b"}
            _DOT_COLOR   = {0: "#475569", 50: "#7c6bff", 100: "#334155"}

            if _st_sort == "По прогрессу":
                _sorted_list = sorted(_st_filtered, key=lambda x: (x.get("progress", 0) == 100, -x.get("progress", 0)))
            elif _st_sort == "По названию А-Я":
                _sorted_list = sorted(_st_filtered, key=lambda x: (x.get("progress", 0) == 100, x.get("title", "").lower()))
            else:
                _sorted_list = sorted(_st_filtered, key=lambda x: (x.get("progress", 0) == 100, -_st_list.index(x)))
            if not _sorted_list:
                st.markdown("""
                <div class="empty-state">
                  <div class="empty-state-title">Ничего не найдено</div>
                  <div class="empty-state-text">Попробуй изменить фильтр или запрос</div>
                </div>""", unsafe_allow_html=True)
            _shown_divider = False
            for _sti in _sorted_list:
                _st_t   = _sti.get("title", "—")
                _st_url = _sti.get("url", "") or ""
                _st_src = _sti.get("source", "").capitalize()
                _st_pr  = _sti.get("progress", 0)
                _done   = _st_pr == 100
                if _done and not _shown_divider:
                    _shown_divider = True
                    st.markdown("""
                    <div style="display:flex;align-items:center;gap:12px;margin:18px 0 14px">
                      <div style="flex:1;height:1px;background:rgba(255,255,255,0.06)"></div>
                      <span style="font-size:0.68rem;color:#374151;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap">Завершено</span>
                      <div style="flex:1;height:1px;background:rgba(255,255,255,0.06)"></div>
                    </div>""", unsafe_allow_html=True)
                # завершённые — серые и зачёркнутые, без цветов
                _title_color  = "#4b5563" if _done else "#f1f5f9"
                _title_strike = "text-decoration:line-through;text-decoration-color:#374151;" if _done else ""
                _dot_c        = "#334155" if _done else _DOT_COLOR[_st_pr]
                _pct_c        = "#374151" if _done else _DOT_COLOR[_st_pr]
                _bar_track    = "rgba(255,255,255,0.05)" if _done else _PROG_TRACK[_st_pr]
                _bar_fill     = "#1e293b"               if _done else _PROG_FILL[_st_pr]
                _card_border  = "rgba(255,255,255,0.05)" if _done else "rgba(255,255,255,0.08)"
                _accent       = "#1e293b"               if _done else _ACCENT_LEFT[_st_pr]
                _title_node   = f'<span style="color:{_title_color};{_title_strike}">{_st_t}</span>'
                _lnk_node     = (f'<a href="{_st_url}" target="_blank" style="color:{_title_color};text-decoration:none;{_title_strike}">{_st_t}</a>') if (_st_url and not _done) else _title_node

                _cc1, _cc2, _cc3 = st.columns([7, 2.5, 0.55])
                with _cc1:
                    st.markdown(f"""
                    <div style="background:#141414;border:1px solid {_card_border};
                                border-left:3px solid {_accent};
                                border-radius:12px;padding:15px 20px 13px;
                                height:100%;box-sizing:border-box;opacity:{'0.6' if _done else '1'}">
                      <div style="font-size:0.95rem;font-weight:600;line-height:1.45;margin-bottom:6px">{_lnk_node}</div>
                      <div style="display:flex;align-items:center;gap:8px;margin-bottom:11px">
                        <span style="width:6px;height:6px;border-radius:50%;background:{_dot_c};display:inline-block;flex-shrink:0"></span>
                        <span style="font-size:0.73rem;color:#4b5563">{_st_src}</span>
                        <span style="font-size:0.68rem;color:{_pct_c};font-weight:600;margin-left:auto">{_PROG_PCT[_st_pr]}</span>
                      </div>
                      <div style="background:{_bar_track};border-radius:4px;height:2px;overflow:hidden">
                        <div style="width:{_PROG_WIDTH[_st_pr]};height:100%;background:{_bar_fill};border-radius:4px"></div>
                      </div>
                    </div>""", unsafe_allow_html=True)
                with _cc2:
                    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
                    _new_prog = st.selectbox("Статус", [0, 50, 100], index=[0, 50, 100].index(_st_pr),
                        format_func=lambda x: _PROG_LABELS[x], key=f"stpg_{hash(_st_t)}", label_visibility="collapsed")
                    if _new_prog != _st_pr:
                        _my_profile.update_started_progress(_st_t, _new_prog)
                        if _new_prog == 100:
                            _xp_bef_c = gam.get_xp(USER_ID)
                            _xp_comp = gam.add_xp(USER_ID, "complete_course")
                            _comp_new_ach = list(_xp_comp["new_achievements"])
                            if gam.unlock_achievement(USER_ID, "completed_1"):
                                _comp_new_ach.append("completed_1")
                            _queue_toast("Курс завершён!")
                            _queue_achievement_toasts(_comp_new_ach)
                            _queue_xp_toasts(_xp_bef_c, _xp_comp["xp"])
                        st.rerun()
                with _cc3:
                    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
                    if st.button("✕", key=f"strm_{hash(_st_t)}", type="secondary"):
                        _my_profile.remove_started(_st_t)
                        st.rerun()
                st.write("")

    # ── Вкладка: Мои оценки ───────────────────────────────────────────────────
    with _tab4:
        _mr_liked_count = len(_my_profile.data.get("likes", []))
        if _mr_liked_count > 0:
            st.markdown(f"""
            <div style="font-size:0.75rem;color:#475569;margin-bottom:18px">
              На основе <span style="color:#7c6bff;font-weight:600">{_mr_liked_count} понравившихся курсов</span>
              система улучшает твои рекомендации
            </div>""", unsafe_allow_html=True)
        _completed  = _my_profile.get_completed()
        _rated      = {r["title"]: r for r in _my_profile.get_ratings()}
        _unrated    = [c for c in _completed if c.get("title") not in _rated]
        _rated_list = list(reversed(_my_profile.get_ratings()))

        if not _completed:
            st.markdown("""
            <div class="empty-state">
              <div class="empty-state-title">Нет завершённых курсов</div>
              <div class="empty-state-text">Отметь курс как «Завершён» во вкладке «Начатые курсы» — и сможешь его оценить</div>
            </div>""", unsafe_allow_html=True)
            _ec1, _ec2, _ec3 = st.columns([1, 1.4, 1])
            if _ec2.button("Перейти к начатым курсам", use_container_width=True, type="primary"):
                st.session_state["_active_tab"] = "started"
                st.rerun()
        else:
            st.markdown(f"""
            <div style="display:flex;gap:10px;margin:16px 0 22px">
              <div style="flex:1;padding:14px 18px;border:1px solid rgba(124,107,255,0.4);
                          border-radius:12px;background:#141414;text-align:center">
                <div style="font-size:1.5rem;font-weight:700;color:#a594ff;line-height:1">{len(_unrated)}</div>
                <div style="font-size:0.68rem;color:#7c6bff99;margin-top:5px;letter-spacing:.06em;text-transform:uppercase">Ожидают оценки</div>
              </div>
              <div style="flex:1;padding:14px 18px;border:1px solid rgba(124,107,255,0.6);
                          border-radius:12px;background:rgba(124,107,255,0.18);text-align:center">
                <div style="font-size:1.5rem;font-weight:700;color:#e0d9ff;line-height:1">{len(_rated_list)}</div>
                <div style="font-size:0.68rem;color:#c0baff;margin-top:5px;letter-spacing:.06em;text-transform:uppercase">Оценено</div>
              </div>
            </div>""", unsafe_allow_html=True)

            if _unrated:
                for _uc in _unrated:
                    _uc_t   = _uc.get("title", "—")
                    _uc_src = _uc.get("source", "").capitalize()
                    _uc_url = _uc.get("url", "") or ""
                    _uc_lnk = f'<a href="{_uc_url}" target="_blank" style="color:#f1f5f9;text-decoration:none">{_uc_t}</a>' if _uc_url else _uc_t
                    _uch    = abs(hash(_uc_t)) % 999983
                    _pkey   = f"pend_{_uch}"
                    if _pkey not in st.session_state:
                        st.session_state[_pkey] = 0
                    _pending = st.session_state[_pkey]

                    _uc1, _uc2, _uc3 = st.columns([6, 2, 1.5])
                    with _uc1:
                        st.markdown(f"""
                        <div style="background:linear-gradient(135deg,#141414,#0f0f18);
                                    border:1px solid rgba(124,107,255,0.2);
                                    border-left:3px solid #7c6bff;
                                    border-radius:14px;padding:14px 18px 13px;
                                    box-shadow:0 2px 10px rgba(0,0,0,0.25)">
                          <div style="font-size:0.92rem;font-weight:600;line-height:1.45;margin-bottom:5px;color:#f1f5f9">{_uc_lnk}</div>
                          <div style="display:flex;align-items:center;gap:7px">
                            <span style="width:6px;height:6px;border-radius:50%;background:#7c6bff;display:inline-block;flex-shrink:0"></span>
                            <span style="font-size:0.72rem;color:#4b5563">{_uc_src}</span>
                          </div>
                        </div>""", unsafe_allow_html=True)
                    with _uc2:
                        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
                        _fb = st.feedback("stars", key=f"fb_{_uch}")
                        if _fb is not None:
                            st.session_state[_pkey] = _fb + 1
                    with _uc3:
                        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
                        if st.button("Сохранить", key=f"save_{_uch}", use_container_width=True, disabled=st.session_state.get(_pkey, 0) == 0):
                            _my_profile.add_rating(_uc_t, _pending, _uc_url, _uc.get("source", ""))
                            gam.add_xp(USER_ID, "set_goal")
                            st.session_state[_pkey] = 0
                            st.session_state.pop(f"fb_{_uch}", None)
                            st.toast(f"Оценка {'★' * _pending} сохранена!")
                            st.rerun()
                    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
            if _unrated and _rated_list:
                st.markdown("""
                <div style="display:flex;align-items:center;gap:12px;margin:18px 0 14px">
                  <div style="flex:1;height:1px;background:rgba(255,255,255,0.06)"></div>
                  <span style="font-size:0.68rem;color:#374151;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap">Оценено</span>
                  <div style="flex:1;height:1px;background:rgba(255,255,255,0.06)"></div>
                </div>""", unsafe_allow_html=True)

            if _rated_list:
                for _rr in _rated_list:
                    _rr_t   = _rr.get("title", "—")
                    _rr_src = _rr.get("source", "").capitalize()
                    _rr_url = _rr.get("url", "") or ""
                    _rr_s   = _rr.get("stars", 0)
                    _rr_edit_key = f"edit_rating_{hash(_rr_t)}"
                    _rr_editing  = st.session_state.get(_rr_edit_key, False)

                    if _rr_editing:
                        _rr_lnk2 = f'<a href="{_rr_url}" target="_blank" style="color:#4b5563;text-decoration:line-through;text-decoration-color:#374151">{_rr_t}</a>' if _rr_url else f'<span style="color:#4b5563;text-decoration:line-through;text-decoration-color:#374151">{_rr_t}</span>'
                        _re1, _re2, _re3 = st.columns([7, 2, 1.2])
                        with _re1:
                            st.markdown(f"""
                            <div style="background:linear-gradient(135deg,#141414,#0f0f18);
                                        border:1px solid rgba(124,107,255,0.35);
                                        border-left:3px solid #7c6bff;
                                        border-radius:14px;padding:14px 18px 12px;
                                        box-shadow:0 2px 12px rgba(124,107,255,0.1)">
                              <div style="font-size:0.92rem;font-weight:600;line-height:1.45;margin-bottom:5px;color:#6b7280">{_rr_lnk2}</div>
                              <div style="display:flex;align-items:center;gap:7px">
                                <span style="width:5px;height:5px;border-radius:50%;background:#2d3748;display:inline-block;flex-shrink:0"></span>
                                <span style="font-size:0.71rem;color:#374151">{_rr_src}</span>
                              </div>
                            </div>""", unsafe_allow_html=True)
                        with _re2:
                            st.markdown('<div style="height:13px"></div>', unsafe_allow_html=True)
                            _re_fb_result = st.feedback("stars", key=f"re_fb_{hash(_rr_t)}")
                            if _re_fb_result is not None:
                                _my_profile.add_rating(_rr_t, _re_fb_result + 1, _rr_url, _rr.get("source", ""))
                                st.session_state[_rr_edit_key] = False
                                st.toast("Оценка обновлена!", icon="⭐")
                                st.rerun()
                        with _re3:
                            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
                            if st.button("Отмена", key=f"re_cancel_{hash(_rr_t)}", use_container_width=True):
                                st.session_state[_rr_edit_key] = False
                                st.rerun()
                    else:
                        _rr_lnk = f'<a href="{_rr_url}" target="_blank" style="color:#4b5563;text-decoration:line-through;text-decoration-color:#374151">{_rr_t}</a>' if _rr_url else f'<span style="color:#4b5563;text-decoration:line-through;text-decoration-color:#374151">{_rr_t}</span>'
                        _rv1, _rv2 = st.columns([9, 1.2])
                        with _rv1:
                            st.markdown(f"""
                            <div style="background:linear-gradient(135deg,#141414,#0f0f18);
                                        border:1px solid rgba(255,255,255,0.05);
                                        border-left:3px solid rgba(124,107,255,0.3);
                                        border-radius:14px;padding:14px 18px 12px;
                                        display:flex;align-items:center;justify-content:space-between;
                                        box-shadow:0 2px 10px rgba(0,0,0,0.25)">
                              <div>
                                <div style="font-size:0.92rem;font-weight:600;line-height:1.45;margin-bottom:5px;color:#6b7280">{_rr_lnk}</div>
                                <div style="display:flex;align-items:center;gap:7px">
                                  <span style="width:5px;height:5px;border-radius:50%;background:#2d3748;display:inline-block;flex-shrink:0"></span>
                                  <span style="font-size:0.71rem;color:#374151">{_rr_src}</span>
                                </div>
                              </div>
                              <div style="display:flex;gap:2px;align-items:center;flex-shrink:0">
                                {"".join([f'<span style="font-size:1.3rem;line-height:1;color:#fbbf24;filter:drop-shadow(0 0 4px rgba(251,191,36,0.5))">★</span>' for _ in range(_rr_s)])}
                                {"".join([f'<span style="font-size:1.3rem;line-height:1;color:rgba(251,191,36,0.18)">★</span>' for _ in range(5-_rr_s)])}
                              </div>
                            </div>""", unsafe_allow_html=True)
                        with _rv2:
                            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
                            if st.button("Изменить", key=f"re_edit_{hash(_rr_t)}", use_container_width=True):
                                st.session_state[_rr_edit_key] = True
                                st.rerun()
                    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    st.stop()

# ══════════════════════════════ PAGE: ДАТАСЕТ ════════════════════════════════

elif _page == "stats":

    st.markdown(f"""
    <div class="page-header">
      <div class="page-header-title">Статистика датасета</div>
      <div class="page-header-sub">{TOTAL:,} курсов собраны с четырёх платформ и размечены вручную</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-value">{TOTAL:,}</div>
        <div class="stat-label">Всего курсов</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{FREE_PCT}%</div>
        <div class="stat-label">Бесплатных</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{AVG_RATING}</div>
        <div class="stat-label">Средний рейтинг</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{PLATFORMS}</div>
        <div class="stat-label">Платформ</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    import altair as alt

    _BLUE = "#4c9be8"
    _BG   = "#13131a"

    def _bar(data, h=220, angle=-30):
        df_p = data.reset_index()
        df_p.columns = ["Категория", "Курсов"]
        return (
            alt.Chart(df_p)
            .mark_bar(color=_BLUE, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Категория:N", sort=None, axis=alt.Axis(labelAngle=angle, title=None)),
                y=alt.Y("Курсов:Q", axis=alt.Axis(title=None)),
                tooltip=["Категория", "Курсов"],
            )
            .properties(height=h, background=_BG)
            .configure_view(stroke="transparent")
            .configure_axis(labelColor="#a0a0b8", gridColor="rgba(255,255,255,0.06)",
                            domainColor="transparent", tickColor="transparent")
        )

    # ── Ряд 1: платформы + языки ──────────────────────────────────────────────
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown('<div class="chart-panel"><div class="chart-panel-title">По платформам</div>', unsafe_allow_html=True)
        st.altair_chart(_bar(source_counts), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="chart-panel"><div class="chart-panel-title">По языкам</div>', unsafe_allow_html=True)
        lang_d = lang_counts.rename(index={"ru": "Русский", "en": "Английский"})
        st.altair_chart(_bar(lang_d, angle=0), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Ряд 2: сложность + ценовые категории ─────────────────────────────────
    c3, c4 = st.columns(2, gap="medium")
    with c3:
        st.markdown('<div class="chart-panel"><div class="chart-panel-title">По уровню сложности</div>', unsafe_allow_html=True)
        diff_d = diff_counts.rename(index={"Beginner": "Начинающий", "Intermediate": "Средний", "Advanced": "Продвинутый"})
        st.altair_chart(_bar(diff_d, angle=0), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="chart-panel"><div class="chart-panel-title">По ценовым категориям</div>', unsafe_allow_html=True)
        price_counts = df["price_category"].value_counts().rename("Курсов")
        st.altair_chart(_bar(price_counts, angle=-20), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Ряд 3: длительность + популярность ───────────────────────────────────
    c5, c6 = st.columns(2, gap="medium")
    with c5:
        st.markdown('<div class="chart-panel"><div class="chart-panel-title">По длительности курса</div>', unsafe_allow_html=True)
        dur_order = ["Короткий (<1 мес)", "Средний (1–3 мес)", "Длинный (>3 мес)", "Не указана"]
        dur_counts = df["duration_category"].value_counts().reindex(dur_order).dropna().rename("Курсов")
        st.altair_chart(_bar(dur_counts, angle=-20), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c6:
        st.markdown('<div class="chart-panel"><div class="chart-panel-title">По популярности (кол-во студентов)</div>', unsafe_allow_html=True)
        pop_order = ["Мало (<100)", "Средне (100–1000)", "Популярно (1000–10000)", "Очень популярно (>10000)"]
        pop_counts = df["students_category"].value_counts().reindex(pop_order).dropna().rename("Курсов")
        st.altair_chart(_bar(pop_counts, angle=-20), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Языки программирования ───────────────────────────────────────────────
    prog_counts = df["programming_language"].value_counts().head(15).rename("Курсов")
    if not prog_counts.empty:
        st.markdown('<div class="chart-panel" style="margin-top:16px"><div class="chart-panel-title">Топ-15 языков программирования</div>', unsafe_allow_html=True)
        st.altair_chart(_bar(prog_counts, h=240, angle=-30), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Топ-12 категорий (без Other) ──────────────────────────────────────────
    st.markdown('<div class="chart-panel" style="margin-top:16px"><div class="chart-panel-title">Топ-12 категорий</div>', unsafe_allow_html=True)
    top_cat_clean = (
        df[~df["category"].isin(["Other", "Другое", "Programming / Other"])]
        .groupby("category").size().rename("Курсов")
        .sort_values(ascending=False).head(12)
    )
    st.altair_chart(_bar(top_cat_clean, h=260), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Сводка по платформам ──────────────────────────────────────────────────
    st.markdown('<div class="section-title" style="margin-top:28px">Сводка по платформам</div>', unsafe_allow_html=True)
    platform_detail = (
        df.groupby("source")
          .agg(
              Курсов=("title", "count"),
              Бесплатных=("is_free", "sum"),
              Платных=("is_free", lambda x: (x == 0).sum()),
              Средний_рейтинг=("weighted_rating", "mean"),
              С_оценкой=("has_rating", "sum"),
          )
          .round(2)
          .sort_values("Курсов", ascending=False)
    )
    platform_detail["Бесплатных"] = platform_detail["Бесплатных"].astype(int)
    platform_detail["Платных"]    = platform_detail["Платных"].astype(int)
    platform_detail["С_оценкой"] = platform_detail["С_оценкой"].astype(int)
    st.dataframe(platform_detail, use_container_width=True)

# ══════════════════════════════ PAGE: ОЦЕНКА ═════════════════════════════════

elif _page == "eval":

    st.markdown(f"""
    <div class="page-header">
      <div class="page-header-title">Оценка качества</div>
      <div class="page-header-sub">Тестирование по {len(TEST_CASES)} сценариям: языки, фреймворки, направления, русскоязычные и фильтрованные запросы</div>
    </div>
    <div class="metric-desc-grid">
      <div class="metric-desc-card">
        <div class="metric-desc-name">Precision@K</div>
        <div class="metric-desc-text">Доля релевантных результатов среди топ-K выдачи</div>
      </div>
      <div class="metric-desc-card">
        <div class="metric-desc-name">NDCG@K</div>
        <div class="metric-desc-text">Качество ранжирования с учётом позиции результата</div>
      </div>
      <div class="metric-desc-card">
        <div class="metric-desc-name">MRR</div>
        <div class="metric-desc-text">Обратный ранг первого релевантного результата</div>
      </div>
      <div class="metric-desc-card">
        <div class="metric-desc-name">Hit Rate@K</div>
        <div class="metric-desc-text">Доля запросов, где есть хотя бы один релевантный</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    k_val = st.select_slider("K (глубина оценки)", options=[3, 5, 10], value=5)

    col_run, _ = st.columns([2, 6])
    run_btn = col_run.button("Запустить оценку", type="primary")

    if run_btn:
        progress_bar = st.progress(0, text="Запускаем тесты...")
        def update_progress(i, total):
            progress_bar.progress(
                int(i / total * 100),
                text=f"Тест {i} из {total}...",
            )

        with st.spinner("Оцениваем систему..."):
            df_res, agg = run_evaluation(df, k=k_val, progress_cb=update_progress)

        progress_bar.empty()

        if not agg:
            st.error("Не удалось получить результаты.")
        else:
            # ── Агрегированные метрики ────────────────────────────────────────
            st.markdown(f"""
            <div class="stat-grid" style="grid-template-columns:repeat(5,1fr);margin-top:24px">
              <div class="stat-card">
                <div class="stat-value" style="font-size:1.5rem">{agg['mean_precision']:.3f}</div>
                <div class="stat-label">Precision@{k_val}</div>
              </div>
              <div class="stat-card">
                <div class="stat-value" style="font-size:1.5rem">{agg['mean_recall']:.3f}</div>
                <div class="stat-label">Recall@{k_val}</div>
              </div>
              <div class="stat-card">
                <div class="stat-value" style="font-size:1.5rem">{agg['mean_ndcg']:.3f}</div>
                <div class="stat-label">NDCG@{k_val}</div>
              </div>
              <div class="stat-card">
                <div class="stat-value" style="font-size:1.5rem">{agg['mean_mrr']:.3f}</div>
                <div class="stat-label">MRR</div>
              </div>
              <div class="stat-card">
                <div class="stat-value" style="font-size:1.5rem">{agg['mean_hit_rate']:.3f}</div>
                <div class="stat-label">Hit Rate@{k_val}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # ── График NDCG по сценариям ──────────────────────────────────────
            valid_rows = df_res[df_res.get("error", pd.Series("", index=df_res.index)).isna()
                                if "error" in df_res.columns else pd.Series(True, index=df_res.index)]
            if "ndcg" in valid_rows.columns:
                chart_df = (
                    valid_rows[["label", "ndcg", "precision", "hit_rate"]]
                    .dropna()
                    .set_index("label")
                    .sort_values("ndcg", ascending=False)
                )
                st.markdown('<div class="chart-panel" style="margin-top:20px"><div class="chart-panel-title">NDCG@K по сценариям</div>',
                            unsafe_allow_html=True)
                st.bar_chart(chart_df["ndcg"])
                st.markdown('</div>', unsafe_allow_html=True)

            # ── Таблица результатов ───────────────────────────────────────────
            st.markdown('<div class="section-title">Результаты по сценариям</div>',
                        unsafe_allow_html=True)
            show_cols  = [c for c in DISPLAY_COLS if c in df_res.columns]
            display_df = df_res[show_cols].rename(columns=DISPLAY_COLS)
            st.dataframe(display_df, use_container_width=True)

            # ── Дополнительная статистика ─────────────────────────────────────
            st.markdown(f"""
            <div class="stat-grid" style="grid-template-columns:repeat(3,1fr);margin-top:16px">
              <div class="stat-card">
                <div class="stat-value">{agg['n_test_cases']}</div>
                <div class="stat-label">Сценариев</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{agg['n_valid']}</div>
                <div class="stat-label">Успешных</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{agg['success_rate']:.0%}</div>
                <div class="stat-label">Success Rate</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            csv = df_res.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Скачать результаты CSV",
                data=csv,
                file_name="evaluation_results.csv",
                mime="text/csv",
            )

# ─── FOOTER ────────────────────────────────────────────────────────────────────


elif _page == "about":

    st.markdown("""
    <div class="page-header">
      <div class="page-header-title">О системе</div>
      <div class="page-header-sub">Как работает CourseFind и как им пользоваться</div>
    </div>
    """, unsafe_allow_html=True)

    _tab_guide, _tab_how = st.tabs(["📖 Инструкция", "🔧 Как работает алгоритм"])

    with _tab_how:
        st.markdown("""
<div style="margin-top:16px">

<div style="background:#13131a;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:24px;margin-bottom:16px">
<div style="font-size:1.1rem;font-weight:700;color:#f0f0f5;margin-bottom:16px">🧠 Гибридная рекомендательная система</div>
<div style="color:#a0a0b8;line-height:1.7">
CourseFind использует <strong style="color:#a594ff">гибридный подход</strong> — комбинацию трёх методов, чтобы давать точные и разнообразные рекомендации.
</div>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:16px">
<div style="background:#13131a;border:1px solid rgba(165,148,255,0.2);border-radius:12px;padding:18px">
  <div style="font-size:1.5rem;margin-bottom:8px">🔍</div>
  <div style="font-weight:700;color:#f0f0f5;margin-bottom:6px">Шаг 1 — Эмбеддинги</div>
  <div style="font-size:0.82rem;color:#a0a0b8;line-height:1.6">Запрос пользователя переводится в числовой вектор с помощью многоязычной нейросети <strong style="color:#a594ff">paraphrase-multilingual-mpnet-base-v2</strong>. Понимает русский и английский.</div>
</div>
<div style="background:#13131a;border:1px solid rgba(165,148,255,0.2);border-radius:12px;padding:18px">
  <div style="font-size:1.5rem;margin-bottom:8px">📐</div>
  <div style="font-weight:700;color:#f0f0f5;margin-bottom:6px">Шаг 2 — KNN поиск</div>
  <div style="font-size:0.82rem;color:#a0a0b8;line-height:1.6">Алгоритм <strong style="color:#a594ff">K-Nearest Neighbors</strong> находит 200 ближайших курсов по косинусному расстоянию между векторами запроса и курсов.</div>
</div>
<div style="background:#13131a;border:1px solid rgba(165,148,255,0.2);border-radius:12px;padding:18px">
  <div style="font-size:1.5rem;margin-bottom:8px">⚖️</div>
  <div style="font-weight:700;color:#f0f0f5;margin-bottom:6px">Шаг 3 — Ранжирование</div>
  <div style="font-size:0.82rem;color:#a0a0b8;line-height:1.6">Финальный <strong style="color:#a594ff">Hybrid Score</strong> = 70% релевантность + 30% популярность. Байесовский рейтинг устраняет перекос в сторону курсов с мало оценок.</div>
</div>
</div>

<div style="background:#13131a;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:18px;margin-bottom:16px">
  <div style="font-weight:700;color:#f0f0f5;margin-bottom:12px">📊 Датасет</div>
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px">
    <div style="text-align:center"><div style="font-size:1.4rem;font-weight:700;color:#a594ff">7 606</div><div style="font-size:0.75rem;color:#a0a0b8">курсов</div></div>
    <div style="text-align:center"><div style="font-size:1.4rem;font-weight:700;color:#a594ff">4</div><div style="font-size:0.75rem;color:#a0a0b8">платформы</div></div>
    <div style="text-align:center"><div style="font-size:1.4rem;font-weight:700;color:#a594ff">15</div><div style="font-size:0.75rem;color:#a0a0b8">категорий</div></div>
    <div style="text-align:center"><div style="font-size:1.4rem;font-weight:700;color:#a594ff">87%</div><div style="font-size:0.75rem;color:#a0a0b8">Precision@5</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div style="margin-top:4px;margin-bottom:4px">', unsafe_allow_html=True)
        if st.button("Узнать подробнее о датасете →", key="guide_nav_dataset", type="primary", use_container_width=False):
            st.session_state.page = "stats"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
<div style="background:#13131a;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:18px">
  <div style="font-weight:700;color:#f0f0f5;margin-bottom:10px">🛠 Технологии</div>
  <div style="display:flex;flex-wrap:wrap;gap:8px">
    <span style="background:rgba(165,148,255,0.1);border:1px solid rgba(165,148,255,0.3);color:#a594ff;padding:4px 12px;border-radius:20px;font-size:0.8rem">Python</span>
    <span style="background:rgba(165,148,255,0.1);border:1px solid rgba(165,148,255,0.3);color:#a594ff;padding:4px 12px;border-radius:20px;font-size:0.8rem">Streamlit</span>
    <span style="background:rgba(165,148,255,0.1);border:1px solid rgba(165,148,255,0.3);color:#a594ff;padding:4px 12px;border-radius:20px;font-size:0.8rem">Sentence Transformers</span>
    <span style="background:rgba(165,148,255,0.1);border:1px solid rgba(165,148,255,0.3);color:#a594ff;padding:4px 12px;border-radius:20px;font-size:0.8rem">scikit-learn KNN</span>
    <span style="background:rgba(165,148,255,0.1);border:1px solid rgba(165,148,255,0.3);color:#a594ff;padding:4px 12px;border-radius:20px;font-size:0.8rem">pandas / numpy</span>
    <span style="background:rgba(165,148,255,0.1);border:1px solid rgba(165,148,255,0.3);color:#a594ff;padding:4px 12px;border-radius:20px;font-size:0.8rem">Udemy / Stepik / Coursera / OpenEdu</span>
  </div>
</div>

</div>
""", unsafe_allow_html=True)

    with _tab_guide:
        # Hidden navigation + search buttons — clicked via JS from components.html iframe
        _gnav_cols = st.columns(8)
        with _gnav_cols[0]:
            if st.button("↗home", key="guide_nav_home"):
                st.session_state.page = "home"; st.rerun()
        with _gnav_cols[1]:
            if st.button("↗personal", key="guide_nav_personal"):
                st.session_state.page = "personal"; st.rerun()
        with _gnav_cols[2]:
            if st.button("↗stats", key="guide_nav_stats"):
                st.session_state.page = "my"; st.rerun()
        with _gnav_cols[3]:
            if st.button("↗catalog", key="guide_nav_catalog"):
                st.session_state.page = "catalog"; st.rerun()
        with _gnav_cols[4]:
            if st.button("↗notifications", key="guide_nav_notif"):
                st.session_state.page = "notifications"; st.rerun()
        with _gnav_cols[5]:
            if st.button("↗s:ml", key="guide_s_ml"):
                st.session_state.page = "search"; st.session_state.q_text = "machine learning"; st.rerun()
        with _gnav_cols[6]:
            if st.button("↗s:docker", key="guide_s_docker"):
                st.session_state.page = "search"; st.session_state.q_text = "docker для начинающих"; st.rerun()
        with _gnav_cols[7]:
            if st.button("↗s:react", key="guide_s_react"):
                st.session_state.page = "search"; st.session_state.q_text = "react"; st.rerun()

        _gnav_cols2 = st.columns(6)
        with _gnav_cols2[0]:
            if st.button("↗s:python", key="guide_s_python"):
                st.session_state.page = "search"; st.session_state.q_text = "python"; st.rerun()
        with _gnav_cols2[1]:
            if st.button("↗s:web", key="guide_s_web"):
                st.session_state.page = "search"; st.session_state.q_text = "web development"; st.rerun()
        with _gnav_cols2[2]:
            if st.button("↗s:js", key="guide_s_js"):
                st.session_state.page = "search"; st.session_state.q_text = "javascript"; st.rerun()
        with _gnav_cols2[3]:
            if st.button("↗s:ds", key="guide_s_ds"):
                st.session_state.page = "search"; st.session_state.q_text = "data science"; st.rerun()
        with _gnav_cols2[4]:
            if st.button("↗s:devops", key="guide_s_devops"):
                st.session_state.page = "search"; st.session_state.q_text = "devops"; st.rerun()
        with _gnav_cols2[5]:
            if st.button("↗s:sql", key="guide_s_sql"):
                st.session_state.page = "search"; st.session_state.q_text = "sql базы данных"; st.rerun()

        _st_components.html("""
<!DOCTYPE html>
<html>
<head>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: transparent; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
.steps { display: grid; gap: 12px; padding: 4px 0; }
.step { background: #13131a; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; padding: 20px; }
.step-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.step-num { width: 32px; height: 32px; background: linear-gradient(135deg,#7c6bff,#a594ff); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 700; color: #fff; flex-shrink: 0; font-size: 0.95rem; }
.step-title { font-weight: 700; color: #f0f0f5; font-size: 1rem; }
.step-body { color: #a0a0b8; font-size: 0.88rem; line-height: 1.7; padding-left: 44px; }
.step-body strong { color: #f0f0f5; }
.nav-link { color: #a594ff; cursor: pointer; text-decoration: underline dotted rgba(165,148,255,0.5); text-underline-offset: 3px; font-weight: 600; transition: color 0.15s; }
.nav-link:hover { color: #c4b8ff; }
em.ex { color: #a594ff; font-style: italic; }
</style>
</head>
<body>
<div class="steps">

  <div class="step">
    <div class="step-header">
      <div class="step-num">1</div>
      <div class="step-title">Зарегистрируйся и настрой профиль</div>
    </div>
    <div class="step-body">
      Создай аккаунт, выбери аватар, укажи цель обучения и интересующие технологии. Чем точнее профиль — тем лучше рекомендации во вкладке <span class="nav-link" onclick="guideNav('personal')">Для вас</span>.
    </div>
  </div>

  <div class="step">
    <div class="step-header">
      <div class="step-num">2</div>
      <div class="step-title">Найди курс через поиск</div>
    </div>
    <div class="step-body">
      Введи тему на <strong>русском или английском</strong> — система поймёт оба языка. Используй фильтры: платформа, уровень, цена, язык курса. Попробуй прямо сейчас: <span class="nav-link" onclick="guideSearch('ml')">Machine Learning</span>, <span class="nav-link" onclick="guideSearch('web')">Web Development</span>, <span class="nav-link" onclick="guideSearch('python')">Python</span>.
    </div>
  </div>

  <div class="step">
    <div class="step-header">
      <div class="step-num">3</div>
      <div class="step-title">Сохраняй курсы и отслеживай прогресс</div>
    </div>
    <div class="step-body">
      Нажми <strong>Сохр.</strong> чтобы добавить курс в список, <strong>Начать</strong> — чтобы отметить начало. В разделе <span class="nav-link" onclick="guideNav('stats')">Моё</span> меняй статус курса, выставляй оценку от 1 до 5 и следи за общим прогрессом.
    </div>
  </div>

  <div class="step">
    <div class="step-header">
      <div class="step-num">4</div>
      <div class="step-title">Получай персональные рекомендации</div>
    </div>
    <div class="step-body">
      Чем больше курсов сохранишь — тем точнее рекомендации. Раздел <span class="nav-link" onclick="guideNav('personal')">Для вас</span> подбирает курсы на основе твоей истории. На <span class="nav-link" onclick="guideNav('home')">Главной</span> тоже появится персональная подборка.
    </div>
  </div>

  <div class="step">
    <div class="step-header">
      <div class="step-num">5</div>
      <div class="step-title">Зарабатывай XP и прокачивай уровень</div>
    </div>
    <div class="step-body">
      За каждое действие — поиск, сохранение, начало курса, оценка — начисляются <strong>очки XP</strong>. Выполняй <strong>задания недели</strong> для бонусного XP. Уровни: Новичок → Средний → Продвинутый → Профессионал → Эксперт.
    </div>
  </div>

  <div class="step">
    <div class="step-header">
      <div class="step-num">6</div>
      <div class="step-title">Исследуй каталог по темам</div>
    </div>
    <div class="step-body">
      В разделе <span class="nav-link" onclick="guideNav('catalog')">Каталог</span> все курсы разбиты по 15 темам — Python, Data Science, DevOps, Веб-разработка и другие. Используй фильтры: <strong>Бесплатные</strong>, <strong>Топ рейтинг</strong>, <strong>На русском</strong> и по платформам. Нажми <strong>Показать все →</strong> чтобы увидеть все курсы раздела.
    </div>
  </div>

  <div class="step">
    <div class="step-header">
      <div class="step-num">7</div>
      <div class="step-title">Находи похожие курсы одним нажатием</div>
    </div>
    <div class="step-body">
      На карточке курса нажми <strong>Похожие</strong> — система мгновенно найдёт 10 курсов с похожей тематикой через семантический поиск. Отлично работает когда нашёл что-то интересное и хочешь изучить тему глубже.
    </div>
  </div>

  <div class="step">
    <div class="step-header">
      <div class="step-num">8</div>
      <div class="step-title">Следи за активностью в уведомлениях</div>
    </div>
    <div class="step-body">
      В разделе <span class="nav-link" onclick="guideNav('notifications')">Уведомления</span> отображается вся активность: полученные значки, выполненные задания, новые достижения. Нажми на значок 🔔 в шапке чтобы быстро открыть ленту.
    </div>
  </div>

</div>

<script>
var _LABELS = {
  'home': '\u2197home',
  'personal': '\u2197personal',
  'stats': '\u2197stats',
  'catalog': '\u2197catalog',
  'notifications': '\u2197notifications',
  'ml': '\u2197s:ml',
  'docker': '\u2197s:docker',
  'react': '\u2197s:react',
  'python': '\u2197s:python',
  'web': '\u2197s:web',
  'js': '\u2197s:js',
  'ds': '\u2197s:ds',
  'devops': '\u2197s:devops',
  'sql': '\u2197s:sql'
};

function _clickParentBtn(label) {
  try {
    var btns = window.parent.document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
      if (btns[i].innerText.trim() === label) { btns[i].click(); return; }
    }
  } catch(e) { console.warn('guideNav error:', e); }
}

function guideNav(page) { _clickParentBtn(_LABELS[page]); }
function guideSearch(q) { _clickParentBtn(_LABELS[q]); }

(function() {
  var _ALL = Object.values(_LABELS);
  function _hide() {
    try {
      window.parent.document.querySelectorAll('button').forEach(function(b) {
        if (_ALL.indexOf(b.innerText.trim()) !== -1) {
          var row = b.closest('[data-testid="stHorizontalBlock"]');
          if (row) row.style.setProperty('display','none','important');
        }
      });
    } catch(e) {}
  }
  _hide(); setTimeout(_hide,300); setTimeout(_hide,800);
})();
</script>
</body>
</html>
""", height=1200, scrolling=False)


st.markdown(f"""
<div class="app-footer">
  <div class="footer-brand">CourseFind</div>
  <div class="footer-meta">Гибридная рекомендательная система · {TOTAL:,} курсов · Stepik · Udemy · Coursera · OpenEdu</div>
</div>
""", unsafe_allow_html=True)
