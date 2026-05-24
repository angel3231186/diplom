import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

HISTORY_DIR = os.path.join(os.path.dirname(__file__), "chat_history")
os.makedirs(HISTORY_DIR, exist_ok=True)

def _history_file(user_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", user_id or "default")
    return os.path.join(HISTORY_DIR, f"chat_history_{safe}.json")
DATA_FILE    = os.path.join(os.path.dirname(__file__), "final_dataset_ready.xlsx")
_PORT   = 11435
_started = False
_lock   = threading.Lock()
_df     = None


def _load_df():
    global _df
    if _df is not None:
        return _df
    try:
        import pandas as pd
        df = pd.read_excel(DATA_FILE)
        df["_search_text"] = (
            df.get("title", "").fillna("") + " " +
            df.get("top_category", "").fillna("") + " " +
            df.get("category", "").fillna("") + " " +
            df.get("programming_language", "").fillna("")
        ).str.lower()
        _df = df
    except Exception:
        _df = None
    return _df


def _stem(word: str) -> str:
    """Обрезаем русские падежные окончания для поиска."""
    for suffix in ["ому","ему","ого","его","ую","ою","ии","ие","ия","ий",
                   "ых","их","ью","ам","ям","ах","ях","ом","ем","ой","ей",
                   "ню","ию","ного","ному","ной"]:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[:-len(suffix)]
    for suffix in ["ю","я","е","у","а","и","ы","й"]:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[:-len(suffix)]
    return word

def _search_courses(query: str, n: int = 5, difficulty: str = "") -> list:
    df = _load_df()
    if df is None:
        return []
    STOP = {"хочу","хочет","найди","найти","курсы","курс","курса","курсе","курсу",
            "хотел","хотела","изучить","изучать","учить","учиться","мне","нам",
            "для","про","что","как","где","есть","нет","все","это","или",
            "нужен","нужна","нужно","нужны","нужного","хочешь","буду","быть",
            "noch","and","the","один","два","три","четыре","пять","шесть","семь",
            "восемь","девять","десять","дай","дайте","покажи","покажите",
            "хочется","можно","пожалуйста","посоветуй","посоветуйте","подбери",
            "первый","первым","первого","первой","второй","вторым","третий","третьим","такой","такое","самый","самое",
            "курсов","курсами","курсам","курсах","темы","тему","теме",
            "нибудь","любой","любое","любых","интересн","интересное","интересный",
            "популярн","популярное","популярный","расскажи","расскажите",
            "знаю","знать","хочется","неважно","всякое","разное","любое",
            "давай","помоги","помогите","подскажи","подскажите","выбери","выбрать",
            "какой","какая","какие","какое","который","которая","которые",
            "начать","начни","очень","просто","вообще","немного","выбор",
            "посмотри","пожалуйста","хочется","незнаю","помочь",
            "разработке","разработки","разработку","разработкой","разработках",
            "изучения","изучение","изучению","изучением","изучении",
            "составь","составьте","разбей","расписание","обучения","обучение",
            "обучению","обучением","план","планом","планы","дней","день","дня"}
    TRANSLIT = {
        "пайтон":"python","питон":"python","джава":"java",
        "джаваскрипт":"javascript","яваскрипт":"javascript","сиквел":"sql",
        "линукс":"linux","андроид":"android","андройд":"android","айос":"ios","свифт":"swift",
        "котлин":"kotlin","раст":"rust","голанг":"golang","реакт":"react",
        "ангуляр":"angular","вью":"vue","докер":"docker","гит":"git",
        "данные":"data","данных":"data","аналитика":"analytics",
        "безопасность":"security","кибербезопасность":"security",
        "кибербезопасности":"security","кибербезопасносте":"security",
        "кибербезопасносту":"security","кибербезопасностью":"security",
        "дизайн":"design","веб":"web","фронтенд":"web","frontend":"web","бэкенд":"backend","backend":"backend",
    }
    raw_words = [w for w in re.split(r"\s+", query.lower()) if len(w) > 2 and w not in STOP]
    # Транслитерация + стемминг
    expanded = []
    for w in raw_words:
        stemmed = _stem(w)
        if w in TRANSLIT:
            expanded.append(TRANSLIT[w])
        elif stemmed in TRANSLIT:
            expanded.append(TRANSLIT[stemmed])
        else:
            expanded.append(stemmed)
    words = [w for w in expanded if len(w) > 2]
    if not words:
        return []
    def _pat(w):
        return r'(?<![a-zA-Z0-9])' + re.escape(w) + r'(?![a-zA-Z0-9])'
    # Сначала пробуем AND по всем словам
    mask = df["_search_text"].str.contains(_pat(words[0]), na=False, regex=True)
    for w in words[1:]:
        mask &= df["_search_text"].str.contains(_pat(w), na=False, regex=True)
    result = df[mask]
    if result.empty:
        # Фолбэк 1: пробуем пары слов (AND по 2 словам)
        if len(words) >= 2:
            for i in range(len(words)):
                for j in range(len(words)):
                    if i == j:
                        continue
                    m = (df["_search_text"].str.contains(_pat(words[i]), na=False, regex=True) &
                         df["_search_text"].str.contains(_pat(words[j]), na=False, regex=True))
                    if m.any():
                        result = df[m]
                        break
                if not result.empty:
                    break
    if result.empty:
        # Фолбэк 2: каждое слово по отдельности — сначала ASCII (технические термины), потом Cyrillic
        sorted_words = sorted(words, key=lambda x: (not x.isascii(), -len(x)))
        for w in sorted_words:
            mask = df["_search_text"].str.contains(_pat(w), na=False, regex=True)
            result = df[mask]
            if not result.empty:
                break
    if result.empty:
        return []
    # Оставляем только курсы с рейтингом > 0
    if "hybrid_score_base" in result.columns:
        rated = result[result["hybrid_score_base"] > 0]
        if not rated.empty:
            result = rated
    # Дополнительная проверка: хотя бы одно слово запроса должно быть в названии курса
    def _title_relevant(title):
        t = str(title).lower()
        return any(w in t for w in words)
    relevant = result[result["title"].apply(_title_relevant)]
    if not relevant.empty:
        result = relevant
    if difficulty and "difficulty" in result.columns:
        filtered_diff = result[result["difficulty"] == difficulty]
        if not filtered_diff.empty:
            result = filtered_diff
    if "hybrid_score_base" in result.columns:
        result = result.sort_values("hybrid_score_base", ascending=False)
    courses = []
    for _, row in result.head(n).iterrows():
        title    = str(row.get("title", ""))
        platform = str(row.get("source", "")).capitalize()
        is_free  = int(row.get("is_free", 0) or 0)
        price    = float(row.get("price", 0) or 0)
        rating   = float(row.get("hybrid_score_base", 0) or 0)
        url      = str(row.get("url", "") or "")
        level    = str(row.get("difficulty", "") or "")
        price_str = "бесплатно" if (is_free == 1 or price == 0) else f"{int(price):,} тг"
        level_map = {"Beginner": "Начинающий", "Intermediate": "Средний", "Advanced": "Продвинутый"}
        level_ru = level_map.get(level, "") or ""
        courses.append({
            "title": title,
            "platform": platform,
            "source": str(row.get("source", "") or "").lower(),
            "price": price_str,
            "price_raw": price,
            "is_free": is_free,
            "hybrid_score_base": round(rating, 2),
            "rating": round(rating, 2),
            "url": url,
            "difficulty": level,
            "level": level_ru,
            "language": str(row.get("language", "") or ""),
            "category": str(row.get("top_category", "") or ""),
            "duration_category": str(row.get("duration_category", "") or ""),
        })
    return courses


class _Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/started":
            params = parse_qs(parsed.query)
            user_id = params.get("user", ["default"])[0]
            try:
                import sys
                sys.path.insert(0, HISTORY_DIR)
                from personalization import profile_manager
                started = profile_manager.get(user_id).get_started()
            except Exception:
                started = []
            body = json.dumps(started, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/popular":
            params = parse_qs(parsed.query)
            n = int(params.get("n", ["5"])[0])
            df = _load_df()
            courses = []
            if df is not None and "hybrid_score_base" in df.columns:
                top = df[df["hybrid_score_base"] > 0].sort_values("hybrid_score_base", ascending=False).head(n)
                for _, row in top.iterrows():
                    is_free = int(row.get("is_free", 0) or 0)
                    price   = float(row.get("price", 0) or 0)
                    price_str = "бесплатно" if (is_free == 1 or price == 0) else f"{int(price):,} тг"
                    level = str(row.get("difficulty", "") or "")
                    level_map = {"Beginner": "Начинающий", "Intermediate": "Средний", "Advanced": "Продвинутый"}
                    courses.append({
                        "title": str(row.get("title", "")),
                        "platform": str(row.get("source", "")).capitalize(),
                        "source": str(row.get("source", "") or "").lower(),
                        "price": price_str, "price_raw": price, "is_free": is_free,
                        "hybrid_score_base": round(float(row.get("hybrid_score_base", 0) or 0), 2),
                        "rating": round(float(row.get("hybrid_score_base", 0) or 0), 2),
                        "url": str(row.get("url", "") or ""),
                        "difficulty": level, "level": level_map.get(level, ""),
                        "language": str(row.get("language", "") or ""),
                        "category": str(row.get("top_category", "") or ""),
                        "duration_category": str(row.get("duration_category", "") or ""),
                    })
            body = json.dumps(courses, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/search":
            params = parse_qs(parsed.query)
            query      = params.get("q", [""])[0]
            n          = int(params.get("n", ["5"])[0])
            difficulty = params.get("difficulty", [""])[0]
            courses = _search_courses(query, n=min(n, 10), difficulty=difficulty)
            body = json.dumps(courses, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        params = parse_qs(parsed.query)
        user_id = params.get("user", ["default"])[0]
        hist_file = _history_file(user_id)
        data = []
        try:
            if os.path.exists(hist_file):
                with open(hist_file, encoding="utf-8") as f:
                    data = json.load(f)
        except Exception:
            data = []
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed  = urlparse(self.path)
        params  = parse_qs(parsed.query)
        user_id = params.get("user", ["default"])[0]
        length  = int(self.headers.get("Content-Length", 0))
        body    = self.rfile.read(length)

        if parsed.path == "/start":
            try:
                import sys
                sys.path.insert(0, HISTORY_DIR)
                from personalization import profile_manager
                import gamification as gam
                course = json.loads(body)
                profile = profile_manager.get(user_id)
                profile.add_started(
                    title=course.get("title", ""),
                    url=course.get("url", ""),
                    source=course.get("platform", ""),
                )
                started_count = len(profile.get_started())
                gam.add_xp(user_id, "start_course")
                gam.track_weekly_course_opened(user_id)
                if started_count >= 1:
                    gam.unlock_achievement(user_id, "started_1")
                if started_count >= 5:
                    gam.unlock_achievement(user_id, "started_5")
                started_cats = {s.get("source", "") for s in profile.get_started()}
                if len(started_cats) >= 3:
                    gam.unlock_achievement(user_id, "explorer")
            except Exception:
                pass
            self.send_response(200)
            self._cors()
            self.end_headers()
            return

        if parsed.path == "/save":
            try:
                import sys
                sys.path.insert(0, HISTORY_DIR)
                from personalization import profile_manager
                import gamification as gam
                course = json.loads(body)
                profile_manager.track_save(user_id, course)
                gam.track_weekly_course_saved(user_id)
            except Exception:
                pass
            self.send_response(200)
            self._cors()
            self.end_headers()
            return

        hist_file = _history_file(user_id)
        try:
            data = json.loads(body)
            with open(hist_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass
        self.send_response(200)
        self._cors()
        self.end_headers()

    def log_message(self, *_):
        pass


def ensure_running():
    global _started
    with _lock:
        if _started:
            return
        try:
            _load_df()
            server = HTTPServer(("localhost", _PORT), _Handler)
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            _started = True
        except OSError:
            _started = True
