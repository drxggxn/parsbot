import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Данные для авторизации и API
login_url = "https://dmb.sundesiremedia.com/"
api_url = "https://dmb.sundesiremedia.com/watchdog.php"  # Проверим этот URL
username = "coldfear"
password = "Weakky1703@"

def get_session():
    """Создаём сессию с авторизацией"""
    logger.info("Создаю сессию и авторизуюсь...")
    session = requests.Session()
    response = session.post(login_url, data={"login": username, "pass": password})
    if response.status_code == 200:
        logger.info("Авторизация успешна")
        return session
    else:
        logger.error(f"Ошибка авторизации: {response.status_code} - {response.text}")
        raise Exception("Не удалось авторизоваться")

def get_all_tracks_stats():
    """Получаем данные через API"""
    logger.info("Запрашиваю статистику треков через API...")
    try:
        session = get_session()
        params = {
            "tab_id": "078392046",  # ID вкладки из вашего примера
            "width": "1298",        # Размеры окна (возможно, необязательно)
            "height": "1305"
        }
        response = session.get(api_url, params=params)
        
        if response.status_code != 200:
            logger.error(f"Ошибка API: {response.status_code} - {response.text}")
            return f"Ошибка API: {response.status_code}"
        
        # Логируем полный текст ответа
        logger.info(f"Ответ от API: {response.text}")
        
        try:
            # Пробуем разобрать как JSON
            data = response.json()
            results = []
            for track in data:
                title = track.get("title", "Unknown")
                artist = track.get("artist", "Unknown")
                streams = track.get("streams", 0)
                results.append(f"{title} — {artist} — {streams} стримов")
            
            if results:
                logger.info(f"Найдено {len(results)} треков")
                return "\n".join(results)
            else:
                logger.warning("Треки не найдены")
                return "Треки не найдены"
        except ValueError:
            # Если не JSON, возвращаем текст ответа для анализа
            logger.error("Ответ не в формате JSON")
            return f"Ошибка: данные не в JSON, содержимое: {response.text}"
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        return f"Ошибка: {str(e)}"

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

if __name__ == "__main__":
    main()  