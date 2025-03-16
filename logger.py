from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time
import logging
import os

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Путь к chromedriver
driver_path = "C:\\coding\\parsbot\\parsbot\\chromedriver.exe"
logger.info(f"Установка пути к chromedriver: {driver_path}")

# Данные для авторизации
login_url = "https://dmb.sundesiremedia.com/"
stats_url = "https://dmb.sundesiremedia.com/trend-stream/lastweek"
username = "coldfear"
password = "Weakky1703@"
output_file = "network_log.json"

def setup_driver():
    """Настраиваем драйвер с логированием сетевых запросов"""
    logger.info("Настройка драйвера с логированием сети...")
    service = Service(driver_path)
    
    # Настройки для захвата сетевых запросов
    chrome_options = webdriver.ChromeOptions()
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})  # Включаем логи производительности
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    logger.info("Драйвер Chrome успешно запущен")
    return driver

def authorize(driver):
    """Авторизация на сайте"""
    logger.info("Начинаю процесс авторизации...")
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

def collect_network_logs(driver):
    """Собираем сетевые запросы"""
    logger.info(f"Перехожу на страницу статистики: {stats_url}")
    driver.get(stats_url)
    
    logger.info("Ожидаю появления хотя бы одной строки таблицы...")
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#top-area tr.control-list-row"))
    )
    
    # Даём время на подгрузку данных
    logger.info("Жду 10 секунд для полной загрузки данных...")
    time.sleep(10)
    
    # Получаем логи производительности
    logs = driver.get_log("performance")
    network_requests = []
    
    for entry in logs:
        message = json.loads(entry["message"])["message"]
        if message["method"] in ["Network.requestWillBeSent", "Network.responseReceived"]:
            request_data = {
                "method": message["method"],
                "url": message.get("params", {}).get("request", {}).get("url", "N/A"),
                "headers": message.get("params", {}).get("request", {}).get("headers", {}),
                "response": message.get("params", {}).get("response", {})
            }
            network_requests.append(request_data)
    
    # Сохраняем в файл
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(network_requests, f, indent=2, ensure_ascii=False)
    logger.info(f"Сетевые запросы сохранены в {output_file}")

def main():
    try:
        driver = setup_driver()
        authorize(driver)
        collect_network_logs(driver)
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
    finally:
        driver.quit()
        logger.info("Драйвер закрыт")

if __name__ == "__main__":
    main()