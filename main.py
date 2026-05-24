import os
import re
import numpy as np
import pandas as pd
import joblib

from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors

from personalization import profile_manager, personalize_scores

DATA_PATH = "final_dataset_ready.xlsx"
MODEL_DIR = "model"

EMBEDDINGS_PATH = f"{MODEL_DIR}/embeddings.npy"
DF_PATH         = f"{MODEL_DIR}/df.pkl"

os.makedirs(MODEL_DIR, exist_ok=True)

_model_instance = None

def _get_model():
    global _model_instance
    if _model_instance is None:
        _model_instance = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
    return _model_instance

# Веса итогового скора: 75% — семантическое сходство с запросом, 25% — качество курса
W_SIMILARITY         = 0.75
W_QUALITY            = 0.25
SIMILARITY_THRESHOLD = 0.20   # порог отсечения нерелевантных результатов KNN
EXACT_LANG_SIM       = 0.85   # similarity для точного совпадения по языку программирования
FAKE_RATING          = 3.72   # средний рейтинг-заглушка у курсов без реальных оценок

LANG_QUERY_MAP = {
    "python":          {"type": "pl", "values": ["Python"],       "confirm": r"\bpython\b|питон|пайтон"},
    "java":            {"type": "pl", "values": ["Java"],         "confirm": r"\bjava\b", "exclude": r"javascript|node\.js|react\b|angular\b|vue\b"},
    "javascript":      {"type": "pl", "values": ["JavaScript"],   "confirm": r"\bjavascript\b|джаваскрипт|яваскрипт"},
    "js":              {"type": "pl", "values": ["JavaScript"],   "confirm": r"\bjavascript\b|джаваскрипт"},
    "go":              {"type": "pl", "values": ["Go"],           "confirm": r"\bgolang\b|\bgo\b"},
    "golang":          {"type": "pl", "values": ["Go"],           "confirm": r"\bgolang\b|\bgo\b"},
    "sql":             {"type": "pl", "values": ["SQL"],          "confirm": r"\bsql\b"},
    "html":            {"type": "pl", "values": ["HTML/CSS"],     "confirm": r"\bhtml\b|\bcss\b"},
    "css":             {"type": "pl", "values": ["HTML/CSS"],     "confirm": r"\bhtml\b|\bcss\b"},
    "html/css":        {"type": "pl", "values": ["HTML/CSS"],     "confirm": r"\bhtml\b|\bcss\b"},
    "frontend":        {"type": "pl", "values": ["Frontend"],     "confirm": r"\bfrontend\b|фронтенд|фронт"},
    "фронтенд":        {"type": "pl", "values": ["Frontend"],     "confirm": r"\bfrontend\b|фронтенд"},
    "backend":         {"type": "pl", "values": ["Backend"],      "confirm": r"\bbackend\b|бэкенд|бекенд"},
    "бэкенд":          {"type": "pl", "values": ["Backend"],      "confirm": r"\bbackend\b|бэкенд"},
    "fullstack":       {"type": "pl", "values": ["Fullstack"],    "confirm": r"\bfullstack\b|фулстек"},
    "фулстек":         {"type": "pl", "values": ["Fullstack"],    "confirm": r"\bfullstack\b|фулстек"},
    "devops":          {"type": "pl", "values": ["DevOps"],       "confirm": r"\bdevops\b|девопс"},
    "девопс":          {"type": "pl", "values": ["DevOps"],       "confirm": r"\bdevops\b|девопс"},
    "linux":           {"type": "pl", "values": ["Linux"],        "confirm": r"\blinux\b|линукс"},
    "линукс":          {"type": "pl", "values": ["Linux"],        "confirm": r"\blinux\b|линукс"},
    "ai":              {"type": "pl", "values": ["AI"],           "confirm": r"\bai\b|искусственный интеллект|нейросет"},
    "ml":              {"type": "pl", "values": ["AI", "Data Science"], "confirm": r"\bml\b|машинное обучение"},
    "нейросети":       {"type": "pl", "values": ["AI"],           "confirm": r"нейросет|искусственный интеллект"},
    "data science":    {"type": "pl", "values": ["Data Science"], "confirm": r"\bdata.?science\b|датасайенс"},
    "датасайенс":      {"type": "pl", "values": ["Data Science"], "confirm": r"\bdata.?science\b|датасайенс"},
    "cybersecurity":   {"type": "pl", "values": ["Cybersecurity"],"confirm": r"\bcybersecurity\b|кибербезопасност"},
    "кибербезопасность":{"type":"pl", "values": ["Cybersecurity"],"confirm": r"\bcybersecurity\b|кибербезопасност"},
    "mobile":          {"type": "pl", "values": ["Mobile"],       "confirm": r"\bmobile\b|мобильн"},
    "мобильная":       {"type": "pl", "values": ["Mobile"],       "confirm": r"\bmobile\b|мобильн"},
    "blockchain":      {"type": "pl", "values": ["Blockchain"],   "confirm": r"\bblockchain\b|блокчейн"},
    "блокчейн":        {"type": "pl", "values": ["Blockchain"],   "confirm": r"\bblockchain\b|блокчейн"},
    "embedded":        {"type": "pl", "values": ["Embedded"],     "confirm": r"\bembedded\b|встроенн"},
    "database":        {"type": "pl", "values": ["Database"],     "confirm": r"\bdatabase\b|базы данных|бд\b"},
    "базы данных":     {"type": "pl", "values": ["Database"],     "confirm": r"\bdatabase\b|базы данных"},
    "web":             {"type": "pl", "values": ["Web"],          "confirm": r"\bweb\b|веб"},
    "wordpress":       {"type": "pl", "values": ["WordPress"],    "confirm": r"\bwordpress\b|вордпресс"},
    "game":            {"type": "pl", "values": ["Game Design"],  "confirm": r"\bgame\b|игр"},
    "gamedev":         {"type": "pl", "values": ["Game Design"],  "confirm": r"\bgame\b|игр|геймдев"},
    "геймдев":         {"type": "pl", "values": ["Game Design"],  "confirm": r"\bgame\b|игр|геймдев"},
    "kotlin":          {"type": "title", "pattern": r"\bkotlin\b|котлин"},
    "swift":           {"type": "title", "pattern": r"\bswift\b"},
    "rust":            {"type": "title", "pattern": r"\brust\b|язык rust"},
    "c#":              {"type": "pl",    "values": ["C#"],            "confirm": r"c#|csharp|\.net|asp\.net"},
    "csharp":          {"type": "pl",    "values": ["C#"],            "confirm": r"c#|csharp|\.net|asp\.net"},
    "си шарп":         {"type": "pl",    "values": ["C#"],            "confirm": r"c#|csharp|\.net|asp\.net"},
    "c++":             {"type": "title", "pattern": r"\bc\+\+\b|cpp", "exclude": r"c#|csharp"},
    "cpp":             {"type": "title", "pattern": r"\bc\+\+\b|cpp", "exclude": r"c#|csharp"},
    "ruby":            {"type": "title", "pattern": r"\bruby\b"},
    "typescript":      {"type": "title", "pattern": r"\btypescript\b|\bts\b"},
    "docker":          {"type": "title", "pattern": r"\bdocker\b|докер"},
    "kubernetes":      {"type": "title", "pattern": r"\bkubernetes\b|\bk8s\b|кубернетес"},
    "flask":           {"type": "title", "pattern": r"\bflask\b|фласк"},
    "django":          {"type": "title", "pattern": r"\bdjango\b|джанго"},
    "fastapi":         {"type": "title", "pattern": r"\bfastapi\b|фастапи"},
    "react":           {"type": "title", "pattern": r"\breact\b|реакт"},
    "angular":         {"type": "title", "pattern": r"\bangular\b|ангуляр"},
    "spring":          {"type": "title", "pattern": r"\bspring\b|спринг"},
    "android":         {"type": "title", "pattern": r"\bandroid\b|андроид"},
    "ios":             {"type": "title", "pattern": r"\bios\b|\bswift\b"},
}


def get_lang_candidates(query: str, normalized: str, df: pd.DataFrame) -> pd.DataFrame:
    matched_lang = None
    for q in [query.lower().strip(), normalized.lower().strip()]:
        if q in LANG_QUERY_MAP:
            matched_lang = q
            break

    if matched_lang is None:
        return pd.DataFrame()

    cfg = LANG_QUERY_MAP[matched_lang]
    search_type = cfg["type"]

    if search_type == "pl":
        if "programming_language" not in df.columns:
            return pd.DataFrame()
        result = df[df["programming_language"].isin(cfg["values"])].copy()

    elif search_type == "category":
        result = df[df["category"].isin(cfg["values"])].copy()

    elif search_type == "title":
        pat    = cfg["pattern"]
        result = df[df["title"].str.contains(pat, case=False, na=False, regex=True)].copy()

    else:
        return pd.DataFrame()

    if result.empty:
        return pd.DataFrame()

    confirm_pat = cfg.get("confirm")
    exclude_pat = cfg.get("exclude")

    if confirm_pat or exclude_pat:
        def is_relevant(row):
            title    = str(row.get("title", "")).lower()
            cat      = str(row.get("category", "")).lower()
            skills   = str(row.get("skills", "")).lower()
            fulltext = f"{title} {cat} {skills}"

            if confirm_pat and not re.search(confirm_pat, title, re.IGNORECASE):
                return False
            if exclude_pat and re.search(exclude_pat, fulltext, re.IGNORECASE):
                if matched_lang == "java" and re.search(r"java(?!script)", title, re.IGNORECASE):
                    return True
                return False
            return True

        result = result[result.apply(is_relevant, axis=1)]

    if result.empty:
        return pd.DataFrame()

    result = result.copy()
    result["_has_real"] = ~(
        (result["rating"].round(2) == FAKE_RATING) &
        (result["reviews_count"] == 0)
    )

    _lang_word = matched_lang.lower()
    _title_lower = result["title"].str.lower().fillna("")
    _sec = rf"\b(?:в|на|с|и|для|с помощью|using|with|in|and|for)\s+{re.escape(_lang_word)}\b"
    _is_secondary = _title_lower.str.contains(_sec, regex=True, na=False)
    result["_primary"] = (~_is_secondary).astype(int)

    result = result.sort_values(
        ["_primary", "_has_real", "hybrid_score"],
        ascending=[False, False, False]
    )
    result["similarity"] = result["_primary"].apply(
        lambda p: EXACT_LANG_SIM if p == 1 else EXACT_LANG_SIM * 0.55
    )
    result = result.drop(columns=["_has_real", "_primary"])
    return result

TECH_SYNONYMS = {
    r"java(?!script|fx|ee|se|me)": "java programming джава",
    r"python":                      "python programming питон пайтон",
    r"kotlin":                      "kotlin android котлин",
    r"\bjs\b|javascript":           "javascript js frontend джаваскрипт",
    r"typescript":                  "typescript javascript frontend",
    r"c\+\+|cpp":                   "c++ cpp programming плюсы",
    r"c#|csharp|\.net":             "csharp dotnet programming",
    r"golang|\bgo\b":               "golang go backend голанг",
    r"\brust\b":                    "rust programming руст",
    r"\bswift\b":                   "swift ios apple",
    r"\breact\b":                   "react frontend javascript реакт",
    r"\bdjango\b":                  "django python web backend джанго",
    r"\bflask\b":                   "flask python web backend фласк",
    r"fastapi":                     "fastapi python web api фастапи",
    r"\bspring\b":                  "spring java backend спринг",
    r"\bdocker\b":                  "docker devops container докер",
    r"kubernetes|k8s":              "kubernetes k8s devops кубернетес",
    r"\blinux\b":                   "linux unix devops линукс",
    r"\bsql\b":                     "sql database databases скл",
    r"postgresql|postgres":         "postgresql sql database постгрес",
    r"\bmysql\b":                   "mysql sql database мускул",
    r"mongodb":                     "mongodb nosql database",
    r"tensorflow":                  "tensorflow machine learning deep learning",
    r"pytorch":                     "pytorch machine learning deep learning",
    r"\bpandas\b":                  "pandas python data science",
    r"\bnumpy\b":                   "numpy python data science",
    r"scikit.learn|sklearn":        "sklearn scikit-learn machine learning python",
    r"\bexcel\b":                   "excel spreadsheet эксель",
    r"power\s*bi":                  "power bi analytics пауэр бай",
    r"\btableau\b":                 "tableau analytics visualization табло",
    r"\bgit\b":                     "git version control гит",
    r"selenium":                    "selenium testing automation сэлениум",
    r"машинное\s+обучение|машиное\s+обучение": "machine learning ml",
    r"глубокое\s+обучение":                    "deep learning neural networks",
    r"нейронные\s+сети|нейросети":             "neural networks deep learning",
    r"искусственный\s+интеллект":              "artificial intelligence ai",
    r"анализ\s+данных":                        "data analysis data science",
    r"компьютерное\s+зрение":                  "computer vision cv",
    r"программирование":                       "programming development",
    r"веб.разработка|веб\s+разработка":        "web development frontend backend",
    r"мобильная\s+разработка":                 "mobile development android ios",
    r"кибербезопасность":                      "cybersecurity security",
    r"тестирование":                           "testing qa automation",
    r"базы\s+данных":                          "databases sql",
}

def enrich_text(text: str) -> str:
    # Расширяем текст синонимами: "python" → добавляем "питон pandas sklearn",
    # чтобы русскоязычные запросы находили англоязычные курсы и наоборот.
    extras = []
    for pattern, expansion in TECH_SYNONYMS.items():
        if re.search(pattern, text, re.IGNORECASE):
            extras.append(expansion)
    return (text + " " + " ".join(extras)).strip() if extras else text


def build_text(row):
    # Поля повторяются для повышения их веса в векторном пространстве эмбеддингов:
    # язык программирования ×5, название и навыки ×3, описание ×1
    pl_val    = row.get("programming_language")
    prog_lang = str(pl_val) if (pl_val and pd.notna(pl_val)) else ""
    base = " ".join([
        str(row.get("title", "")) * 4,
        str(row.get("category", "")) * 3,
        str(row.get("skills", "")) * 3,
        prog_lang * 5,
        str(row.get("description", "")),
    ])
    return enrich_text(base)


def load_data(path):
    df = pd.read_excel(path)
    df["price"]          = pd.to_numeric(df.get("price", 0),          errors="coerce").fillna(0)
    df["students_count"] = pd.to_numeric(df.get("students_count", 0), errors="coerce").fillna(0)
    df["rating"]         = pd.to_numeric(df.get("rating", 0),         errors="coerce").fillna(0)
    df["reviews_count"]  = pd.to_numeric(df.get("reviews_count", 0),  errors="coerce").fillna(0)
    df["is_free"]        = (df["price"] == 0).astype(int)
    df["_text"]          = df.apply(build_text, axis=1)
    return df


def fix_categories(df: "pd.DataFrame") -> "pd.DataFrame":
    rules = [
        (r"html|css|верстк|вёрстк|web.{0,5}tech|web-технолог|bootstrap", "Frontend / JavaScript", "Programming"),
        (r"react|vue[.]js|angular|next[.]js|svelte|webpack|frontend","Frontend / JavaScript", "Programming"),
        (r"javascript|typescript|node[.]js|express[.]js",            "Frontend / JavaScript", "Programming"),
        (r"android|kotlin|swift|ios dev|flutter|react native",       "Mobile Development",    "Mobile Development"),
        (r"photoshop|illustrator|figma|ui.{0,3}ux|ux.{0,3}design|graphic design", "UI/UX Design", "Design"),
        (r"excel|\bmicrosoft word\b|powerpoint|microsoft office|google sheets", "Excel", "General IT"),
        (r"marketing|smm|seo|tiktok|instagram|реклам|таргет|crm",   "Business / Management / Soft Skills", "Management"),
        (r"project manag|scrum|agile|jira|управление проект",        "Project Management",    "Management"),
        (r"\bmysql\b|\bpostgresql\b|\bpostgres\b|\bsqlite\b|\bсубд\b|\bms access\b|sqlalchemy|проектирование.{0,20}баз.{0,20}данных|разработк.{0,20}баз.{0,20}данных|pl.{0,3}pgsql", "SQL", "General IT"),
        (r"golang|\bgo\b.{0,10}(lang|программ|разработ|курс|основ)|thank go|задачи.{0,10}golang", "Go / Golang", "Programming"),
        (r"иностранн|китайский|японский|корейский|французский|немецкий|испанский|итальянский|английский.{0,20}(язык|для|уровень|начинающ|продолжающ)|математический английский|chinese language|japanese language|korean language|french language|german language|spanish language|hsk\b|jlpt\b|topik\b", "Иностранные языки", "Other"),
        (r"веб.{0,10}проект|web.{0,10}проект|веб-проект|сайт.{0,10}(html|css|bootstrap|верстк)|вводный курс.{0,20}веб|веб.{0,20}разработ", "Frontend / JavaScript", "Programming"),
        (r"c\+\+|c/c\+\+|cpp\b|работа с массивами на с\b|простые задачки по си\b|программирование на с[.]|многопоточн.{0,20}c", "C++", "Programming"),
        (r"\bc#\b|csharp|pro c#|\basp\.net\b|\b\.net\b|язык.{0,10}c#|задачник.{0,20}c#", "C#", "Programming"),
        (r"\bdjango\b|\bflask\b|\bfastapi\b",                         "Python",                "Programming"),
        (r"\bjava\b(?!script)",                                        "Java / Kotlin",         "Programming"),
        (r"jetpack compose|android studio",                           "Mobile Development",    "Mobile Development"),
        (r"\b1с\b|\b1c\b|1с.{0,10}программ|программ.{0,10}1с",      "Other",                 "Other"),
        (r"\bgit\b|\bgithub\b|\bgitlab\b",                           "Git / GitHub",          "General IT"),
        # Исправляем курсы где Git — второстепенная тема
        (r"gitlab.{0,10}ci\b|github.{0,10}actions|gitlab.{0,10}pipeline", "DevOps / Cloud", "DevOps / Cloud"),
        (r"\bpython\b.{0,60}\bgit\b|\bgit\b.{0,60}\bpython\b",     "Python",                "Programming"),
        (r"(javascript|frontend|верстальщик|верстк).{0,60}\bgit\b|\bgit\b.{0,60}(javascript|frontend|верстальщик|верстк)", "Frontend / JavaScript", "Programming"),
        (r"(\b1с\b|\b1c\b).{0,60}\bgit\b|\bgit\b.{0,60}(\b1с\b|\b1c\b)", "Other",          "Other"),
        (r"pro c#.{0,30}git|c#.{0,60}\bgit\b|\bgit\b.{0,60}c#",    "C#",                   "Programming"),
        (r"docker|kubernetes|devops|linux|nginx|ansible|terraform",  "DevOps / Cloud",        "DevOps / Cloud"),
        (r"cybersecur|pentest|kali|hacking|информацион.{0,10}безопасн", "Cybersecurity / Ethical Hacking", "Security"),
        (r"autocad|3d model|blender|solidworks|revit| cad ",         "Design",                "Design"),
        (r"\bэкологи\b|экология|оцифровк.{0,30}историч|историч.{0,30}оцифровк|ветеринар", "Other", "Other"),
        (r"компьютерное зрение.{0,30}робот|робот.{0,30}компьютерное зрение", "Data Science / ML / AI", "Data Science / ML / AI"),
        (r"fullstack|full.stack|full-stack|фулстак|фул.стак",              "Fullstack",             "Programming"),
        # DS/ML курсы которые ошибочно помечены как Programming
        (r"machine learning|deep learning|neural network|data science|искусственный интеллект|нейронн|машинн.{0,5}обуч|reinforcement learning|computer vision|natural language processing|nlp|генеративн|large language model|llm|tensorflow|pytorch|scikit.learn|keras", "Data Science / ML / AI", "Data Science / ML / AI"),
    ]
    import re as _re
    df = df.copy()
    title_lower = df["title"].str.lower().fillna("")
    for pattern, new_cat, new_top in rules:
        mask = title_lower.str.contains(pattern, regex=True, na=False)
        df.loc[mask, "category"]     = new_cat
        df.loc[mask, "top_category"] = new_top
    # Объединяем дублирующиеся бизнес-категории
    _merge = {"Business", "Management", "Soft Skills", "Business / Management / Soft Skills"}
    df.loc[df["category"].isin(_merge), "category"]     = "Business & Management"
    df.loc[df["category"] == "Business & Management", "top_category"] = "Management"
    return df


def add_bayes(df):
    # Байесовский взвешенный рейтинг: (n·R + m·C) / (n + m)
    # n — число студентов, R — рейтинг курса, C — средний рейтинг по всей выборке,
    # m = 20 — сглаживающая константа (штрафует курсы с малым числом отзывов)
    df = fix_categories(df)
    C = df["rating"].mean()
    m = 20
    df["weighted_rating"] = (df["students_count"] * df["rating"] + m * C) / (df["students_count"] + m)
    df["rating_score"]    = df["weighted_rating"] / 5
    pop = np.log1p(df["students_count"])
    df["popularity_norm"] = pop / pop.max()

    # Курсы без реальных отзывов (рейтинг-заглушка 3.72) получают штраф ×0.5
    has_real_rating = ~(
        (df["rating"].round(2) == FAKE_RATING) &
        (df["reviews_count"] == 0)
    )
    # Stepik и Udemy дают небольшой бонус (+0.05): там рейтинги верифицированы студентами
    source_bonus = df["source"].map(
        {"stepik": 0.05, "udemy": 0.05, "coursera": 0.0, "openedu": 0.0}
    ).fillna(0.0)
    base_score = 0.7 * df["rating_score"] + 0.3 * df["popularity_norm"]
    df["hybrid_score"] = (base_score + source_bonus).where(
        has_real_rating, (base_score + source_bonus) * 0.5
    )
    return df


def build_embeddings(df):
    # normalize_embeddings=True → все векторы на единичной сфере,
    # косинусное расстояние сводится к скалярному произведению (быстрее).
    return np.array(_get_model().encode(
        df["_text"].tolist(),
        show_progress_bar=True,
        batch_size=64,
        normalize_embeddings=True
    ))


def get_model(df, force_rebuild=False):
    if force_rebuild:
        for path in [EMBEDDINGS_PATH, DF_PATH]:
            if os.path.exists(path):
                os.remove(path)
        print("🗑  Кэш удалён, пересобираем эмбеддинги...")

    if os.path.exists(EMBEDDINGS_PATH) and os.path.exists(DF_PATH):
        print("📦 Загружаем модель из кэша...")
        embeddings = np.load(EMBEDDINGS_PATH)
        df         = joblib.load(DF_PATH)
        df         = add_bayes(df)
        knn = NearestNeighbors(metric="cosine", algorithm="brute")
        knn.fit(embeddings)
        return embeddings, knn, df

    print("⚙️  Обучаем модель (это займёт минуту)...")
    embeddings = build_embeddings(df)
    knn = NearestNeighbors(metric="cosine", algorithm="brute")
    knn.fit(embeddings)
    np.save(EMBEDDINGS_PATH, embeddings)
    joblib.dump(df, DF_PATH)
    print("✅ Эмбеддинги сохранены в кэш")
    return embeddings, knn, df


def mmr_rerank(df, embeddings, lambda_param=0.7, top_k=5):
    # MMR (Maximal Marginal Relevance) — балансирует релевантность и разнообразие результатов.
    # λ=0.7: каждый следующий курс максимизирует 0.7·релевантность − 0.3·сходство_с_уже_выбранными.
    # Это предотвращает показ дублирующих курсов по одной теме.
    selected  = []
    remaining = df.copy()
    df_indices = df.index.to_list()
    emb_map    = {idx: embeddings[i] for i, idx in enumerate(df_indices)}

    while len(selected) < top_k and len(remaining) > 0:
        if not selected:
            best_idx = remaining["personal_score"].idxmax()
            selected.append(best_idx)
            remaining = remaining.drop(best_idx)
            continue

        scores = []
        for idx in remaining.index:
            relevance = remaining.loc[idx, "personal_score"]
            diversity = max((np.dot(emb_map[idx], emb_map[s]) * 0.8 for s in selected), default=0)
            scores.append((idx, lambda_param * relevance - (1 - lambda_param) * diversity))

        best_idx = max(scores, key=lambda x: x[1])[0]
        selected.append(best_idx)
        remaining = remaining.drop(best_idx)

    return df.loc[selected]

QUERY_SYNONYMS = {
    "пайтон": "python", "пйтон": "python", "питон": "python",
    "питхон": "python", "паитон": "python", "пайтхон": "python",
    "жава": "java", "джавa": "java", "джава": "java",
    "плюсы": "c++", "плюс плюс": "c++", "си шарп": "c#",
    "эр": "r programming", "джаваскрипт": "javascript", "жс": "javascript",
    "свифт": "swift", "котлин": "kotlin", "голанг": "golang",
    "руст": "rust", "скала": "scala",
    "джанго": "django", "фласк": "flask", "спринг": "spring boot",
    "реакт": "react", "вю": "vue", "вью": "vue", "ангуляр": "angular",
    "нода": "node.js", "нодж": "node.js", "фастапи": "fastapi",
    "фронтенд": "frontend web", "фронт": "frontend",
    "бэкенд": "backend", "бэк": "backend",
    "фулстек": "fullstack", "фуллстек": "fullstack",
    "веб разработка": "web development", "веб-разработка": "web development",
    "девопс": "devops", "докер": "docker",
    "кубернетес": "kubernetes", "кубер": "kubernetes",
    "линукс": "linux", "гит": "git",
    "облако": "cloud", "облачные": "cloud",
    "авс": "aws", "гцп": "gcp google cloud",
    "тестирование": "testing qa", "тест": "testing",
    "автотесты": "automation testing", "автоматизация": "automation testing",
    "сэлениум": "selenium", "сeлениум": "selenium",
    "машиное обучение":        "machine learning",
    "машинное обучение":       "machine learning",
    "глубокое обучение":       "deep learning",
    "ии":                      "artificial intelligence",
    "искусственный интеллект": "artificial intelligence",
    "нейронки":                "neural networks",
    "нейросети":               "neural networks",
    "нейронные сети":          "neural networks",
    "дата сайенс":             "data science",
    "датасаенс":               "data science",
    "анализ данных":           "data analysis",
    "обработка данных":        "data processing",
    "визуализация данных":     "data visualization",
    "генеративный ии":         "generative ai",
    "большие языковые модели": "llm large language models",
    "лдм":                     "llm",
    "компьютерное зрение":     "computer vision",
    "обработка текста":        "natural language processing nlp",
    "нлп":                     "nlp natural language processing",
    "программирование": "programming", "прогр": "programming",
    "веб программирование": "web development programming",
    "базы данных": "databases sql", "бд": "databases",
    "скул": "sql", "скл": "sql",
    "постгрес": "postgresql", "мускул": "mysql",
    "мобильная разработка": "mobile development", "мобайл": "mobile development",
    "андроид": "android", "айос": "ios",
    "кибербезопасность": "cybersecurity", "кибер": "cybersecurity",
    "этичный хакинг": "ethical hacking",
    "информационная безопасность": "cybersecurity information security",
    "алгоритмы": "algorithms",
    "структуры данных": "data structures algorithms",
    "матан": "mathematics calculus",
    "линейная алгебра": "linear algebra mathematics",
    "статистика": "statistics",
    "эксель": "excel spreadsheets",
    "пауэр бай": "power bi", "табло": "tableau",
    "проектное управление": "project management",
    "скрам": "agile scrum",
    "программирование": "programming",
    "разработка": "development programming",
}

def normalize_query(query: str) -> str:
    # Переводит русскоязычный запрос в технические термины:
    # "пайтон машинное обучение" → "python machine learning".
    # Сортируем по длине чтобы длинные фразы заменялись раньше коротких подстрок.
    q = query.lower().strip()
    q = re.sub(r"[^\w\s+#.]", " ", q)
    for ru, en in sorted(QUERY_SYNONYMS.items(), key=lambda x: -len(x[0])):
        q = re.sub(rf"\b{re.escape(ru)}\b", en, q)
    return re.sub(r"\s+", " ", q).strip()


def explain(row) -> str:
    parts = []
    sim = row.get("similarity", 0)
    if   sim >= EXACT_LANG_SIM: parts.append("точное совпадение по языку")
    elif sim >= 0.50:            parts.append("отличное совпадение с запросом")
    elif sim >= 0.30:            parts.append("хорошее совпадение")
    else:                        parts.append("частичное совпадение")

    wr = row.get("weighted_rating", 0)
    s  = int(row.get("students_count", 0))
    if wr >= 4.8 and s > 1000:
        parts.append(f"рейтинг {wr:.2f} у {s:,} студентов")
    elif wr >= 4.5:
        parts.append(f"рейтинг {wr:.2f}")

    if row.get("is_free", 0) == 1:
        parts.append("бесплатный")
    else:
        p = int(row.get("price", 0) or 0)
        if p > 0:
            parts.append(f"цена {p:,} тг")

    return "  ·  ".join(parts) if parts else "—"


def precision_at_k(recommended, relevant, k):
    return len(set(recommended[:k]) & set(relevant)) / k

def recall_at_k(recommended, relevant, k):
    if not relevant: return 0
    return len(set(recommended[:k]) & set(relevant)) / len(relevant)

def dcg_at_k(recommended, relevant, k):
    return sum(1 / np.log2(i + 2) for i, item in enumerate(recommended[:k]) if item in relevant)

def ndcg_at_k(recommended, relevant, k):
    dcg = dcg_at_k(recommended, relevant, k)
    ideal = dcg_at_k(relevant, relevant, k)
    return dcg / ideal if ideal > 0 else 0


def recommend(
    query:        str,
    top_k:        int   = 5,
    user_id:      str   = "anonymous",
    language:     str   = "all",
    difficulty:   str   = "any",
    category:     str   = "all",
    top_cat:      str   = "all",
    source:       str   = "all",
    price_filter: str   = "any",
    duration:     str   = "any",
    min_rating:   float = 0.0,
    sort_by:      str   = "relevance",
) -> pd.DataFrame:
    # Пайплайн рекомендаций (5 шагов):
    # 1. normalize_query — транслитерация + синонимы (RU→EN терминология)
    # 2. KNN-поиск по косинусному расстоянию в пространстве эмбеддингов (top-200)
    # 3. Точный поиск по языку программирования (get_lang_candidates) + слияние с KNN
    # 4. Фильтрация по параметрам пользователя, подсчёт final_score = 0.75·sim + 0.25·quality
    # 5. MMR-переранжирование для разнообразия → возврат top_k результатов

    if not query.strip():
        return pd.DataFrame({"Сообщение": ["Введите запрос"]})

    normalized = normalize_query(query)

    user_vec = _get_model().encode([normalized], normalize_embeddings=True)
    n_neighbors = min(200, len(df))
    distances, indices = knn.kneighbors(user_vec, n_neighbors=n_neighbors)

    knn_cands = df.iloc[indices[0]].copy()
    knn_cands["similarity"] = 1 - distances[0]  # косинусное расстояние → сходство
    knn_cands = knn_cands[knn_cands["similarity"] >= SIMILARITY_THRESHOLD]

    # Точный поиск по языку программирования добавляется поверх KNN:
    # KNN может пропустить курс если его эмбеддинг далеко от запроса, но язык совпадает точно.
    lang_cands = get_lang_candidates(query, normalized, df)

    if not lang_cands.empty:
        candidates = pd.concat([lang_cands, knn_cands])
        candidates = candidates[~candidates.index.duplicated(keep="first")]
    else:
        candidates = knn_cands

    if candidates.empty:
        return pd.DataFrame({"Сообщение": ["Ничего не нашлось — попробуй переформулировать запрос"]})

    if language != "all":
        candidates = candidates[candidates["language"] == language]
    if difficulty != "any":
        candidates = candidates[candidates["difficulty"] == difficulty]
    if category != "all":
        candidates = candidates[candidates["category"] == category]
    if top_cat != "all":
        candidates = candidates[candidates["top_category"] == top_cat]
    if source != "all":
        candidates = candidates[candidates["source"] == source]

    if price_filter == "free":
        candidates = candidates[candidates["is_free"] == 1]
    elif price_filter == "paid":
        candidates = candidates[candidates["is_free"] == 0]
    elif price_filter == "cheap":
        candidates = candidates[candidates["price_category"] == "До 5000 тг"]
    elif price_filter == "mid":
        candidates = candidates[candidates["price_category"] == "5000–20000 тг"]
    elif price_filter == "expensive":
        candidates = candidates[candidates["price_category"] == "Дорого (>20000)"]

    if duration == "short":
        candidates = candidates[candidates["duration_category"] == "Короткий (<1 мес)"]
    elif duration == "medium":
        candidates = candidates[candidates["duration_category"] == "Средний (1–3 мес)"]
    elif duration == "long":
        candidates = candidates[candidates["duration_category"] == "Длинный (>3 мес)"]

    if min_rating > 0:
        candidates = candidates[candidates["weighted_rating"] >= min_rating]

    if candidates.empty:
        return pd.DataFrame({"Сообщение": ["Ничего не нашлось — попробуй ослабить фильтры"]})

    candidates = candidates.copy()

    # Итоговый скор: 75% семантическое сходство с запросом + 25% качество курса
    candidates["final_score"] = (
        W_SIMILARITY * candidates["similarity"] +
        W_QUALITY    * candidates["hybrid_score"]
    )

    # Персонализация: поднимаем курсы по тематикам которые пользователь лайкал,
    # опускаем то что он уже видел или пометил "не интересно".
    profile = profile_manager.get(user_id)
    if profile:
        candidates = personalize_scores(candidates, profile)
    else:
        candidates["personal_score"] = candidates["final_score"]

    if sort_by == "rating":
        candidates = candidates.sort_values("weighted_rating", ascending=False)
    elif sort_by == "popularity":
        candidates = candidates.sort_values("students_count", ascending=False)
    else:
        candidates = candidates.sort_values("personal_score", ascending=False)

    candidates = candidates.head(max(top_k * 5, 20))

    # При коротком запросе (≤2 слов) MMR чуть консервативнее (λ=0.80) —
    # запрос размытый, лучше держаться ближе к релевантности.
    query_words  = len(normalized.split())
    lambda_param = 0.80 if query_words <= 2 else 0.70
    candidates   = mmr_rerank(candidates, embeddings, lambda_param=lambda_param, top_k=top_k)

    candidates["объяснение"] = candidates.apply(explain, axis=1)

    cols = [
        "title", "source", "weighted_rating", "difficulty",
        "category", "language", "is_free", "price",
        "duration_category", "similarity", "final_score",
        "объяснение", "url"
    ]
    cols = [c for c in cols if c in candidates.columns]
    return candidates[cols].reset_index(drop=True)


def print_results(recs: pd.DataFrame, show_url: bool = True):
    if "Сообщение" in recs.columns:
        print(f"\n  ⚠  {recs['Сообщение'].iloc[0]}\n")
        return

    print()
    for i, row in recs.iterrows():
        price_val = row.get("price", 0)
        is_free   = row.get("is_free", 0)
        free_tag  = "Бесплатно" if (is_free == 1 or price_val == 0) else f"{int(price_val):,} тг"
        dur_tag   = row.get("duration_category", "—")
        lang_tag  = "🇷🇺 RU" if row.get("language") == "ru" else "🇬🇧 EN"
        rating    = row.get("weighted_rating", 0)
        sim       = row.get("similarity", 0)

        print(f"  {i+1}. {row['title']}")
        print(f"     📦 {row.get('source','?').upper():10} "
              f"⭐ {rating:.2f}  "
              f"{lang_tag}  "
              f"📚 {row.get('difficulty','—'):13} "
              f"💰 {free_tag}  "
              f"⏱ {dur_tag}")
        print(f"     🏷  {row.get('category','—')}")
        if sim > 0:
            print(f"     🎯 sim={sim:.2f}  💡 {row.get('объяснение','—')}")
        else:
            print(f"     💡 {row.get('объяснение','—')}")
        if show_url and row.get("url"):
            print(f"     🔗 {row['url']}")
        print()


def list_categories():
    print("\n  Категории (category):")
    for c in sorted(df["category"].dropna().unique()):
        print(f"    {c}  ({(df['category'] == c).sum()})")
    print("\n  Топ-категории (top_cat):")
    for c in sorted(df["top_category"].dropna().unique()):
        print(f"    {c}  ({(df['top_category'] == c).sum()})")


HELP_TEXT = """
╔═══════════════════════════════════════════════════════════════╗
║   РЕКОМЕНДАТЕЛЬНАЯ СИСТЕМА IT-КУРСОВ  v4.9                   ║
╠═══════════════════════════════════════════════════════════════╣
║  Примеры запросов:                                            ║
║    python          java          kotlin       c++             ║
║    java language=ru              python free                  ║
║    docker          kubernetes    flask        django           ║
║    machine learning language=ru                               ║
║    пайтон difficulty=Beginner free                            ║
║    data science min_rating=4.5 source=stepik                  ║
║    нейросети language=ru duration=medium                      ║
║    devops top=10                                              ║
╠═══════════════════════════════════════════════════════════════╣
║  Фильтры:                                                     ║
║    language=ru|en      source=udemy|stepik|coursera|openedu   ║
║    difficulty=Beginner|Intermediate|Advanced                  ║
║    price=free|paid|cheap|mid|expensive    free                ║
║    duration=short|medium|long    min_rating=4.0|4.5|4.8      ║
║    sort=relevance|rating|popularity       top=5|10|20         ║
╠═══════════════════════════════════════════════════════════════╣
║  Команды:                                                     ║
║    categories · metrics · profile · my                        ║
║    like <слово> · dislike <слово> · clear · help · q          ║
╚═══════════════════════════════════════════════════════════════╝
"""

def parse_input(line: str):
    parts, query_p, filters = line.strip().split(), [], {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            filters[k.lower().strip()] = v.replace("_", " ").strip()
        elif p.lower() in ("free", "бесплатно"):
            filters["price"] = "free"
        else:
            query_p.append(p)
    return " ".join(query_p), filters


def test_metrics():
    print("\n📊 Тест метрик качества\n")
    recommended = ["course1", "course2", "course3", "course4", "course5"]
    relevant    = ["course2", "course3", "course6"]
    print(f"Precision@5: {precision_at_k(recommended, relevant, 5):.2f}")
    print(f"Recall@5:    {recall_at_k(recommended, relevant, 5):.2f}")
    print(f"NDCG@5:      {ndcg_at_k(recommended, relevant, 5):.2f}")


def interactive():
    print(HELP_TEXT)
    USER_ID = "cli_user"

    while True:
        try:
            line = input("Запрос: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nДо встречи!")
            break

        if not line: continue

        if line.lower() in ("q", "выход", "exit"):
            print("До встречи!"); break
        if line.lower() in ("help", "помощь"):
            print(HELP_TEXT); continue
        if line.lower() in ("categories", "категории"):
            list_categories(); continue
        if line.lower() == "profile":
            print("\n👤 Профиль:"); print(profile_manager.get_summary(USER_ID)); continue
        if line.lower() == "metrics":
            test_metrics(); continue
        if line.lower() == "clear":
            profile_manager.get(USER_ID).clear_history()
            print("🗑 История очищена"); continue

        if line.lower() == "my":
            print("\n🔥 Персональные рекомендации (по лайкам):")
            from personalization import recommend_by_likes
            print_results(recommend_by_likes(profile_manager.get(USER_ID), df, top_k=5))
            continue

        if line.startswith("like "):
            term    = line[5:].strip()
            matches = df[df["title"].str.lower().str.contains(term.lower(), na=False)]
            if not matches.empty:
                best = matches.sort_values("weighted_rating", ascending=False).iloc[0]
                profile_manager.track_like(USER_ID, best.to_dict())
                print(f"👍 Лайк сохранён: {best['title']}")
            else:
                profile_manager.track_like(USER_ID, {"title": term})
                print(f"👍 Лайк сохранён (курс не найден точно): {term}")
            continue

        if line.startswith("dislike "):
            title = line[8:].strip()
            profile_manager.track_dislike(USER_ID, title)
            print(f"👎 Дизлайк сохранён: {title}"); continue

        query, f = parse_input(line)
        if not query and not f: continue

        profile_manager.track_search(USER_ID, query)

        top_k        = int(f.get("top", 5))
        sort_by      = f.get("sort", "relevance")
        language     = f.get("language", "all")
        difficulty   = f.get("difficulty", "any")
        category     = f.get("category", "all")
        top_cat      = f.get("top_cat", "all")
        source       = f.get("source", "all")
        price_filter = f.get("price", "any")
        duration     = f.get("duration", "any")
        try:    min_rating = float(f.get("min_rating", 0))
        except: min_rating = 0.0

        norm = normalize_query(query) if query else ""
        print(f"\n  Запрос: '{query}' -> '{norm}'")

        active = {k: v for k, v in {
            "language": language, "difficulty": difficulty,
            "category": category, "top_cat": top_cat,
            "source": source, "price": price_filter,
            "duration": duration, "min_rating": min_rating,
            "sort": sort_by, "top": top_k
        }.items() if v not in ("all", "any", 0, 0.0, "relevance", 5)}
        if active: print(f"  Фильтры: {active}")

        recs = recommend(
            query=query or norm, top_k=top_k, user_id=USER_ID,
            language=language, difficulty=difficulty,
            category=category, top_cat=top_cat, source=source,
            price_filter=price_filter, duration=duration,
            min_rating=min_rating, sort_by=sort_by,
        )
        print_results(recs)

        if "Сообщение" not in recs.columns:
            for _, row in recs.iterrows():
                profile_manager.track_view(USER_ID, row.to_dict())


if __name__ == "__main__":
    df = load_data(DATA_PATH)
    df = add_bayes(df)

    embeddings, knn, df = get_model(df, force_rebuild=False)

    print("✅ Система готова (v4.9)")
    interactive()