"""
Проверка и обновление цен в датасете.

Запуск:
    python3 check_prices.py                        # проверить все Stepik (~20 мин) и обновить xlsx
    python3 check_prices.py --sample 50            # проверить 50 случайных
    python3 check_prices.py --no-update            # только отчёт, без записи в xlsx

Результат: обновлённый final_dataset_ready.xlsx + отчёт price_check_report.xlsx
"""

import argparse
import re
import time
import random

import pandas as pd
import requests

DATASET_PATH = "final_dataset_ready.xlsx"
REPORT_PATH  = "price_check_report.xlsx"
RUB_TO_KZT   = 5.5

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})


def price_category(price: float, is_free: int) -> str:
    if is_free == 1 or price == 0:
        return "Бесплатно"
    elif price < 5000:
        return "До 5000 тг"
    elif price <= 20000:
        return "5000–20000 тг"
    else:
        return "Дорого (>20000)"


def parse_stepik_price(url: str) -> float | None:
    """Возвращает текущую цену в рублях со страницы Stepik."""
    try:
        url = re.sub(r"/(promo|info)/?$", "", url.strip())
        r = SESSION.get(url, timeout=15)
        if r.status_code != 200:
            return None
        html = r.text

        # Основной путь: unicode-escaped JSON внутри HTML-страницы
        # Stepik встраивает: \u0022price\u0022: \u00227900.00\u0022, \u0022currency_code\u0022: \u0022RUB\u0022
        m = re.search(
            r'\\u0022price\\u0022:\s*\\u0022([\d.]+)\\u0022'
            r'.*?\\u0022currency_code\\u0022:\s*\\u0022(RU[A-Z]*)',
            html,
        )
        if m:
            price = float(m.group(1))
            if price > 0:
                return price

        # Запасной: обычный JSON-блок
        m = re.search(
            r'"price"\s*:\s*"?([\d]+(?:[.,]\d+)?)"?'
            r'.*?"currency_code"\s*:\s*"(RU[A-Z]*)"',
            html,
        )
        if m:
            price = float(m.group(1).replace(",", "."))
            if price > 0:
                return price

        # Последний вариант: display_price
        m = re.search(r'\\u0022display_price\\u0022:\s*\\u0022([\d]+)', html)
        if m:
            price = float(m.group(1))
            if price > 0:
                return price

        return None
    except Exception:
        return None


def check_row(row) -> dict:
    url       = str(row.get("url", "") or "")
    old_kzt   = float(row.get("price", 0) or 0)   # уже в тенге после нашей конвертации
    title     = str(row.get("title", ""))

    result = {
        "idx":       row.name,
        "title":     title,
        "url":       url,
        "old_kzt":   old_kzt,
        "rub_site":  None,
        "new_kzt":   None,
        "diff_pct":  None,
        "status":    "error",
    }

    if not url:
        result["status"] = "no_url"
        return result

    rub = parse_stepik_price(url)
    if rub is None:
        return result

    new_kzt  = round(rub * RUB_TO_KZT)
    diff_pct = ((new_kzt - old_kzt) / old_kzt * 100) if old_kzt > 0 else None

    result.update({
        "rub_site": rub,
        "new_kzt":  new_kzt,
        "diff_pct": round(diff_pct, 1) if diff_pct is not None else None,
        "status":   "changed" if abs(new_kzt - old_kzt) > 300 else "ok",
    })
    return result


def run(args):
    df   = pd.read_excel(DATASET_PATH)
    paid = df[(df["source"] == "stepik") & (df["price"] > 0)].copy()

    if args.sample:
        paid = paid.sample(min(args.sample, len(paid)), random_state=42)

    total = len(paid)
    print(f"Stepik платных курсов к проверке: {total}")
    print(f"Примерное время: ~{total * 1.2 / 60:.0f} мин\n")

    results  = []
    ok_cnt   = 0
    chg_cnt  = 0
    err_cnt  = 0

    for i, (_, row) in enumerate(paid.iterrows(), 1):
        res = check_row(row)
        results.append(res)

        icon = {"ok": "✓", "changed": "!", "error": "✗", "no_url": "—"}.get(res["status"], "?")
        print(
            f"[{i:4}/{total}] {icon}  "
            f"было {res['old_kzt']:>8.0f} тг  →  "
            f"стало {str(res['new_kzt']) if res['new_kzt'] else '—':>8} тг  "
            f"{res['title'][:55]}"
        )

        if res["status"] == "ok":      ok_cnt  += 1
        elif res["status"] == "changed": chg_cnt += 1
        else:                            err_cnt += 1

        if res["status"] in ("ok", "changed"):
            time.sleep(random.uniform(0.8, 1.5))   # вежливая пауза

        # Прогресс каждые 50 курсов
        if i % 50 == 0:
            print(f"\n  → {i}/{total} готово | ✓ {ok_cnt}  ! {chg_cnt}  ✗ {err_cnt}\n")

    report_df = pd.DataFrame(results)

    print(f"\n{'─'*65}")
    print(f"Проверено:    {total}")
    print(f"Не изменились: {ok_cnt}")
    print(f"Изменились:    {chg_cnt}")
    print(f"Ошибки:        {err_cnt}")
    print(f"{'─'*65}")

    # ── Сохраняем отчёт ──────────────────────────────────────────────────────
    changed_df = report_df[report_df["status"] == "changed"]
    errors_df  = report_df[report_df["status"] == "error"]

    with pd.ExcelWriter(REPORT_PATH, engine="openpyxl") as writer:
        report_df.to_excel(writer, index=False, sheet_name="Все результаты")
        if not changed_df.empty:
            changed_df.to_excel(writer, index=False, sheet_name="Изменились")
        if not errors_df.empty:
            errors_df.to_excel(writer, index=False, sheet_name="Ошибки")
    print(f"Отчёт → {REPORT_PATH}")

    # ── Обновляем датасет ────────────────────────────────────────────────────
    if args.update:
        updated = 0
        for res in results:
            if res["status"] in ("ok", "changed") and res["new_kzt"] is not None:
                idx = res["idx"]
                df.at[idx, "price"]          = res["new_kzt"]
                df.at[idx, "price_category"] = price_category(res["new_kzt"], int(df.at[idx, "is_free"]))
                updated += 1

        df.to_excel(DATASET_PATH, index=False)
        print(f"Датасет обновлён: {updated} цен записано → {DATASET_PATH}")
        print("Не забудь удалить кэш модели (model/df.pkl, model/embeddings.npy) и перезапустить приложение.")
    else:
        print("Датасет НЕ изменён (передай --update чтобы записать цены).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Проверка и обновление цен Stepik")
    parser.add_argument("--sample",    type=int,            help="Проверить N случайных курсов")
    parser.add_argument("--no-update", dest="update", action="store_false",
                        help="Только отчёт, без записи в xlsx")
    parser.set_defaults(update=True)
    args = parser.parse_args()
    run(args)
