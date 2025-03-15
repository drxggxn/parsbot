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
driver_path = "C:\\coding\\parsbot\\chromedriver.exe"
service = Service(driver_path)
driver = webdriver.Chrome(service=service)

# Данные для авторизации
login_url = "https://dmb.sundesiremedia.com/"
username = "coldfear"
password = "Weakky1703@"

def is_logged_in():
    """Проверяет, авторизован ли бот, по наличию элемента профиля."""
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "profile-username"))
        )
        print("Сессия активна")
        return True
    except:
        print("Сессия неактивна")
        return False

def authorize():
    """Авторизация на сайте."""
    print("Открываю страницу авторизации...")
    driver.get(login_url)
    
    # Ждем загрузки формы логина
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "login"))
    )
    
    print("Ищу поле логина...")
    login_field = driver.find_element(By.ID, "login")
    print("Ввожу логин...")
    login_field.send_keys(username)
    
    print("Ищу поле пароля...")
    password_field = driver.find_element(By.ID, "pass")
    print("Ввожу пароль...")
    password_field.send_keys(password)
    
    print("Ищу кнопку входа...")
    try:
        login_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@value='Login to DMB']"))
        )
        print("Найдена кнопка 'Login to DMB'")
    except:
        login_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit']"))
        )
        print("Найдена кнопка submit (запасной вариант)")
    
    print("Нажимаю кнопку входа...")
    login_button.click()
    
    print("Ожидаю появления дашборда...")
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "profile-username"))
        )
        print("Авторизация завершена успешно")
    except:
        print(f"Не удалось подтвердить вход. Текущий URL: {driver.current_url}")
        with open("login_page_after_submit.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        raise Exception("Ошибка авторизации — дашборд не загрузился")

def go_to_stats():
    """Переход на страницу статистики."""
    if not is_logged_in():
        raise Exception("Сессия истекла, требуется повторная авторизация")
    
    print("Ищу ссылку на статистику...")
    stats_link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[@href='/trend-stream/lastweek']"))
    )
    time.sleep(1)
    
    print("Перехожу на страницу статистики...")
    stats_link.click()
    
    print("Ожидаю загрузки таблицы...")
    # Ждем, пока в tbody появится хотя бы одна строка с артистом
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr.control-list-row td.field-sale_artist"))
    )
    # Дополнительная задержка для полной прогрузки
    time.sleep(3)
    # Прокручиваем страницу до конца
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    print("Страница статистики загружена")

def get_artist_stats(artist_name):
    """Получение статистики по артисту."""
    print(f"Парсинг статистики для '{artist_name}'...")
    
    # Убеждаемся, что таблица загрузилась
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr.control-list-row td.field-sale_artist"))
    )
    
    # Прокручиваем страницу до конца для подгрузки всех данных
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    tbody = soup.find("tbody")
    if not tbody:
        print("Таблица не найдена")
        return "Таблица не найдена"
    
    results = []
    for row in tbody.find_all("tr", class_="control-list-row"):
        artist_cell = row.find("td", class_="field-sale_artist")
        streams_cell = row.find("td", class_="field-sale_units")
        title_cell = row.find("td", class_="field-sale_title")
        
        if artist_cell and streams_cell and title_cell:
            # Извлекаем текст и убираем лишние пробелы и невидимые символы
            artist_text = unicodedata.normalize("NFKD", artist_cell.find("span", class_="column-value").text).strip()
            streams_text = streams_cell.find("span", class_="column-value").text.strip().replace(",", "")
            title_text = unicodedata.normalize("NFKD", title_cell.find("span", class_="column-value").text).strip()
            
            print(f"Найден артист: '{artist_text}' с треком '{title_text}' и {streams_text} стримами")
            # Сравниваем без учета регистра и невидимых символов
            if artist_name.lower() in artist_text.lower():
                results.append(f"{title_text} — {streams_text} стримов")
    
    if results:
        print(f"Найдено {len(results)} записей для '{artist_name}'")
    else:
        print(f"Артист '{artist_name}' не найден")
    return results if results else f"Артист '{artist_name}' не найден"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот для проверки статистики стримов на DMB.\n"
        "Используй команду /stats <имя_артиста>, чтобы получить статистику.\n"
        "Например: /stats Drake"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажи имя артиста после команды. Например: /stats Drake")
        return
    
    artist_name = " ".join(context.args)
    await update.message.reply_text(f"Обрабатываю запрос для '{artist_name}', подождите...")

    try:
        # Проверяем, авторизован ли бот
        if "authorized" not in context.bot_data or not is_logged_in():
            authorize()
            go_to_stats()
            context.bot_data["authorized"] = True
        else:
            # Если уже авторизован, просто переходим к статистике
            go_to_stats()

        stats = get_artist_stats(artist_name)
        if isinstance(stats, list):
            response = f"Статистика для '{artist_name}':\n" + "\n".join(stats)
        else:
            response = stats
        
        await update.message.reply_text(response)
    
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        await update.message.reply_text(f"Ошибка: {e}")

def main():
    token = "7624800237:AAEZHPHTZc1btzeM8_ubSQhCEXUDi2Jy6Xs"
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))

    print("Бот запущен")
    application.run_polling()
    print("Бот остановлен")
    driver.quit()

if __name__ == "__main__":
    main()