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

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка Selenium
driver_path = "C:\\coding\\parsbot\\parsbot\\chromedriver.exe"
service = Service(driver_path)
driver = webdriver.Chrome(service=service)
logger.info("Драйвер Chrome запущен")

# Данные для авторизации
login_url = "https://dmb.sundesiremedia.com/"
stats_url = "https://dmb.sundesiremedia.com/trend-stream/lastweek"
username = "coldfear"
password = "Weakky1703@"

def authorize():
    logger.info("Начинаю авторизацию...")
    driver.get(login_url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "login")))
    driver.find_element(By.ID, "login").send_keys(username)
    driver.find_element(By.ID, "pass").send_keys(password)
    try:
        driver.find_element(By.XPATH, "//input[@value='Login to DMB']").click()
    except:
        driver.find_element(By.XPATH, "//input[@type='submit']").click()
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "profile-username")))
    logger.info("Авторизация успешна")

def get_all_tracks_stats(artist_name=None):
    logger.info("Получаю статистику треков...")
    authorize()
    
    logger.info(f"Перехожу на {stats_url}")
    driver.get(stats_url)
    
    # Ждём появления хотя бы одной строки в таблице
    logger.info("Ожидаю появления строки таблицы...")
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#top-area tbody tr.control-list-row"))
    )
    
    # Даём время на подгрузку видимых данных
    time.sleep(5)
    
    # Берём HTML и сохраняем для отладки
    html = driver.page_source
    with open("debug.html", "w", encoding="utf-8") as f:
        f.write(html)
    logger.info("HTML сохранён в debug.html")
    
    soup = BeautifulSoup(html, "html.parser")
    top_area = soup.find("div", id="top-area")
    if not top_area:
        logger.error("Блок top-area не найден")
        return "Блок с данными треков не найден"
    
    tbody = top_area.find("tbody")
    if not tbody:
        logger.error("Элемент tbody не найден")
        logger.debug(f"Содержимое top-area: {top_area.prettify()}")
        return "Элемент tbody не найден"
    
    rows = tbody.find_all("tr", class_="control-list-row")
    if not rows:
        logger.error("Строки в tbody не найдены")
        return "Данные в таблице отсутствуют"
    
    results = []
    for row in rows:
        title_td = row.find("td", class_="field-sale_title")
        artist_td = row.find("td", class_="field-sale_artist")
        streams_td = row.find("td", class_="field-sale_units")
        
        title = title_td.find("span", class_="column-value").get_text(strip=True) if title_td else "Unknown"
        artist = artist_td.find("span", class_="column-value").get_text(strip=True) if artist_td else "Unknown"
        streams = streams_td.find("span", class_="column-value").get_text(strip=True) if streams_td else "0"
        
        # Фильтруем по имени артиста, если оно указано (регистронезависимо)
        if artist_name is None or artist.lower() == artist_name.lower():
            results.append(f"{title} — {artist} — {streams} стримов")
    
    if results:
        logger.info(f"Найдено {len(results)} треков")
        return "\n".join(results)
    else:
        logger.warning("Треки не найдены")
        return f"Треки для артиста '{artist_name}' не найдены" if artist_name else "Треки не найдены"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Получена команда /start")
    await update.message.reply_text(
        "Привет! Я бот для проверки статистики стримов на DMB.\n"
        "Используй /stats для списка всех треков.\n"
        "Используй /artist <имя_артиста> для поиска по артисту."
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
    finally:
        driver.quit()
        logger.info("Драйвер закрыт")

async def artist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Получена команда /artist")
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажи имя артиста после команды, например: /artist coldfff")
        return
    
    artist_name = " ".join(context.args)  # Собираем имя артиста из аргументов
    logger.info(f"Поиск треков для артиста: {artist_name}")
    await update.message.reply_text(f"Ищу треки для '{artist_name}'...")
    
    try:
        stats = get_all_tracks_stats(artist_name)
        if len(stats) > 4096:
            for i in range(0, len(stats), 4096):
                await update.message.reply_text(stats[i:i + 4096])
        else:
            await update.message.reply_text(stats)
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await update.message.reply_text(f"Ошибка: {str(e)}")
    finally:
        driver.quit()
        logger.info("Драйвер закрыт")

def main():
    token = "7624800237:AAEZHPHTZc1btzeM8_ubSQhCEXUDi2Jy6Xs"
    logger.info(f"Инициализация бота с токеном: {token}")
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("artist", artist))

    logger.info("Бот запущен")
    application.run_polling()

if __name__ == "__main__":
    main()