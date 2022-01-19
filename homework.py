import os
import time
import logging
import telegram
import requests
from telegram.ext import Updater
from logging import StreamHandler
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 60
PRACT_ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
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
    """Отправка сообщения."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.info('Сообщение отправлено')
    except Exception:
        logger.error('Сообщение не отправлено')


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(PRACT_ENDPOINT, headers=HEADERS, params=params)
        logger.info('Запрос на сервер отправлен')
    except Exception:
        logger.error('Запрос на сервер не отправлен')
    if response.status_code != 200:
        raise logger.error('Не удалось получить ответ API'
                           f'error-status: {response.status_code}')
    try:
        return response.json()
    except Exception:
        raise logger.error('Ответ от сервера не в json формате')


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Ошибка в типе ответа API')
    if 'homeworks' not in response:
        raise KeyError('В ответе API нет ключа homeworks')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Homeworks не является списком')
    if homeworks[0] is None:
        raise IndexError('В homeworks нет домашних работ')
    return homeworks[0]


def parse_status(homework):
    """Извлекается информацию о нужной домашней работе."""
    if 'homework_name' not in homework:
        raise KeyError('В ответе API отсутсвует ключ homework_name')
    if 'status' not in homework:
        raise KeyError('В ответе API отсутсвует ключ status')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise Exception(f'Неизвестный статус работы - {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    updater = Updater(TELEGRAM_TOKEN)
    start_timestamp = 1640995200
    current_timestamp = start_timestamp
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
                if STATUS != '':
                    current_timestamp = int(time.time())
                STATUS = new_status
            else:
                logger.debug('Статус не поменялся')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)

        time.sleep(RETRY_TIME)
        updater.start_polling()


if __name__ == '__main__':
    main()
