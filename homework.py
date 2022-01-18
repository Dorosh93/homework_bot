import os
import time
import logging
import telegram
import requests
from telegram.ext import CommandHandler, Updater
from logging import StreamHandler
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler()
logger.addHandler(handler)

formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)

handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправка сообщения"""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.info = ('Сообщение отправлено')
    except Exception:
            logger.error('Сообщение не отправлено')


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        raise logger.error('Не удалось получить ответ API'
                           f'error-status: {response.status_code}')
    return response.json()


def check_response(response):
    """Проверка ответа API на корректность"""
    if type(response) is not dict:
        raise TypeError('Ошибка в типе ответа API')
    if 'homeworks' not in response:
        raise KeyError('В ответе API нет ключа homeworks')
    homeworks = response['homeworks']
    if type(homeworks) is not list:
        raise TypeError('Homeworks не является списком')
    return homeworks[0]


def parse_status(homework):
    """Извлекается информацию о нужной домашней работы
       и готовит строку для отправки"""
    if 'homework_name' not in homework:
        raise KeyError('В ответе API отсутсвует ключ homework_name')
    if 'status' not in homework:
        raise KeyError('В ответе API отсутсвует ключ status')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise Exception('Неизвестный статус работы')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов"""
    if (TELEGRAM_TOKEN is None or PRACTICUM_TOKEN is None):
        return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    updater = Updater(TELEGRAM_TOKEN)
    current_timestamp = 1635795445
    STATUS = ''
    if not check_tokens():
        logger.critical = ('Отсутсвуют переменные окружения')
        raise Exception('Отсутсвуют переменные окружения')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            new_status = parse_status(check_response(response))
            if new_status != STATUS:
                send_message(bot, new_status)
                STATUS = new_status
                current_timestamp = int(time.time())
                time.sleep(RETRY_TIME)
            logger.debug('Статус не поменялся')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)

        updater.dispatcher.add_handler(
            CommandHandler('start', send_message))
        updater.dispatcher.add_handler(
            CommandHandler('status_hw', parse_status))
        updater.start_polling()
 

if __name__ == '__main__':
    main()