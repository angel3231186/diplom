"""
Модуль персонализации рекомендательной системы
===============================================
Хранит историю пользователя и адаптирует рекомендации.

Что запоминает:
  - просмотренные курсы
  - лайкнутые курсы
  - категории и навыки которые интересуют
  - предпочтения по языку, уровню, источнику

Как влияет на рекомендации:
  - курсы из любимых категорий получают бонус к скору
  - уже просмотренные курсы понижаются
  - дизлайкнутые курсы получают сильный штраф
  - лайкнутые курсы используются как "эталон" для поиска похожих

Хранение: JSON файл на диске (легко заменить на БД)

УЛУЧШЕНИЯ v2:
  - get_preferences: добавлен decay (свежие действия весят больше)
  - personalize_scores: штраф за просмотренные снижен 0.4→0.2
    (чтобы не прятать хорошие курсы которые просто открыли)
  - recommend_by_likes: сортировка учитывает hybrid_score,
    убраны курсы с рейтингом 0.0
  - UserProfile.summary: показывает топ-3 категории вместо 2
  - ProfileManager: добавлен метод get_stats для дипломной отчётности
"""

import json
import os
import math
import re
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from collections import Counter


PROFILES_DIR = "user_profiles"
os.makedirs(PROFILES_DIR, exist_ok=True)

FAKE_RATING = 3.72  # дефолтный рейтинг без реальных оценок

# Профиль пользователя

class UserProfile:
    """
    Хранит историю действий пользователя и его предпочтения.

    Пример:
        profile = UserProfile("user_123")
        profile.add_view("Python для начинающих", "Programming", "Beginner", "ru")
        profile.add_like("Machine Learning A-Z", "Data Science / ML / AI", "Intermediate", "en")
        prefs = profile.get_preferences()
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.path    = os.path.join(PROFILES_DIR, f"{user_id}.json")
        self.data    = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "user_id":    self.user_id,
            "created_at": datetime.now().isoformat(),
            "views":      [],
            "likes":      [],
            "searches":   [],
            "dislikes":   [],
            "saved":      [],
        }

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ── Действия ──────────────────────────────────────────────────────────────

    def add_view(self, title: str, category: str = "", difficulty: str = "",
                 language: str = "", source: str = ""):
        self.data["views"].append({
            "title": title, "category": category,
            "difficulty": difficulty, "language": language,
            "source": source,
            "ts": datetime.now().isoformat()
        })
        self.data["views"] = self.data["views"][-200:]  # увеличен лимит с 100
        self.save()

    def add_like(self, title: str, category: str = "", difficulty: str = "",
                 language: str = "", source: str = ""):
        existing = {a["title"] for a in self.data["likes"]}
        if title in existing:
            return
        self.data["likes"].append({
            "title": title, "category": category,
            "difficulty": difficulty, "language": language,
            "source": source,
            "ts": datetime.now().isoformat()
        })
        self.data["likes"] = self.data["likes"][-50:]
        self.save()

    def add_saved(self, course_row: dict):
        """Сохраняет курс в список для изучения."""
        existing = {a["title"] for a in self.data.get("saved", [])}
        if course_row.get("title") in existing:
            return
        entry = {
            "title":      course_row.get("title", ""),
            "source":     course_row.get("source", ""),
            "category":   course_row.get("category", ""),
            "difficulty": course_row.get("difficulty", ""),
            "language":   course_row.get("language", ""),
            "is_free":    course_row.get("is_free", 0),
            "price":      course_row.get("price", 0),
            "duration_category": course_row.get("duration_category", ""),
            "weighted_rating":   course_row.get("weighted_rating", 0),
            "url":        course_row.get("url", ""),
            "organization": course_row.get("organization", ""),
            "ts":         datetime.now().isoformat(),
        }
        self.data.setdefault("saved", []).append(entry)
        self.save()

    def remove_saved(self, title: str):
        """Удаляет курс из списка для изучения."""
        self.data["saved"] = [
            s for s in self.data.get("saved", []) if s.get("title") != title
        ]
        self.save()

    def get_saved(self) -> list:
        return self.data.get("saved", [])

    def get_started(self) -> list:
        return self.data.get("started", [])

    def add_started(self, title: str, url: str = "", source: str = ""):
        existing = {a["title"] for a in self.data.get("started", [])}
        if title in existing:
            return
        self.data.setdefault("started", []).append({
            "title": title, "url": url, "source": source,
            "progress": 0,
            "started_at": datetime.now().isoformat(),
        })
        self.save()

    def update_started_progress(self, title: str, progress: int):
        for item in self.data.get("started", []):
            if item["title"] == title:
                item["progress"] = progress
                break
        self.save()

    def remove_started(self, title: str):
        self.data["started"] = [
            i for i in self.data.get("started", []) if i["title"] != title
        ]
        self.save()

    def add_rating(self, title: str, stars: int, url: str = "", source: str = ""):
        """Сохраняет оценку пользователя (1–5 звёзд). Перезаписывает если уже есть."""
        ratings = self.data.setdefault("user_ratings", [])
        for r in ratings:
            if r["title"] == title:
                r["stars"] = stars
                r["ts"] = datetime.now().isoformat()
                self.save()
                return
        ratings.append({
            "title": title,
            "stars": stars,
            "url": url,
            "source": source,
            "ts": datetime.now().isoformat(),
        })
        self.save()

    def get_ratings(self) -> list:
        return self.data.get("user_ratings", [])

    def get_completed(self) -> list:
        """Возвращает курсы с прогрессом 100%."""
        return [s for s in self.data.get("started", []) if s.get("progress", 0) == 100]

    def remove_like(self, title: str):
        self.data["likes"] = [a for a in self.data.get("likes", []) if a["title"] != title]
        self.save()

    def add_dislike(self, title: str):
        # Не добавляем дубликаты
        existing = {a["title"] for a in self.data.get("dislikes", [])}
        if title not in existing:
            self.data["dislikes"].append({
                "title": title,
                "ts": datetime.now().isoformat()
            })
            self.save()

    def remove_dislike(self, title: str):
        self.data["dislikes"] = [d for d in self.data.get("dislikes", []) if d["title"] != title]
        self.save()

    def add_search(self, query: str):
        if not query.strip():
            return
        self.data["searches"].append({
            "query": query.strip(),
            "ts": datetime.now().isoformat()
        })
        self.data["searches"] = self.data["searches"][-100:]
        self.save()

    def remove_search(self, index: int):
        """Удаляет один запрос из истории по индексу."""
        searches = self.data.get("searches", [])
        if 0 <= index < len(searches):
            del searches[index]
            self.save()

    def clear_searches(self):
        """Очищает только историю поиска."""
        self.data["searches"] = []
        self.save()

    def clear_history(self):
        self.data["views"]    = []
        self.data["likes"]    = []
        self.data["searches"] = []
        self.data["dislikes"] = []
        self.save()

    # ── Онбординг ─────────────────────────────────────────────────────────────

    def set_onboarding(self, level: str, languages: list, goals: list):
        """Сохраняет результаты анкеты при первом входе."""
        self.data["onboarding"] = {
            "level":        level,
            "languages":    languages,
            "goals":        goals,
            "completed_at": datetime.now().isoformat(),
        }
        self.save()

    def is_onboarded(self) -> bool:
        return bool(self.data.get("onboarding"))

    def get_onboarding(self) -> dict:
        return self.data.get("onboarding", {})

    # ── Мета-профиль (bio, goal, avatar) ──────────────────────────────────────

    def get_profile_meta(self) -> dict:
        return self.data.get("profile_meta", {})

    def set_profile_meta(self, bio: str = "", goal: str = "", avatar: str = "", display_name: str = "", display_name_changed_at: str = ""):
        existing = self.data.get("profile_meta", {})
        self.data["profile_meta"] = {
            "bio":        bio,
            "goal":       goal,
            "avatar":     avatar,
            "display_name": display_name,
            "display_name_changed_at": display_name_changed_at or existing.get("display_name_changed_at", ""),
            "updated_at": datetime.now().isoformat(),
        }
        self.save()

    # ── Анализ предпочтений ────────────────────────────────────────────────────

    def get_preferences(self, decay_days: float = 30.0) -> dict:
        """
        Анализирует историю и возвращает предпочтения пользователя.

        УЛУЧШЕНО: временной decay — свежие действия весят больше старых.
        Лайки весят в 3x больше просмотров.

        decay_days: период полураспада (действие 30 дней назад весит в 2 раза меньше)
        """
        now = datetime.now()

        def time_weight(ts_str: str, base_weight: float) -> float:
            """Умножает базовый вес на decay-коэффициент по времени."""
            try:
                ts   = datetime.fromisoformat(ts_str)
                days = (now - ts).total_seconds() / 86400
                return base_weight * math.exp(-0.693 * days / decay_days)
            except Exception:
                return base_weight

        all_actions = (
            [(a, time_weight(a.get("ts", ""), 3.0)) for a in self.data["likes"]] +
            [(a, time_weight(a.get("ts", ""), 1.0)) for a in self.data["views"]]
        )

        if not all_actions:
            return {}

        categories   = Counter()
        difficulties = Counter()
        languages    = Counter()
        sources      = Counter()

        for action, weight in all_actions:
            if action.get("category"):
                categories[action["category"]]   += weight
            if action.get("difficulty"):
                difficulties[action["difficulty"]] += weight
            if action.get("language"):
                languages[action["language"]]     += weight
            if action.get("source"):
                sources[action["source"]]         += weight

        total_w = sum(w for _, w in all_actions)

        return {
            "top_categories":   [c for c, _ in categories.most_common(3)],
            "top_difficulty":   difficulties.most_common(1)[0][0] if difficulties else None,
            "top_language":     languages.most_common(1)[0][0] if languages else None,
            "top_source":       sources.most_common(1)[0][0] if sources else None,
            "viewed_titles":    [a["title"] for a in self.data["views"]],
            "liked_titles":     [a["title"] for a in self.data["likes"]],
            "disliked_titles":  [a["title"] for a in self.data.get("dislikes", [])],
            "recent_queries":   [s["query"] for s in self.data["searches"][-5:]],
            "total_actions":    int(total_w),
            "category_weights": dict(categories),
            "language_weights": dict(languages),
        }

    def has_history(self) -> bool:
        return bool(self.data.get("views") or self.data.get("likes"))

    def summary(self) -> str:
        prefs = self.get_preferences()
        if not prefs:
            return "История пуста"
        parts = []
        if prefs.get("top_categories"):
            # УЛУЧШЕНО: показываем до 3 категорий
            cats = prefs["top_categories"][:3]
            parts.append(f"Категории: {', '.join(cats)}")
        if prefs.get("top_language"):
            lang = "Русский" if prefs["top_language"] == "ru" else "Английский"
            parts.append(f"Язык: {lang}")
        if prefs.get("top_difficulty"):
            parts.append(f"Уровень: {prefs['top_difficulty']}")
        parts.append(f"Лайков: {len(self.data['likes'])}")
        parts.append(f"Просмотров: {len(self.data['views'])}")
        return " · ".join(parts)

# Персонализированное ранжирование

def personalize_scores(
    candidates:     pd.DataFrame,
    profile:        UserProfile,
    base_score_col: str   = "final_score",
    weight:         float = 0.25,
) -> pd.DataFrame:
    """
    Корректирует скоры кандидатов на основе профиля пользователя.

    Бонусы:
      +0.30  — курс из любимой категории (пропорционально весу)
      +0.15  — курс на предпочтительном языке (если >60% истории)
      +0.10  — курс нужного уровня сложности
      +0.20  — курс лайкнут (напоминание)

    Штрафы:
      -0.20  — курс уже просмотрен (УЛУЧШЕНО: снижен с 0.4,
               чтобы не прятать хорошие курсы которые просто открыли)
      -0.80  — курс дизлайкнут
    """
    if not profile.has_history():
        candidates["personal_score"] = candidates[base_score_col]
        candidates["personal_bonus"] = 0.0
        return candidates

    prefs = profile.get_preferences()
    df    = candidates.copy()
    bonus = np.zeros(len(df))

    # ── Бонус за категорию ────────────────────────────────────────────────────
    cat_weights = prefs.get("category_weights", {})
    if cat_weights:
        max_cat_w = max(cat_weights.values())
        def cat_bonus(row):
            cat = row.get("category", "") or ""
            w   = cat_weights.get(cat, 0)
            return (w / max_cat_w) * 0.30 if max_cat_w > 0 else 0
        bonus += df.apply(cat_bonus, axis=1).values

    # ── Бонус за язык ─────────────────────────────────────────────────────────
    top_lang = prefs.get("top_language")
    if top_lang and "language" in df.columns:
        lang_w          = prefs.get("language_weights", {})
        total_lang      = sum(lang_w.values()) or 1
        pref_lang_ratio = lang_w.get(top_lang, 0) / total_lang
        if pref_lang_ratio > 0.60:
            bonus += (df["language"] == top_lang).astype(float).values * 0.15

    # ── Бонус за уровень ──────────────────────────────────────────────────────
    top_diff = prefs.get("top_difficulty")
    if top_diff and "difficulty" in df.columns:
        bonus += (df["difficulty"] == top_diff).astype(float).values * 0.10

    # ── Штраф за уже просмотренные ────────────────────────────────────────────
    # УЛУЧШЕНО: снижен с 0.4 до 0.2 — просмотренный курс не прячем полностью,
    # пользователь мог открыть его случайно или хочет вернуться
    viewed = set(prefs.get("viewed_titles", []))
    if viewed and "title" in df.columns:
        bonus -= df["title"].isin(viewed).astype(float).values * 0.20

    # ── Штраф за дизлайк ──────────────────────────────────────────────────────
    disliked = set(prefs.get("disliked_titles", []))
    if disliked and "title" in df.columns:
        bonus -= df["title"].isin(disliked).astype(float).values * 0.80

    # ── Фильтр лайкнутых — убираем из рекомендаций уже понравившиеся ──────────
    liked = set(prefs.get("liked_titles", []))
    if liked and "title" in df.columns:
        bonus -= df["title"].isin(liked).astype(float).values * 1.5

    # ── Бонус за цель обучения ────────────────────────────────────────────────
    goal = profile.get_profile_meta().get("goal", "")
    if goal == "Сменить работу":
        # Платные курсы с сертификатом, средний/длинный срок, Intermediate+
        if "is_free" in df.columns:
            bonus += (df["is_free"] == 0).astype(float).values * 0.12
        if "duration_category" in df.columns:
            bonus += df["duration_category"].isin(
                ["Средний (1–3 мес)", "Длинный (>3 мес)"]
            ).astype(float).values * 0.10
        if "difficulty" in df.columns:
            bonus += df["difficulty"].isin(
                ["Intermediate", "Advanced"]
            ).astype(float).values * 0.10

    elif goal == "Повысить квалификацию":
        # Advanced и Intermediate, платные
        if "difficulty" in df.columns:
            bonus += (df["difficulty"] == "Advanced").astype(float).values * 0.18
            bonus += (df["difficulty"] == "Intermediate").astype(float).values * 0.10
        if "is_free" in df.columns:
            bonus += (df["is_free"] == 0).astype(float).values * 0.08

    elif goal == "Хобби / интерес":
        # Бесплатные, короткие, Beginner/Intermediate
        if "is_free" in df.columns:
            bonus += (df["is_free"] == 1).astype(float).values * 0.15
        if "duration_category" in df.columns:
            bonus += (df["duration_category"] == "Короткий (<1 мес)").astype(
                float).values * 0.10
        if "difficulty" in df.columns:
            bonus += df["difficulty"].isin(
                ["Beginner", "Intermediate"]
            ).astype(float).values * 0.08

    elif goal == "Подготовка к собеседованию":
        # Высокий рейтинг, много студентов, Intermediate/Advanced
        if "weighted_rating" in df.columns:
            bonus += (df["weighted_rating"] >= 4.5).astype(float).values * 0.15
        if "students_count" in df.columns:
            max_stu = df["students_count"].max() or 1
            bonus += (df["students_count"] / max_stu * 0.12).values
        if "difficulty" in df.columns:
            bonus += df["difficulty"].isin(
                ["Intermediate", "Advanced"]
            ).astype(float).values * 0.10

    df["personal_bonus"] = bonus * weight
    df["personal_score"] = df[base_score_col] + df["personal_bonus"]

    return df

# Похожие на лайкнутые (item-to-item)

def recommend_by_likes(
    profile:    UserProfile,
    df_courses: pd.DataFrame,
    top_k:      int = 5,
    seed:       int = 0,
) -> pd.DataFrame:
    """
    Рекомендует курсы похожие на те, что пользователь лайкнул.

    Логика (по приоритету):
      1. Совпадение по category лайкнутых курсов
      2. Поиск по подстроке title лайкнутых курсов
      3. Если пусто — топ по hybrid_score глобально

    УЛУЧШЕНО:
      - сортировка по hybrid_score (учитывает рейтинг + популярность)
      - исключаются курсы с нулевым рейтингом и рейтингом 3.72 без отзывов
    """
    prefs = profile.get_preferences()
    liked_titles     = prefs.get("liked_titles", [])
    liked_categories = prefs.get("top_categories", [])

    if not liked_titles and not liked_categories:
        return pd.DataFrame({"Сообщение": ["Поставьте лайк курсам для персональных рекомендаций"]})

    result_df = df_courses.copy()

    # Убираем курсы без реального рейтинга из рекомендаций по лайкам
    if "reviews_count" in result_df.columns:
        has_real = ~(
            (result_df["rating"].round(2) == FAKE_RATING) &
            (result_df["reviews_count"] == 0)
        )
        result_df = result_df[has_real | (result_df["rating"] > 0)]

    mask = pd.Series(False, index=result_df.index)

    # 1. По категориям лайкнутых курсов
    if liked_categories and "category" in result_df.columns:
        mask |= result_df["category"].isin(liked_categories)

    # 2. По подстроке title
    if mask.sum() == 0:
        for term in liked_titles[-8:]:
            term_lower = str(term).strip().lower()
            if len(term_lower) < 3:
                continue
            mask |= result_df["title"].str.lower().str.contains(
                re.escape(term_lower), na=False
            )
            if "skills" in result_df.columns:
                mask |= result_df["skills"].str.lower().str.contains(
                    re.escape(term_lower), na=False
                )

    filtered = result_df[mask]

    # 3. Запасной вариант — глобальный топ
    if filtered.empty:
        filtered = result_df.copy()

    # Убираем уже лайкнутые, дизлайкнутые, сохранённые и начатые
    disliked_set = set(prefs.get("disliked_titles", []))
    saved_set    = {s["title"] for s in profile.get_saved()}
    started_set  = {s["title"] for s in profile.get_started()}
    exclude_set  = set(liked_titles) | disliked_set | saved_set | started_set
    filtered     = filtered[~filtered["title"].isin(exclude_set)]

    # Сортируем по hybrid_score если есть, иначе по weighted_rating
    sort_col = "hybrid_score" if "hybrid_score" in filtered.columns else "weighted_rating"
    filtered = filtered.sort_values(
        by=[sort_col, "students_count"],
        ascending=[False, False]
    )
    # При обновлении подборки берём следующую "страницу" результатов
    pool = min(len(filtered), top_k * 4)
    offset = (seed * top_k) % max(pool, 1)
    indices = list(range(pool))
    rotated = indices[offset:] + indices[:offset]
    filtered = filtered.iloc[rotated[:top_k]]

    filtered = filtered.copy()
    # Текст объяснения зависит от того что drove рекомендацию
    expl = "на основе вашей истории" if not liked_titles else "рекомендация на основе сохранённых курсов"
    filtered["объяснение"] = expl

    cols = [
        "title", "source", "weighted_rating", "difficulty",
        "category", "language", "is_free", "price",
        "duration_category", "объяснение", "url"
    ]
    cols = [c for c in cols if c in filtered.columns]

    return filtered[cols].reset_index(drop=True)

# Рекомендации на основе эмбеддингов сохранённых курсов

def recommend_by_embeddings(
    profile:    "UserProfile",
    df_courses: "pd.DataFrame",
    embeddings: "np.ndarray",
    knn,
    top_k:      int = 10,
    seed:       int = 0,
) -> "pd.DataFrame":
    """
    Строит «вкусовой вектор» из эмбеддингов сохранённых/лайкнутых курсов
    и ищет семантически ближайшие курсы через KNN.
    """
    import numpy as np

    prefs        = profile.get_preferences()
    liked_titles = set(prefs.get("liked_titles", []))
    saved_titles = {s["title"] for s in profile.get_saved()}
    started_titles = {s["title"] for s in profile.get_started()}
    disliked_titles = set(prefs.get("disliked_titles", []))
    exclude_set  = liked_titles | saved_titles | started_titles | disliked_titles

    # Собираем эмбеддинги сохранённых и лайкнутых курсов
    source_titles = liked_titles | saved_titles
    if not source_titles:
        return recommend_by_likes(profile, df_courses, top_k=top_k, seed=seed)

    # Ищем индексы курсов в df
    title_to_idx = {t: i for i, t in enumerate(df_courses["title"])}
    found_indices = [title_to_idx[t] for t in source_titles if t in title_to_idx]

    if not found_indices:
        return recommend_by_likes(profile, df_courses, top_k=top_k, seed=seed)

    # Усредняем эмбеддинги → «вкусовой вектор» пользователя
    taste_vec = embeddings[found_indices].mean(axis=0, keepdims=True)
    norm = np.linalg.norm(taste_vec)
    if norm > 0:
        taste_vec = taste_vec / norm

    # KNN-поиск: берём большой пул, потом фильтруем
    n_neighbors = min(top_k * 6 + len(exclude_set), len(df_courses))
    distances, indices = knn.kneighbors(taste_vec, n_neighbors=n_neighbors)

    candidates = df_courses.iloc[indices[0]].copy()
    candidates["similarity"] = 1 - distances[0]

    # Убираем уже известные курсы
    candidates = candidates[~candidates["title"].isin(exclude_set)]

    # Сортируем: 70% вес семантики + 30% качество
    sort_col = "hybrid_score" if "hybrid_score" in candidates.columns else "weighted_rating"
    candidates["_final"] = candidates["similarity"] * 0.7 + (
        candidates[sort_col] / candidates[sort_col].max().clip(1e-9)
    ) * 0.3
    candidates = candidates.sort_values("_final", ascending=False)

    # Ротация при обновлении подборки
    pool   = min(len(candidates), top_k * 4)
    offset = (seed * top_k) % max(pool, 1)
    idxs   = list(range(pool))
    candidates = candidates.iloc[(idxs + idxs)[offset: offset + top_k]]

    candidates = candidates.copy()
    candidates["объяснение"] = "рекомендация на основе сохранённых курсов"

    cols = ["title", "source", "weighted_rating", "difficulty", "category",
            "top_category", "language", "is_free", "price", "duration_category",
            "объяснение", "url", "similarity"]
    cols = [c for c in cols if c in candidates.columns]
    return candidates[cols].reset_index(drop=True)


# Рекомендации по анкете онбординга

# Ключевые слова для каждой цели — используются при поиске по title/category
_GOAL_KEYWORDS = {
    "Веб-разработка":            ["web", "html", "css", "javascript", "frontend", "backend", "react", "django", "flask"],
    "Data Science / ML":         ["data", "machine learning", "ml", "deep learning", "neural", "tensorflow", "pandas", "ai"],
    "Мобильная разработка":      ["mobile", "android", "ios", "kotlin", "swift", "flutter", "react native"],
    "DevOps":                    ["devops", "docker", "kubernetes", "ci/cd", "linux", "ansible", "terraform", "nginx"],
    "Системное программирование":["c++", "rust", "embedded", "system", "os", "kernel", "assembly"],
    "Базы данных":               ["sql", "database", "postgresql", "mysql", "mongodb", "redis", "nosql"],
    "Кибербезопасность":         ["security", "cyber", "hacking", "penetration", "ctf", "cryptography", "network security"],
}


def recommend_by_onboarding(
    profile:    "UserProfile",
    df_courses: pd.DataFrame,
    top_k:      int = 6,
) -> pd.DataFrame:
    """
    Рекомендации на основе анкеты пользователя.

    Логика:
      1. Фильтр по уровню сложности
      2. Фильтр по выбранным языкам/технологиям
      3. Бонус к скору курсам, совпадающим с целями пользователя
      4. Сортировка по итоговому скору
    """
    onb       = profile.get_onboarding()
    level     = onb.get("level", "")
    languages = onb.get("languages", [])
    goals     = onb.get("goals", [])

    result = df_courses.copy()

    # Фильтр по уровню
    if level and "difficulty" in result.columns:
        level_df = result[result["difficulty"] == level]
        if not level_df.empty:
            result = level_df

    # Фильтр по языкам/технологиям
    if languages:
        mask = pd.Series(False, index=result.index)
        for lang in languages:
            pat = re.escape(lang.lower())
            if "title" in result.columns:
                mask |= result["title"].str.lower().str.contains(pat, na=False)
            if "programming_language" in result.columns:
                mask |= result["programming_language"].fillna("").str.lower().str.contains(
                    pat, na=False
                )
        if mask.sum() >= 3:
            result = result[mask]

    # Фильтр + бонус по целям
    sort_col = "hybrid_score" if "hybrid_score" in result.columns else "weighted_rating"
    result = result.copy()
    result["_score"] = result[sort_col].fillna(0)

    if goals:
        goal_keywords = []
        for g in goals:
            goal_keywords.extend(_GOAL_KEYWORDS.get(g, []))

        if goal_keywords:
            title_col = result["title"].str.lower().fillna("") if "title" in result.columns else pd.Series("", index=result.index)
            cat_col   = result["category"].str.lower().fillna("") if "category" in result.columns else pd.Series("", index=result.index)

            goal_mask = pd.Series(False, index=result.index)
            for kw in goal_keywords:
                goal_mask |= title_col.str.contains(re.escape(kw), na=False) | cat_col.str.contains(re.escape(kw), na=False)

            # Жёсткий фильтр по целям если достаточно совпадений
            goal_filtered = result[goal_mask]
            if len(goal_filtered) >= 3:
                result = goal_filtered

            # Бонус за совпадение с целями
            bonus = pd.Series(0.0, index=result.index)
            for kw in goal_keywords:
                title_c = result["title"].str.lower().fillna("") if "title" in result.columns else pd.Series("", index=result.index)
                cat_c   = result["category"].str.lower().fillna("") if "category" in result.columns else pd.Series("", index=result.index)
                match = title_c.str.contains(re.escape(kw), na=False) | cat_c.str.contains(re.escape(kw), na=False)
                bonus += match.astype(float) * 0.3
            result["_score"] = result["_score"] + bonus.clip(upper=1.5)

    result = result.sort_values("_score", ascending=False).head(top_k)
    result = result.drop(columns=["_score"], errors="ignore")

    cols = [c for c in [
        "title", "source", "weighted_rating", "difficulty",
        "category", "language", "is_free", "price",
        "duration_category", "url",
    ] if c in result.columns]

    return result[cols].reset_index(drop=True)


# Менеджер профилей

class ProfileManager:
    """
    Удобный интерфейс для работы с профилями пользователей.
    Используется в recommender.py через глобальный profile_manager.
    """

    def get(self, user_id: str) -> UserProfile:
        return UserProfile(user_id)

    def track_view(self, user_id: str, course_row: dict):
        """Вызывается когда пользователь открыл страницу курса."""
        profile = self.get(user_id)
        profile.add_view(
            title      = course_row.get("title", ""),
            category   = course_row.get("category", ""),
            difficulty = course_row.get("difficulty", ""),
            language   = course_row.get("language", ""),
            source     = course_row.get("source", ""),
        )

    def track_like(self, user_id: str, course_row: dict):
        """Вызывается когда пользователь нажал лайк."""
        profile = self.get(user_id)
        profile.add_like(
            title      = course_row.get("title", ""),
            category   = course_row.get("category", ""),
            difficulty = course_row.get("difficulty", ""),
            language   = course_row.get("language", ""),
            source     = course_row.get("source", ""),
        )

    def track_save(self, user_id: str, course_row: dict):
        """Вызывается когда пользователь сохраняет курс в список."""
        self.get(user_id).add_saved(course_row)

    def track_unsave(self, user_id: str, title: str):
        """Удаляет курс из списка для изучения."""
        self.get(user_id).remove_saved(title)

    def track_unlike(self, user_id: str, title: str):
        """Удаляет курс из списка понравившихся."""
        self.get(user_id).remove_like(title)

    def track_dislike(self, user_id: str, title: str):
        """Вызывается когда пользователь нажал дизлайк."""
        profile = self.get(user_id)
        profile.add_dislike(title)

    def track_search(self, user_id: str, query: str):
        """Вызывается при каждом поиске."""
        profile = self.get(user_id)
        profile.add_search(query)

    def get_summary(self, user_id: str) -> str:
        return self.get(user_id).summary()

    def get_stats(self, user_id: str) -> dict:
        """
        НОВОЕ: возвращает статистику профиля для дипломной отчётности.

        Пример вывода:
            {
              "likes": 3,
              "views": 12,
              "searches": 8,
              "dislikes": 1,
              "top_categories": ["Programming / Python", "Data Science / ML / AI"],
              "top_language": "ru",
              "top_difficulty": "Beginner"
            }
        """
        profile = self.get(user_id)
        prefs   = profile.get_preferences()
        return {
            "likes":          len(profile.data.get("likes", [])),
            "saves":          len(profile.get_saved()),
            "views":          len(profile.data.get("views", [])),
            "searches":       len(profile.data.get("searches", [])),
            "dislikes":       len(profile.data.get("dislikes", [])),
            "top_categories": prefs.get("top_categories", []),
            "top_language":   prefs.get("top_language"),
            "top_difficulty": prefs.get("top_difficulty"),
        }


# Глобальный менеджер (импортируется в recommender.py)
profile_manager = ProfileManager()

# Тест

if __name__ == "__main__":
    print("Тестируем персонализацию v2...\n")

    p = UserProfile("test_user")
    p.clear_history()

    p.add_view("Python for Beginners",  "Programming",           "Beginner",     "en", "udemy")
    p.add_view("Python Data Science",   "Data Science / ML / AI","Intermediate", "en", "udemy")
    p.add_like("Machine Learning A-Z",  "Data Science / ML / AI","Intermediate", "en", "udemy")
    p.add_view("Django Web Framework",  "Programming",           "Intermediate", "en", "stepik")
    p.add_search("python machine learning")

    # Тест дубликата лайка
    p.add_like("Machine Learning A-Z",  "Data Science / ML / AI","Intermediate", "en", "udemy")
    assert len(p.data["likes"]) == 1, "Дубликат лайка не должен добавляться"

    prefs = p.get_preferences()

    print(f"Топ категории:            {prefs['top_categories']}")
    print(f"Предпочтительный язык:    {prefs['top_language']}")
    print(f"Предпочтительный уровень: {prefs['top_difficulty']}")
    print(f"Просмотрено:              {len(prefs['viewed_titles'])} курсов")
    print(f"Лайкнуто:                 {len(prefs['liked_titles'])} курсов")
    print(f"\nСводка: {p.summary()}")

    # Тест get_stats
    pm    = ProfileManager()
    stats = pm.get_stats("test_user")
    print(f"\nСтатистика: {stats}")

    print("\n✅ Персонализация v2 работает!")