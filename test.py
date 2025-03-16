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
from selenium.common.exceptions import TimeoutException

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
username = "coldfear"
password = "Weakky1703@"
logger.info(f"Установлены данные для авторизации: URL={login_url}, username={username}")

def is_logged_in():
    """Проверяет, авторизован ли бот."""
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

def authorize():
    """Авторизация на сайте."""
    logger.info("Начинаю процесс авторизации...")
    logger.info(f"Открываю страницу авторизации: {login_url}")
    driver.get(login_url)
    
    logger.info("Ожидаю загрузки формы логина...")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "login"))
    )
    logger.info("Форма логина найдена")
    
    logger.info("Ищу поле для ввода логина...")
    login_field = driver.find_element(By.ID, "login")
    logger.info("Поле логина найдено")
    logger.info(f"Ввожу логин: {username}")
    login_field.send_keys(username)
    
    logger.info("Ищу поле для ввода пароля...")
    password_field = driver.find_element(By.ID, "pass")
    logger.info("Поле пароля найдено")
    logger.info("Ввожу пароль...")
    password_field.send_keys(password)
    
    logger.info("Ищу кнопку входа...")
    try:
        login_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@value='Login to DMB']"))
        )
        logger.info("Найдена кнопка 'Login to DMB'")
    except:
        logger.warning("Кнопка 'Login to DMB' не найдена, ищу запасной вариант...")
        login_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit']"))
        )
        logger.info("Найдена кнопка submit (запасной вариант)")
    
    logger.info("Нажимаю кнопку входа...")
    login_button.click()
    
    logger.info("Ожидаю появления дашборда...")
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "profile-username"))
        )
        logger.info("Авторизация завершена успешно")
    except:
        logger.error(f"Не удалось подтвердить вход. Текущий URL: {driver.current_url}")
        with open("login_page_after_submit.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logger.info("HTML страницы после попытки входа сохранён в login_page_after_submit.html")
        raise Exception("Ошибка авторизации — дашборд не загрузился")

def go_to_stats():
    if not is_logged_in():
        logger.error("Сессия истекла, требуется авторизация")
        raise Exception("Сессия истекла, требуется авторизация")
    
    stats_url = "https://dmb.sundesiremedia.com/trend-stream/lastweek"
    logger.info(f"Перехожу на страницу статистики: {stats_url}")
    driver.get(stats_url)
    
    logger.info("Ожидаю загрузки страницы...")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    
    current_url = driver.current_url
    logger.info(f"Текущий URL: {current_url}")
    if "trend-stream/lastweek" not in current_url:
        raise Exception(f"Редирект на неверную страницу: {current_url}")
    
    # Проверяем таблицу через JavaScript
    logger.info("Проверяю наличие строк таблицы через JavaScript...")
    for _ in range(3):  # 3 попытки с интервалом
        row_count = driver.execute_script(
            "return document.querySelectorAll('table.list.control-list tr.control-list-row').length;"
        )
        logger.info(f"Найдено строк: {row_count}")
        if row_count > 0:
            logger.info("Таблица загружена")
            return
        time.sleep(5)  # Ждем 5 секунд между попытками
    
    # Если таблица не загрузилась, пробуем найти данные в JS-переменных
    logger.info("Таблица не найдена, ищу данные в JavaScript...")
    js_data = driver.execute_script("return window.someData || window.chartData || [];")
    if js_data:
        logger.info(f"Найдены данные в JavaScript: {js_data[:200]}...")
        # Здесь нужно будет обработать js_data в get_artist_stats()
    else:
        logger.error("Данные не найдены ни в таблице, ни в JS")
        with open("stats_page_error.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        raise Exception("Не удалось найти данные")

def get_artist_stats(artist_name):
    """Получение статистики по артисту: название трека, никнейм, стримы."""
    logger.info(f"Парсинг статистики для артиста '{artist_name}'...")
    
    html = driver.page_source
    with open("stats_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    logger.info("HTML страницы сохранён в stats_page.html для отладки")
    
    soup = BeautifulSoup(html, "html.parser")
    
    logger.info("Ищу таблицу с классом 'list control-list'...")
    table = soup.find("table", class_="list control-list")
    if not table:
        logger.error("Таблица не найдена в HTML")
        return "Таблица не найдена"
    
    tbody = table.find("tbody")
    if not tbody:
        logger.error("В таблице не найден <tbody>")
        return "Таблица не найдена"
    
    rows = tbody.find_all("tr", class_="control-list-row")
    logger.info(f"Найдено {len(rows)} строк в таблице")
    
    results = []
    artist_name_normalized = unicodedata.normalize("NFKD", artist_name).strip().lower()
    
    for i, row in enumerate(rows, 1):
        try:
            title = row.find("td", class_="field-sale_title").find("span", class_="column-value").text.strip()
            artist = row.find("td", class_="field-sale_artist").find("span", class_="column-value").text.strip()
            streams = row.find("td", class_="field-sale_units").find("span", class_="column-value").text.strip()
            
            artist_normalized = unicodedata.normalize("NFKD", artist).strip().lower()
            logger.debug(f"Строка {i}: Название='{title}', Артист='{artist}', Стримы='{streams}'")
            
            if artist_name_normalized in artist_normalized:
                results.append(f"{title} — {artist} — {streams} стримов")
        except AttributeError:
            logger.warning(f"Ошибка в строке {i}: не удалось извлечь данные")
            continue
    
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
        if "authorized" not in context.bot_data or not is_logged_in():
            logger.info("Требуется авторизация")
            authorize()
            go_to_stats()
            context.bot_data["authorized"] = True
        else:
            logger.info("Уже авторизован, обновляю страницу статистики")
            go_to_stats()

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