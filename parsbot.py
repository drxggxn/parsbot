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

# Настройка Selenium
driver_path = "C:\\coding\\parsbot\\parsbot\\chromedriver.exe"
print(f"[INFO] Установка пути к chromedriver: {driver_path}")
service = Service(driver_path)
print("[INFO] Инициализация сервиса ChromeDriver...")
driver = webdriver.Chrome(service=service)
print("[INFO] Драйвер Chrome успешно запущен")

# Данные для авторизации
login_url = "https://dmb.sundesiremedia.com/"
username = "coldfear"
password = "Weakky1703@"
print(f"[INFO] Установлены данные для авторизации: URL={login_url}, username={username}, password={password}")

def is_logged_in():
    """Проверяет, авторизован ли бот, по наличию элемента профиля."""
    print("[INFO] Проверка статуса авторизации...")
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "profile-username"))
        )
        print("[SUCCESS] Сессия активна, пользователь авторизован")
        return True
    except:
        print("[WARNING] Сессия неактивна, требуется авторизация")
        return False

def authorize():
    """Авторизация на сайте."""
    print("[INFO] Начинаю процесс авторизации...")
    print(f"[INFO] Открываю страницу авторизации: {login_url}")
    driver.get(login_url)
    
    print("[INFO] Ожидаю загрузки формы логина...")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "login"))
    )
    print("[SUCCESS] Форма логина найдена")
    
    print("[INFO] Ищу поле для ввода логина...")
    login_field = driver.find_element(By.ID, "login")
    print("[SUCCESS] Поле логина найдено")
    print(f"[INFO] Ввожу логин: {username}")
    login_field.send_keys(username)
    
    print("[INFO] Ищу поле для ввода пароля...")
    password_field = driver.find_element(By.ID, "pass")
    print("[SUCCESS] Поле пароля найдено")
    print("[INFO] Ввожу пароль...")
    password_field.send_keys(password)
    
    print("[INFO] Ищу кнопку входа...")
    try:
        login_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@value='Login to DMB']"))
        )
        print("[SUCCESS] Найдена кнопка 'Login to DMB'")
    except:
        print("[WARNING] Кнопка 'Login to DMB' не найдена, ищу запасной вариант...")
        login_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit']"))
        )
        print("[SUCCESS] Найдена кнопка submit (запасной вариант)")
    
    print("[INFO] Нажимаю кнопку входа...")
    login_button.click()
    
    print("[INFO] Ожидаю появления дашборда...")
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "profile-username"))
        )
        print("[SUCCESS] Авторизация завершена успешно")
    except:
        print(f"[ERROR] Не удалось подтвердить вход. Текущий URL: {driver.current_url}")
        with open("login_page_after_submit.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("[INFO] HTML страницы после попытки входа сохранён в login_page_after_submit.html")
        raise Exception("Ошибка авторизации — дашборд не загрузился")

def go_to_stats():
    """Переход на страницу статистики."""
    print("[INFO] Проверяю статус авторизации перед переходом на страницу статистики...")
    if not is_logged_in():
        print("[ERROR] Сессия истекла, требуется повторная авторизация")
        raise Exception("Сессия истекла, требуется повторная авторизация")
    
    print("[INFO] Ищу ссылку на страницу статистики...")
    stats_link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[@href='/trend-stream/lastweek']"))
    )
    print("[SUCCESS] Ссылка на страницу статистики найдена")
    time.sleep(1)
    
    print("[INFO] Перехожу на страницу статистики...")
    stats_link.click()
    
    print("[INFO] Ожидаю загрузки таблицы с id='control-table-window'...")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "control-table-window"))
    )
    print("[SUCCESS] Таблица с id='control-table-window' найдена в DOM")
    
    print("[INFO] Добавляю дополнительную задержку для полной загрузки данных...")
    time.sleep(3)
    
    print("[INFO] Прокручиваю страницу до конца для подгрузки всех строк...")
    for i in range(3):
        print(f"[INFO] Прокрутка {i + 1}/3...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
    print("[SUCCESS] Прокрутка завершена")
    print("[SUCCESS] Страница статистики полностью загружена")

def get_artist_stats(artist_name):
    """Получение статистики по артисту."""
    print(f"[INFO] Начинаю парсинг статистики для артиста '{artist_name}'...")
    
    print("[INFO] Ожидаю появления таблицы с данными (id='control-table-window')...")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "control-table-window"))
    )
    print("[SUCCESS] Таблица найдена в DOM")
    
    print("[INFO] Прокручиваю страницу до конца для подгрузки всех строк...")
    for i in range(3):
        print(f"[INFO] Прокрутка {i + 1}/3...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
    print("[SUCCESS] Прокрутка завершена")
    
    print("[INFO] Получаю HTML страницы...")
    html = driver.page_source
    print(f"[INFO] Длина HTML: {len(html)} символов")
    with open("stats_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("[INFO] HTML сохранён в stats_page.html для отладки")
    
    print("[INFO] Парсинг HTML с помощью BeautifulSoup...")
    soup = BeautifulSoup(html, "html.parser")
    
    print("[INFO] Ищу таблицу с id='control-table-window'...")
    table = soup.find("table", id="control-table-window")
    if not table:
        print("[ERROR] Таблица с id='control-table-window' не найдена в HTML")
        return "Таблица не найдена"
    print("[SUCCESS] Таблица с id='control-table-window' найдена")
    
    print("[INFO] Ищу <tbody> внутри таблицы...")
    tbody = table.find("tbody")
    if not tbody:
        print("[ERROR] В таблице не найден <tbody>")
        return "Таблица не найдена"
    print("[SUCCESS] <tbody> найден")
    
    print(f"[DEBUG] Содержимое <tbody> (первые 500 символов): {tbody.prettify()[:500]}...")
    
    print("[INFO] Ищу все строки с классом 'control-list-row'...")
    rows = tbody.find_all("tr", class_="control-list-row")
    print(f"[INFO] Найдено {len(rows)} строк в таблице")
    
    results = []
    for i, row in enumerate(rows, 1):
        print(f"\n[INFO] Обработка строки {i}/{len(rows)}...")
        
        print("[DEBUG] Ищу ячейку с названием трека (field-sale_title)...")
        title_cell = row.find("td", class_="field-sale_title")
        print("[DEBUG] Ищу ячейку с именем артиста (field-sale_artist)...")
        artist_cell = row.find("td", class_="field-sale_artist")
        print("[DEBUG] Ищу ячейку с количеством стримов (field-sale_units)...")
        streams_cell = row.find("td", class_="field-sale_units")
        
        if not all([title_cell, artist_cell, streams_cell]):
            print(f"[WARNING] Не все ячейки найдены в строке {i}")
            continue
        print("[SUCCESS] Все ячейки (title, artist, streams) найдены")
        
        print("[DEBUG] Извлекаю текст из ячейки названия трека...")
        title_span = title_cell.find("span", class_="column-value")
        print("[DEBUG] Извлекаю текст из ячейки имени артиста...")
        artist_span = artist_cell.find("span", class_="column-value")
        print("[DEBUG] Извлекаю текст из ячейки количества стримов...")
        streams_span = streams_cell.find("span", class_="column-value")
        
        if not all([title_span, artist_span, streams_span]):
            print(f"[WARNING] Не все span-элементы найдены в строке {i}")
            continue
        print("[SUCCESS] Все span-элементы (title, artist, streams) найдены")
        
        title_text = unicodedata.normalize("NFKD", title_span.text).strip()
        artist_text = unicodedata.normalize("NFKD", artist_span.text).strip()
        streams_text = streams_span.text.strip().replace(",", "")
        
        print(f"[INFO] Извлечённые данные: Название='{title_text}', Артист='{artist_text}', Стримы='{streams_text}'")
        
        artist_name_normalized = unicodedata.normalize("NFKD", artist_name).strip().lower()
        artist_text_normalized = artist_text.lower()
        print(f"[DEBUG] Сравниваю: запрос='{artist_name_normalized}', артист из таблицы='{artist_text_normalized}'")
        print(f"[DEBUG] Условие совпадения: {artist_name_normalized} in {artist_text_normalized} = {artist_name_normalized in artist_text_normalized}")
        
        if artist_name_normalized in artist_text_normalized:
            print(f"[SUCCESS] Совпадение найдено! Добавляю трек '{title_text}' в результаты")
            results.append(f"{title_text} — {streams_text} стримов")
        else:
            print(f"[INFO] Совпадение не найдено, пропускаю строку")
    
    if results:
        print(f"[SUCCESS] Найдено {len(results)} записей для артиста '{artist_name}'")
        return "\n".join(results)
    else:
        print(f"[WARNING] Артист '{artist_name}' не найден")
        return f"Артист '{artist_name}' не найден"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("[INFO] Получена команда /start")
    await update.message.reply_text(
        "Привет! Я бот для проверки статистики стримов на DMB.\n"
        "Используй команду /stats <имя_артиста>, чтобы получить статистику.\n"
        "Например: /stats Drake"
    )
    print("[SUCCESS] Ответ на команду /start отправлен")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("[INFO] Получена команда /stats")
    if not context.args:
        print("[WARNING] Имя артиста не указано")
        await update.message.reply_text("Пожалуйста, укажи имя артиста после команды. Например: /stats Drake")
        print("[SUCCESS] Ответ на ошибку отправлен")
        return
    
    artist_name = " ".join(context.args)
    print(f"[INFO] Имя артиста из запроса: '{artist_name}'")
    await update.message.reply_text(f"Обрабатываю запрос для '{artist_name}', подождите...")
    print("[INFO] Сообщение о начале обработки отправлено")

    try:
        print("[INFO] Проверяю статус авторизации...")
        if "authorized" not in context.bot_data or not is_logged_in():
            print("[INFO] Авторизация требуется, выполняю авторизацию...")
            authorize()
            print("[INFO] Перехожу на страницу статистики...")
            go_to_stats()
            context.bot_data["authorized"] = True
            print("[SUCCESS] Авторизация выполнена, статус сохранён")
        else:
            print("[INFO] Уже авторизован, перехожу на страницу статистики...")
            go_to_stats()

        print("[INFO] Запрашиваю статистику для артиста...")
        stats = get_artist_stats(artist_name)
        print(f"[INFO] Результат парсинга: {stats}")
        await update.message.reply_text(stats)
        print("[SUCCESS] Статистика успешно отправлена в Telegram")
    
    except Exception as e:
        print(f"[ERROR] Произошла ошибка: {str(e)}")
        await update.message.reply_text(f"Ошибка: {str(e)}")
        print("[INFO] Сообщение об ошибке отправлено в Telegram")

def main():
    token = "7624800237:AAEZHPHTZc1btzeM8_ubSQhCEXUDi2Jy6Xs"
    print(f"[INFO] Инициализация бота с токеном: {token}")
    application = Application.builder().token(token).build()

    print("[INFO] Добавляю обработчики команд...")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))

    print("[SUCCESS] Бот запущен")
    application.run_polling()
    print("[INFO] Бот остановлен")
    driver.quit()
    print("[INFO] Драйвер Chrome закрыт")

if __name__ == "__main__":
    main()