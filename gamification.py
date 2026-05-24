import json
import os
import re as _re
from datetime import date, datetime, timedelta
import pandas as pd

PROFILES_DIR = "user_profiles"

ACHIEVEMENTS = [
    {"id": "first_search",    "icon": "🔍", "title": "Первопроходец",      "desc": "Сделай первый поиск"},
    {"id": "streak_3",        "icon": "🔥", "title": "3 дня подряд",        "desc": "Заходи 3 дня подряд"},
    {"id": "streak_7",        "icon": "⚡", "title": "Неделя!",             "desc": "Заходи 7 дней подряд"},
    {"id": "streak_30",       "icon": "💎", "title": "Месяц!",              "desc": "Заходи 30 дней подряд"},
    {"id": "started_1",       "icon": "🚀", "title": "Поехали!",            "desc": "Начни первый курс"},
    {"id": "started_5",       "icon": "📚", "title": "Книжный червь",       "desc": "Начни 5 курсов"},
    {"id": "completed_1",     "icon": "🎓", "title": "Выпускник",           "desc": "Заверши первый курс"},
    {"id": "xp_100",          "icon": "⭐", "title": "100 XP",              "desc": "Набери 100 XP"},
    {"id": "xp_500",          "icon": "🌟", "title": "500 XP",              "desc": "Набери 500 XP"},
    {"id": "xp_2000",         "icon": "💫", "title": "2000 XP",             "desc": "Набери 2000 XP"},
    {"id": "xp_7000",         "icon": "🔮", "title": "7000 XP",             "desc": "Набери 7000 XP"},
    {"id": "xp_20000",        "icon": "👑", "title": "20000 XP",            "desc": "Набери 20000 XP"},
    {"id": "xp_45000",        "icon": "🌠", "title": "45000 XP",            "desc": "Набери 45000 XP"},
    {"id": "searches_10",     "icon": "🧭", "title": "Исследователь",       "desc": "Сделай 10 поисков"},
    {"id": "goal_set",        "icon": "🎯", "title": "С целью!",            "desc": "Укажи цель обучения"},
    {"id": "course_of_day",   "icon": "📅", "title": "По расписанию",       "desc": "Открой курс дня"},
    {"id": "explorer",        "icon": "🌍", "title": "Исследователь миров", "desc": "Начни курсы в 3 разных направлениях"},
    {"id": "weekly_3",        "icon": "📆", "title": "Активная неделя",     "desc": "Открой 3 курса за неделю"},
    {"id": "weekly_5",        "icon": "🏆", "title": "Чемпион недели",      "desc": "Открой 5 курсов за неделю"},
    {"id": "saved_10",        "icon": "🔖", "title": "Коллекционер",        "desc": "Сохрани 10 курсов"},
]

WEEKLY_QUESTS = [
    {"id": "wq_open_3",    "title": "Открой 3 курса за неделю",   "target": 3,  "xp": 80,  "icon": "📖"},
    {"id": "wq_open_5",    "title": "Открой 5 курсов за неделю",  "target": 5,  "xp": 150, "icon": "🏆"},
    {"id": "wq_streak_5",  "title": "Заходи 5 дней подряд",       "target": 5,  "xp": 100, "icon": "🔥"},
    {"id": "wq_save_3",    "title": "Сохрани 3 курса за неделю",  "target": 3,  "xp": 50,  "icon": "🔖"},
]

ACHIEVEMENT_MAP = {a["id"]: a for a in ACHIEVEMENTS}

XP_REWARDS = {
    "start_course":    30,
    "complete_course": 150,
    "daily_login":     15,
    "course_of_day":   25,
    "set_goal":        20,
}


def _path(user_id: str) -> str:
    return os.path.join(PROFILES_DIR, f"{user_id}.json")


def _load(user_id: str) -> dict:
    p = _path(user_id)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(user_id: str, data: dict):
    with open(_path(user_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _push_notif(data: dict, text: str, icon: str = "", category: str = "info"):
    data.setdefault("notifications", []).append({
        "text":     text,
        "icon":     icon,
        "category": category,
        "ts":       datetime.now().isoformat(),
        "read":     False,
    })


def _get_gamif(data: dict) -> dict:
    if "gamification" not in data:
        data["gamification"] = {
            "streak": 0,
            "last_visit": "",
            "xp": 0,
            "achievements": [],
            "total_searches": 0,
            "course_of_day_opened": "",
        }
    return data["gamification"]


def update_streak(user_id: str) -> dict:
    data = _load(user_id)
    g = _get_gamif(data)

    today = date.today().isoformat()
    last  = g.get("last_visit", "")
    xp_gained = 0
    new_achievements = []

    _cur_week = _week_start()
    wdata = g.setdefault("weekly", {})
    if wdata.get("week_start") != _cur_week:
        wdata.clear()
        wdata["week_start"]     = _cur_week
        wdata["courses_opened"] = 0
        wdata["courses_saved"]  = 0
        wdata["claimed"]        = []
        wdata["days_visited"]   = []
    _visited = wdata.setdefault("days_visited", [])
    if today not in _visited:
        _visited.append(today)

    if last == today:
        _save(user_id, data)
        return {"streak": g["streak"], "xp_gained": 0, "new_achievements": []}

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    if last == yesterday:
        g["streak"] += 1
    elif last == "":
        g["streak"] = 1
    else:
        g["streak"] = 1  # пропустил день — сброс

    g["last_visit"] = today
    xp_gained += XP_REWARDS["daily_login"]
    g["xp"] = g.get("xp", 0) + xp_gained

    for sid, days in [("streak_3", 3), ("streak_7", 7), ("streak_30", 30)]:
        if g["streak"] >= days and sid not in g["achievements"]:
            g["achievements"].append(sid)
            new_achievements.append(sid)
            _ach = ACHIEVEMENT_MAP.get(sid, {})
            _push_notif(data,
                f"Достижение разблокировано: {_ach.get('title','')}",
                icon=_ach.get("icon", "🏆"), category="achievement")

    _save(user_id, data)
    return {"streak": g["streak"], "xp_gained": xp_gained, "new_achievements": new_achievements}


def get_streak(user_id: str) -> int:
    data = _load(user_id)
    g = _get_gamif(data)
    return g.get("streak", 0)


def add_xp(user_id: str, action: str) -> dict:
    data = _load(user_id)
    g = _get_gamif(data)
    new_achievements = []

    amount = XP_REWARDS.get(action, 0)
    xp_before = g.get("xp", 0)
    g["xp"] = xp_before + amount

    _level_thresholds = [0, 500, 1200, 2500, 4500, 7500, 11000, 16000, 22000, 30000]
    _level_titles     = ["Новичок", "Студент", "Знаток", "Практик", "Эксперт", "Профессионал", "Мастер", "Гуру", "Элита", "Легенда"]
    _level_icons      = ["⬆️", "⬆️", "⬆️", "⬆️", "⬆️", "⬆️", "⬆️"]
    _level_before = sum(1 for t in _level_thresholds if xp_before >= t) - 1
    _level_after  = sum(1 for t in _level_thresholds if g["xp"] >= t) - 1
    if _level_after > _level_before:
        _new_title = _level_titles[_level_after]
        _new_icon  = _level_icons[min(_level_after, len(_level_icons) - 1)]
        _push_notif(data,
            f"Новый уровень: {_new_title}! ({g['xp']} XP)",
            icon=_new_icon, category="level")

    if action == "search":
        g["total_searches"] = g.get("total_searches", 0) + 1
        if g["total_searches"] == 1 and "first_search" not in g["achievements"]:
            g["achievements"].append("first_search")
            new_achievements.append("first_search")
            _push_notif(data, "Достижение разблокировано: Первопроходец",
                icon="🔍", category="achievement")
        if g["total_searches"] >= 10 and "searches_10" not in g["achievements"]:
            g["achievements"].append("searches_10")
            new_achievements.append("searches_10")
            _push_notif(data, "Достижение разблокировано: Исследователь",
                icon="🔎", category="achievement")

    for xid, threshold in [("xp_100", 100), ("xp_500", 500), ("xp_2000", 2000), ("xp_7000", 7000), ("xp_20000", 20000), ("xp_45000", 45000)]:
        if g["xp"] >= threshold and xid not in g["achievements"]:
            g["achievements"].append(xid)
            new_achievements.append(xid)
            _ach = ACHIEVEMENT_MAP.get(xid, {})
            _push_notif(data,
                f"Достижение разблокировано: {_ach.get('title','')}",
                icon=_ach.get("icon", "🏆"), category="achievement")

    _save(user_id, data)
    return {"xp": g["xp"], "new_achievements": new_achievements}


def get_xp(user_id: str) -> int:
    data = _load(user_id)
    return _get_gamif(data).get("xp", 0)


def unlock_achievement(user_id: str, achievement_id: str) -> bool:
    data = _load(user_id)
    g = _get_gamif(data)
    if achievement_id not in g["achievements"]:
        g["achievements"].append(achievement_id)
        _ach = ACHIEVEMENT_MAP.get(achievement_id, {})
        if _ach:
            _push_notif(data,
                f"Достижение разблокировано: {_ach.get('title', '')}",
                icon=_ach.get("icon", "🏆"), category="achievement")
        _save(user_id, data)
        return True
    return False


def get_achievements(user_id: str) -> list:
    data = _load(user_id)
    g = _get_gamif(data)
    unlocked = set(g.get("achievements", []))
    result = []
    for a in ACHIEVEMENTS:
        result.append({**a, "unlocked": a["id"] in unlocked})
    return result


_GOAL_KW = {
    "Веб-разработка":             ["web", "html", "css", "javascript", "frontend", "backend", "react", "django", "flask"],
    "Data Science / ML":          ["data", "machine learning", "ml", "deep learning", "neural", "tensorflow", "pandas"],
    "Мобильная разработка":       ["mobile", "android", "ios", "kotlin", "swift", "flutter"],
    "DevOps":                     ["devops", "docker", "kubernetes", "linux", "ci/cd", "ansible"],
    "Системное программирование": ["c++", "rust", "embedded", "system"],
    "Базы данных":                ["sql", "postgresql", "mysql", "database", "mongodb"],
    "Кибербезопасность":          ["security", "cybersecurity", "hacking", "pentest"],
}


def get_course_of_day(df, profile=None) -> dict:
    today_seed = int(date.today().strftime("%Y%m%d"))
    pool = df.copy()

    if profile is not None:
        onb       = profile.get_onboarding() if hasattr(profile, "get_onboarding") else {}
        level     = onb.get("level", "")
        languages = onb.get("languages", [])
        goals     = onb.get("goals", [])

        if level and "difficulty" in pool.columns:
            lvl_pool = pool[pool["difficulty"] == level]
            if len(lvl_pool) >= 5:
                pool = lvl_pool

        if languages:
            mask = pd.Series(False, index=pool.index)
            for lang in languages:
                pat = _re.escape(lang.lower())
                if "title" in pool.columns:
                    mask |= pool["title"].str.lower().str.contains(pat, na=False)
                if "programming_language" in pool.columns:
                    mask |= pool["programming_language"].fillna("").str.lower().str.contains(pat, na=False)
            if mask.sum() >= 5:
                pool = pool[mask]

        if goals:
            goal_keywords = []
            for g in goals:
                goal_keywords.extend(_GOAL_KW.get(g, []))
            if goal_keywords and "title" in pool.columns:
                gmask = pd.Series(False, index=pool.index)
                for kw in goal_keywords:
                    gmask |= pool["title"].str.lower().str.contains(_re.escape(kw), na=False)
                    if "category" in pool.columns:
                        gmask |= pool["category"].str.lower().fillna("").str.contains(_re.escape(kw), na=False)
                if gmask.sum() >= 5:
                    pool = pool[gmask]

    if "weighted_rating" in pool.columns:
        filtered = pool[pool["weighted_rating"] >= 3.5]
        pool = filtered if len(filtered) >= 5 else pool
    top = pool.nlargest(200, "weighted_rating") if "weighted_rating" in pool.columns else pool.head(200)
    idx = today_seed % len(top)
    row = top.iloc[idx]
    return row.to_dict()


def mark_course_of_day_opened(user_id: str) -> list:
    data = _load(user_id)
    g = _get_gamif(data)
    today = date.today().isoformat()
    new_achievements = []

    if g.get("course_of_day_opened") != today:
        g["course_of_day_opened"] = today
        g["xp"] = g.get("xp", 0) + XP_REWARDS["course_of_day"]
        if "course_of_day" not in g["achievements"]:
            g["achievements"].append("course_of_day")
            new_achievements.append("course_of_day")
        _save(user_id, data)

    return new_achievements


def add_notification(user_id: str, text: str, icon: str = "", category: str = "info"):
    data = _load(user_id)
    notifs = data.setdefault("notifications", [])
    notifs.append({
        "text":     text,
        "icon":     icon,
        "category": category,
        "ts":       datetime.now().isoformat(),
        "read":     False,
    })
    _save(user_id, data)


def get_notifications(user_id: str) -> list:
    data = _load(user_id)
    return list(reversed(data.get("notifications", [])))


def unread_count(user_id: str) -> int:
    data = _load(user_id)
    return sum(1 for n in data.get("notifications", []) if not n.get("read"))


def mark_all_read(user_id: str):
    data = _load(user_id)
    for n in data.get("notifications", []):
        n["read"] = True
    _save(user_id, data)


def clear_notifications(user_id: str):
    data = _load(user_id)
    data["notifications"] = []
    _save(user_id, data)


def _week_start() -> str:
    today = date.today()
    return (today - timedelta(days=today.weekday())).isoformat()


def get_weekly_progress(user_id: str) -> list:
    data = _load(user_id)
    g    = _get_gamif(data)
    week = _week_start()
    wdata = g.setdefault("weekly", {})

    if wdata.get("week_start") != week:
        wdata.clear()
        wdata["week_start"] = week
        wdata["courses_opened"] = 0
        wdata["courses_saved"]  = 0
        wdata["claimed"]        = []
        _save(user_id, data)

    streak = g.get("streak", 0)
    result = []
    for q in WEEKLY_QUESTS:
        if q["id"] == "wq_open_3" or q["id"] == "wq_open_5":
            progress = wdata.get("courses_opened", 0)
        elif q["id"] == "wq_streak_5":
            progress = min(len(wdata.get("days_visited", [])), q["target"])
        elif q["id"] == "wq_save_3":
            progress = wdata.get("courses_saved", 0)
        else:
            progress = 0
        result.append({
            **q,
            "progress": min(progress, q["target"]),
            "done":     progress >= q["target"],
            "claimed":  q["id"] in wdata.get("claimed", []),
        })
    return result


def track_weekly_course_opened(user_id: str):
    data = _load(user_id)
    g    = _get_gamif(data)
    week = _week_start()
    wdata = g.setdefault("weekly", {})
    if wdata.get("week_start") != week:
        wdata.clear()
        wdata["week_start"]      = week
        wdata["courses_opened"]  = 0
        wdata["courses_saved"]   = 0
        wdata["claimed"]         = []
    wdata["courses_opened"] = wdata.get("courses_opened", 0) + 1

    opened = wdata["courses_opened"]
    new_achievements = []
    if opened >= 3 and "weekly_3" not in g["achievements"]:
        g["achievements"].append("weekly_3")
        new_achievements.append("weekly_3")
        _push_notif(data, "Достижение: Активная неделя! 3 курса за неделю", icon="📆", category="achievement")
    if opened >= 5 and "weekly_5" not in g["achievements"]:
        g["achievements"].append("weekly_5")
        new_achievements.append("weekly_5")
        _push_notif(data, "Достижение: Чемпион недели! 5 курсов за неделю", icon="🏆", category="achievement")
    _save(user_id, data)
    return new_achievements


def track_weekly_course_saved(user_id: str):
    data = _load(user_id)
    g    = _get_gamif(data)
    week = _week_start()
    wdata = g.setdefault("weekly", {})
    if wdata.get("week_start") != week:
        wdata.clear()
        wdata["week_start"]     = week
        wdata["courses_opened"] = 0
        wdata["courses_saved"]  = 0
        wdata["claimed"]        = []
    wdata["courses_saved"] = wdata.get("courses_saved", 0) + 1

    new_achievements = []
    if wdata["courses_saved"] >= 10 and "saved_10" not in g["achievements"]:
        g["achievements"].append("saved_10")
        new_achievements.append("saved_10")
        _push_notif(data, "Достижение: Коллекционер! 10 сохранённых курсов", icon="🔖", category="achievement")
    _save(user_id, data)
    return new_achievements


def claim_weekly_quest(user_id: str, quest_id: str) -> int:
    data = _load(user_id)
    g    = _get_gamif(data)
    wdata = g.setdefault("weekly", {})
    if quest_id in wdata.get("claimed", []):
        return 0
    quest = next((q for q in WEEKLY_QUESTS if q["id"] == quest_id), None)
    if not quest:
        return 0
    wdata.setdefault("claimed", []).append(quest_id)
    xp = quest["xp"]
    g["xp"] = g.get("xp", 0) + xp
    _push_notif(data, f"Получено {xp} XP за задание: {quest['title']}", icon="🎁", category="achievement")
    _save(user_id, data)
    return xp


def check_streak_warning(user_id: str) -> bool:
    data = _load(user_id)
    g    = _get_gamif(data)
    streak = g.get("streak", 0)
    if streak < 2:
        return False
    last = g.get("last_visit", "")
    if not last:
        return False
    today     = date.today()
    last_date = date.fromisoformat(last)
    diff = (today - last_date).days
    return diff == 1


def xp_level(xp: int) -> dict:
    thresholds = [0, 500, 1200, 2500, 4500, 7500, 11000, 16000, 22000, 30000]
    titles     = ["Новичок", "Студент", "Знаток", "Практик", "Эксперт", "Профессионал", "Мастер", "Гуру", "Элита", "Легенда"]
    level = 0
    for i, t in enumerate(thresholds):
        if xp >= t:
            level = i
    current_min = thresholds[level]
    next_min    = thresholds[level + 1] if level + 1 < len(thresholds) else thresholds[-1]
    progress    = (xp - current_min) / max(next_min - current_min, 1)
    return {
        "level":    level + 1,
        "title":    titles[level],
        "xp":       xp,
        "progress": min(progress, 1.0),
        "next_xp":  next_min,
    }
