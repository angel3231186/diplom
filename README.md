# CourseFind — Рекомендательная система IT-курсов

Веб-приложение для поиска и персональных рекомендаций онлайн-курсов по IT и смежным направлениям.

## Технологии

- **Python 3.11+**
- **Streamlit** — веб-интерфейс
- **Sentence Transformers** — семантический поиск (paraphrase-multilingual-mpnet-base-v2)
- **scikit-learn** — KNN-поиск по эмбеддингам
- **pandas / openpyxl** — работа с датасетом
- **Claude API** — AI-чат ассистент

## Структура проекта

```
├── app.py                      # Главный файл приложения
├── main.py                     # Модель рекомендаций, поиск
├── auth.py                     # Авторизация и регистрация
├── gamification.py             # XP, стрики, достижения
├── personalization.py          # Профили пользователей
├── styles.py                   # CSS стили 
├── evaluation.py               # Метрики качества рекомендаций
├── chat_history_server.py      # Локальный HTTP-сервер для чата
├── final_dataset_ready.xlsx    # Датасет курсов (7600+ курсов)
├── requirements.txt            # Зависимости
├── model/                      # Кэш модели (эмбеддинги)
├── user_profiles/              # Профили пользователей (JSON)
├── chat_history/               # История чатов (JSON)
├── pages/                      # Дополнительные страницы Streamlit
├── backups/                    # Резервные копии датасета
└── scripts/                    # Вспомогательные скрипты
```

## Запуск

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Датасет

7606 курсов с платформ Coursera, Udemy, Stepik и других.  
25 категорий: Data Science / ML / AI, Python, Frontend, DevOps, SQL, Fullstack и др.
