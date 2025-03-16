from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import time
import unicodedata
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
    
    logger.info("Ожидаю загрузки страницы...")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    
    # Прокручиваем страницу для загрузки видимых данных
    logger.info("Прокручиваю страницу...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(5)  # Даём время на рендеринг
    
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

def get_artist_stats(artist_name):
    logger.info(f"Парсинг статистики для артиста '{artist_name}' из файла {html_file}...")
    
    # Читаем сохранённый HTML
    if not os.path.exists(html_file):
        logger.error(f"Файл {html_file} не найден")
        return "Файл статистики не найден"
    
    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()
    
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="list control-list")
    
    if not table:
        logger.error("Таблица не найдена в HTML")
        return "Таблица не найдена"
    
    tbody = table.find("tbody")
    if not tbody:
        logger.error("В таблице не найден <tbody>")
        return "Таблица не найдена"
    
    # Собираем весь текст из <tbody>
    tbody_text = tbody.get_text(separator="\n").strip()
    logger.info(f"Текст из <tbody>:\n{tbody_text[:500]}...")  # Показываем первые 500 символов
    
    # Разбиваем текст на строки
    lines = [line.strip() for line in tbody_text.split("\n") if line.strip()]
    logger.info(f"Найдено {len(lines)} строк текста")
    
    results = []
    artist_name_normalized = unicodedata.normalize("NFKD", artist_name).strip().lower()
    
    # Классификация данных
    i = 0
    while i < len(lines):
        line = lines[i]
        # Ищем строку с артистом
        if artist_name_normalized in unicodedata.normalize("NFKD", line).lower():
            title = line  # Предполагаем, что это название или артист
            artist = line
            streams = None
            
            # Проверяем следующую строку на стримы
            if i + 1 < len(lines) and re.match(r"^\d+$", lines[i + 1]):
                streams = lines[i + 1]
                i += 1
            
            # Если есть стримы, уточняем название
            if streams:
                if i > 0 and lines[i - 2] and not re.match(r"^\d+$", lines[i - 2]):
                    title = lines[i - 2]
                results.append(f"{title} — {artist} — {streams} стримов")
        i += 1
    
    if results:
        logger.info(f"Найдено {len(results)} записей для артиста '{artist_name}'")
        return "\n".join(results)
    else:
        logger.warning(f"Артист '{artist_name}' не найден")
        return f"Артист '{artist_name}' не найден"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Получена команда /start")
    await update.message.reply_text(
        "Привет! Я бот для проверки статистики стримов на DMB.\n"
        "Используй /stats <имя_артиста> для получения данных.\n"
        "Пример: /stats killamyself"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Получена команда /stats")
    if not context.args:
        await update.message.reply_text("Укажи имя артиста. Пример: /stats killamyself")
        return
    
    artist_name = " ".join(context.args)
    logger.info(f"Запрос статистики для артиста: '{artist_name}'")
    await update.message.reply_text(f"Обрабатываю запрос для '{artist_name}'...")

    try:
        # Если файла нет или он старый, скачиваем новый
        if not is_file_fresh():
            logger.info("Файл отсутствует или устарел, требуется авторизация и скачивание")
            authorize_and_download()
        else:
            logger.info("Использую существующий файл stats.html")
        
        stats = get_artist_stats(artist_name)
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