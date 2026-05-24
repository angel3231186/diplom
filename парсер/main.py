from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# создаём драйвер один раз
options = Options()
options.page_load_strategy = "eager"
options.add_argument("--headless=new")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def get_best_course(topic):
    driver.get(f"https://www.coursera.org/search?query={topic}")

    wait = WebDriverWait(driver, 5)
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/learn/']"))
    )

    # Берём первую ссылку напрямую через JS
    link = driver.execute_script("""
        return document.querySelector("a[href*='/learn/']").href;
    """)

    return link

# основной цикл — вводим темы построчно
print("Вводите темы построчно, пустая строка = выход")
while True:
    topic = input()
    if topic == "":
        break
    link = get_best_course(topic)
    print(link)

# закрываем драйвер в конце
driver.quit()