import re
import time
import numpy as np
import pandas as pd

TEST_CASES = [
    {"label": "Python",          "query": "python",          "relevant": {"pl": "Python"}},
    {"label": "Java",            "query": "java",            "relevant": {"pl": "Java"}},
    {"label": "SQL",             "query": "sql",             "relevant": {"pl": "SQL"}},
    {"label": "C++",             "query": "c++",             "relevant": {"pl": "C/C++"}},
    {"label": "Ruby",            "query": "ruby on rails",   "relevant": {"title": r"ruby"}},
    {"label": "Go",              "query": "golang",          "relevant": {"pl": "Go"}},
    {"label": "Docker",          "query": "docker",          "relevant": {"title": r"docker"}},
    {"label": "Kubernetes",      "query": "kubernetes",      "relevant": {"title": r"kubernetes|k8s"}},
    {"label": "React",           "query": "react",           "relevant": {"title": r"react"}},
    {"label": "Django",          "query": "django",          "relevant": {"title": r"django"}},
    {"label": "Kotlin",          "query": "kotlin",          "relevant": {"title": r"kotlin"}},
    {"label": "Spring",          "query": "spring",          "relevant": {"title": r"spring"}},
    {"label": "Machine Learning","query": "machine learning","relevant": {"title": r"machine learning|deep learning|neural"}},
    {"label": "Data Science",    "query": "data science",    "relevant": {"title": r"data science|machine learning|data analysis"}},
    {"label": "DevOps",          "query": "devops",          "relevant": {"top_cat": "DevOps"}},
    {"label": "Mobile Dev",      "query": "android",         "relevant": {"top_cat": "Mobile"}},
    {"label": "Security",        "query": "cybersecurity",   "relevant": {"top_cat": "Security"}},
    {"label": "Design",          "query": "ui ux design",    "relevant": {"top_cat": "Design"}},
    {"label": "Нейросети (RU)",       "query": "нейросети",          "relevant": {"top_cat": "Data Science"}},
    {"label": "Программирование (RU)","query": "программирование",   "relevant": {"title": r"python|java|programming|c\+\+|javascript"}},
    {"label": "Базы данных (RU)",      "query": "базы данных",        "relevant": {"title": r"sql|database|базы данных|postgresql|mysql"}},
    {"label": "Девопс (RU)",           "query": "девопс",             "relevant": {"top_cat": "DevOps"}},
    {"label": "Python RU",       "query": "python",  "relevant": {"pl": "Python"},
     "filters": {"language": "ru"}},
    {"label": "Python бесплатно","query": "python",  "relevant": {"pl": "Python"},
     "filters": {"price_filter": "free"}},
    {"label": "Java Beginner",   "query": "java",    "relevant": {"pl": "Java"},
     "filters": {"difficulty": "Beginner"}},
]


def make_relevant_mask(df: pd.DataFrame, criteria: dict) -> pd.Series:
    mask = pd.Series(True, index=df.index)

    if "pl" in criteria:
        col = df.get("programming_language", pd.Series("", index=df.index)).fillna("")
        mask &= col.str.lower().str.contains(criteria["pl"].lower(), na=False)

    if "top_cat" in criteria:
        col = df.get("top_category", pd.Series("", index=df.index)).fillna("")
        mask &= col.str.lower().str.contains(criteria["top_cat"].lower(), na=False)

    if "cat" in criteria:
        col = df.get("category", pd.Series("", index=df.index)).fillna("")
        mask &= col.str.lower().str.contains(criteria["cat"].lower(), na=False)

    if "title" in criteria:
        col = df.get("title", pd.Series("", index=df.index)).fillna("")
        mask &= col.str.contains(criteria["title"], case=False, na=False, regex=True)

    return mask


def precision_at_k(hits: list[bool], k: int) -> float:
    return sum(hits[:k]) / k if k > 0 else 0.0


def recall_at_k(hits: list[bool], n_relevant: int, k: int) -> float:
    if n_relevant == 0:
        return 0.0
    return sum(hits[:k]) / n_relevant


def dcg_at_k(hits: list[bool], k: int) -> float:
    return sum(1.0 / np.log2(i + 2) for i, h in enumerate(hits[:k]) if h)


def ndcg_at_k(hits: list[bool], n_relevant: int, k: int) -> float:
    dcg   = dcg_at_k(hits, k)
    ideal = dcg_at_k([True] * min(n_relevant, k), k)
    return dcg / ideal if ideal > 0 else 0.0


def mrr(hits: list[bool]) -> float:
    for i, h in enumerate(hits):
        if h:
            return 1.0 / (i + 1)
    return 0.0


def hit_rate_at_k(hits: list[bool], k: int) -> float:
    return float(any(hits[:k]))


def evaluate_case(case: dict, df: pd.DataFrame, k: int = 5) -> dict:
    import sys as _sys
    _main = _sys.modules.get("_coursefind_main") or _sys.modules.get("main")
    if _main is None:
        import main as _main

    query   = case["query"]
    filters = case.get("filters", {})

    rel_mask  = make_relevant_mask(df, case["relevant"])
    n_relevant = int(rel_mask.sum())
    rel_titles = set(df[rel_mask]["title"].str.lower().tolist())

    if n_relevant == 0:
        return {
            "label": case["label"], "query": query,
            "n_relevant": 0, "error": "Нет релевантных курсов в датасете",
        }

    t0 = time.perf_counter()
    try:
        recs = _main.recommend(
            query=query, top_k=k, user_id="eval",
            language=filters.get("language", "all"),
            difficulty=filters.get("difficulty", "any"),
            category="all", top_cat="all",
            source=filters.get("source", "all"),
            price_filter=filters.get("price_filter", "any"),
            duration="any", min_rating=0.0, sort_by="relevance",
        )
    except Exception as e:
        return {"label": case["label"], "query": query, "error": str(e)}
    elapsed = time.perf_counter() - t0

    if "Сообщение" in recs.columns or recs.empty:
        return {
            "label": case["label"], "query": query,
            "n_relevant": n_relevant, "n_retrieved": 0,
            "precision": 0, "recall": 0, "ndcg": 0,
            "mrr": 0, "hit_rate": 0,
            "avg_sim": 0, "time_ms": round(elapsed * 1000, 1),
        }

    rec_titles = recs["title"].str.lower().tolist()
    hits       = [t in rel_titles for t in rec_titles]
    avg_sim    = float(recs["similarity"].mean()) if "similarity" in recs else 0.0

    return {
        "label":       case["label"],
        "query":       query,
        "filters":     str(filters) if filters else "—",
        "n_relevant":  n_relevant,
        "n_retrieved": len(recs),
        "precision":   round(precision_at_k(hits, k), 3),
        "recall":      round(recall_at_k(hits, n_relevant, k), 3),
        "ndcg":        round(ndcg_at_k(hits, n_relevant, k), 3),
        "mrr":         round(mrr(hits), 3),
        "hit_rate":    round(hit_rate_at_k(hits, k), 3),
        "avg_sim":     round(avg_sim, 3),
        "time_ms":     round(elapsed * 1000, 1),
    }


def run_evaluation(
    df: pd.DataFrame,
    k: int = 5,
    progress_cb=None,
) -> tuple[pd.DataFrame, dict]:
    results = []
    for i, case in enumerate(TEST_CASES):
        if progress_cb:
            progress_cb(i, len(TEST_CASES))
        results.append(evaluate_case(case, df, k=k))

    if progress_cb:
        progress_cb(len(TEST_CASES), len(TEST_CASES))

    valid = [r for r in results if "error" not in r and r.get("n_retrieved", 0) > 0]
    df_results = pd.DataFrame(results)

    if not valid:
        return df_results, {}

    metrics_cols = ["precision", "recall", "ndcg", "mrr", "hit_rate", "avg_sim", "time_ms"]
    agg = {}
    for col in metrics_cols:
        vals = [r[col] for r in valid if col in r]
        agg[f"mean_{col}"] = round(float(np.mean(vals)), 3) if vals else 0.0

    agg["n_test_cases"] = len(TEST_CASES)
    agg["n_valid"]      = len(valid)
    agg["success_rate"] = round(len(valid) / len(TEST_CASES), 3)

    return df_results, agg


DISPLAY_COLS = {
    "label":      "Сценарий",
    "query":      "Запрос",
    "filters":    "Фильтры",
    "n_relevant": "Релевантных",
    "precision":  "Precision@K",
    "recall":     "Recall@K",
    "ndcg":       "NDCG@K",
    "mrr":        "MRR",
    "hit_rate":   "Hit Rate",
    "avg_sim":    "Avg Sim",
    "time_ms":    "Время (мс)",
}


def print_report(df_results: pd.DataFrame, agg: dict, k: int = 5):
    sep = "─" * 72
    print(f"\n{'═' * 72}")
    print(f"  ОЦЕНКА РЕКОМЕНДАТЕЛЬНОЙ СИСТЕМЫ  (K = {k})")
    print(f"{'═' * 72}\n")

    valid = df_results[~df_results.get("error", pd.Series("", index=df_results.index)).astype(bool)]
    if "error" in df_results.columns:
        valid = df_results[df_results["error"].isna() | (df_results["error"] == "")]
    else:
        valid = df_results

    for _, row in df_results.iterrows():
        label = row.get("label", row.get("query", "—"))
        if "error" in row and row["error"]:
            print(f"  {label:25}  ОШИБКА: {row['error']}")
            continue
        print(
            f"  {label:25}"
            f"  P@{k}={row.get('precision', 0):.3f}"
            f"  R@{k}={row.get('recall', 0):.3f}"
            f"  NDCG={row.get('ndcg', 0):.3f}"
            f"  MRR={row.get('mrr', 0):.3f}"
            f"  HR={row.get('hit_rate', 0):.3f}"
            f"  {row.get('time_ms', 0):.0f}мс"
        )

    print(f"\n{sep}")
    print("  СРЕДНИЕ ЗНАЧЕНИЯ")
    print(sep)
    print(f"  Precision@{k}  : {agg.get('mean_precision', 0):.3f}")
    print(f"  Recall@{k}     : {agg.get('mean_recall', 0):.3f}")
    print(f"  NDCG@{k}       : {agg.get('mean_ndcg', 0):.3f}")
    print(f"  MRR          : {agg.get('mean_mrr', 0):.3f}")
    print(f"  Hit Rate@{k}   : {agg.get('mean_hit_rate', 0):.3f}")
    print(f"  Avg Similarity: {agg.get('mean_avg_sim', 0):.3f}")
    print(f"  Среднее время : {agg.get('mean_time_ms', 0):.1f} мс")
    print(f"\n  Сценариев всего : {agg.get('n_test_cases', 0)}")
    print(f"  Успешных        : {agg.get('n_valid', 0)}")
    print(f"  Success rate    : {agg.get('success_rate', 0):.1%}")
    print(f"\n{'═' * 72}\n")


if __name__ == "__main__":
    import main as _main

    print("Загружаем данные и модель...")
    df = _main.load_data(_main.DATA_PATH)
    df = _main.add_bayes(df)
    embeddings, knn, df = _main.get_model(df, force_rebuild=False)
    _main.df         = df
    _main.embeddings = embeddings
    _main.knn        = knn

    K = 5
    print(f"Запускаем оценку ({len(TEST_CASES)} сценариев, K={K})...\n")

    df_results, agg = run_evaluation(df, k=K)
    print_report(df_results, agg, k=K)
