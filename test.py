from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import time
import logging
import os
import datetime

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка Selenium
driver_path = "C:\\coding\\parsbot\\parsbot\\chromedriver.exe"
logger.info(f"Установка пути к chromedriver: {driver_path}")
service = Service(driver_path)
logger.info("Инициализация сервиса ChromeDriver...")
driver = webdriver.Chrome(service=service)
logger.info("Драйвер Chrome успешно запущен")

# Данные для авторизации
login_url = "https://dmb.sundesiremedia.com/"
stats_url = "https://dmb.sundesiremedia.com/trend-stream/lastweek"
username = "coldfear"
password = "Weakky1703@"
html_file = "stats.html"

def is_logged_in():
    logger.info("Проверка статуса авторизации...")
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "profile-username"))
        )
        logger.info("Сессия активна, пользователь авторизован")
        return True
    except:
        logger.warning("Сессия неактивна, требуется авторизация")
        return False

def authorize_and_download():
    logger.info("Начинаю процесс авторизации и скачивания HTML...")
    driver.get(login_url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "login")))
    driver.find_element(By.ID, "login").send_keys(username)
    driver.find_element(By.ID, "pass").send_keys(password)
    try:
        driver.find_element(By.XPATH, "//input[@value='Login to DMB']").click()
    except:
        driver.find_element(By.XPATH, "//input[@type='submit']").click()
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "profile-username")))
    logger.info("Авторизация завершена успешно")
    
    logger.info(f"Перехожу на страницу статистики: {stats_url}")
    driver.get(stats_url)
    
    logger.info("Ожидаю загрузки страницы и хотя бы одной строки таблицы...")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "top-area"))
    )
    
    # Ждём появления хотя бы одной строки таблицы
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#top-area tr.control-list-row"))
    )
    
    # Прокручиваем страницу для полной загрузки видимых данных
    logger.info("Прокручиваю страницу...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(5)  # Даём немного времени на подгрузку остальных строк
    
    # Сохраняем HTML
    html = driver.page_source
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"HTML сохранён в {html_file}")

def is_file_fresh():
    """Проверяет, актуален ли файл (обновлён менее 24 часов назад)."""
    if not os.path.exists(html_file):
        return False
    file_time = datetime.datetime.fromtimestamp(os.path.getmtime(html_file))
    current_time = datetime.datetime.now()
    age = current_time - file_time
    return age.total_seconds() < 24 * 60 * 60  # 24 часа

def get_all_tracks_stats():
    logger.info("Парсинг статистики всех треков...")
    
    # Проверяем авторизацию и загружаем страницу, если нужно
    if not is_logged_in() or not is_file_fresh():
        logger.info("Требуется авторизация или обновление данных")
        authorize_and_download()
    else:
        logger.info("Сессия активна и файл актуален, использую сохранённый HTML")
    
    # Читаем HTML
    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()
    
    soup = BeautifulSoup(html, "html.parser")
    top_area = soup.find("div", id="top-area")
    
    if not top_area:
        logger.error("Блок top-area не найден")
        return "Блок с данными треков не найден"
    
    table = top_area.find("table", class_="list control-list")
    if not table:
        logger.error("Таблица треков не найдена")
        logger.debug(f"Содержимое top-area: {top_area.prettify()}")
        return "Таблица треков не найдена"
    
    rows = table.find_all("tr", class_="control-list-row")
    if not rows:
        logger.error("Строки в таблице не найдены")
        return "Данные в таблице отсутствуют"
    
    results = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 7:  # Убедимся, что есть все нужные колонки
            title = cols[0].find("span", class_="column-value").get_text(strip=True)  # field-sale_title
            artist = cols[2].find("span", class_="column-value").get_text(strip=True)  # field-sale_artist
            streams = cols[6].find("span", class_="column-value").get_text(strip=True)  # field-sale_units
            results.append(f"{title} — {artist} — {streams} стримов")
    
    if results:
        logger.info(f"Найдено {len(results)} треков")
        return "\n".join(results)
    else:
        logger.warning("Треки не найдены")
        return "Треки не найдены"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Получена команда /start")
    await update.message.reply_text(
        "Привет! Я бот для проверки статистики стримов на DMB.\n"
        "Используй /stats для получения списка всех треков с названием, артистом и стримами."
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Получена команда /stats")
    await update.message.reply_text("Обрабатываю запрос...")

    try:
        stats = get_all_tracks_stats()
        if len(stats) > 4096:
            for i in range(0, len(stats), 4096):
                await update.message.reply_text(stats[i:i + 4096])
        else:
            await update.message.reply_text(stats)
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await update.message.reply_text(f"Ошибка: {str(e)}")

def main():
    token = "7624800237:AAEZHPHTZc1btzeM8_ubSQhCEXUDi2Jy6Xs"
    logger.info(f"Инициализация бота с токеном: {token}")
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))

    logger.info("Бот запущен")
    application.run_polling()
    driver.quit()
    logger.info("Бот остановлен, драйвер закрыт")

if __name__ == "__main__":
    main()