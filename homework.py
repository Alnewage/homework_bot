import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv
from telegram import TelegramError

from exceptions import RequiredEnvVariables, StatusCodeError, VerdictError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Интервал повторного запроса к API в секундах.
RETRY_PERIOD = 600
# Интервал времени в секундах от текущего момента назад,
# за которое получаем данные от API.
PAST_TIMESTAMP = 3 * 7 * 24 * 60 * 60  # 3 недели
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)


def check_tokens():
    """Проверяет наличие обязательных переменных окружения."""
    if not all(
        [
            PRACTICUM_TOKEN,
            TELEGRAM_TOKEN,
            TELEGRAM_CHAT_ID,
        ]
    ):
        text_error = 'Отсутствуют обязательные переменные окружения'
        logger.critical(text_error)
        raise RequiredEnvVariables(text_error)
    logger.debug('Обязательные переменные окружения обнаружены')


def send_message(bot, message):
    """Отправляет сообщение с использованием Telegram бота."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.debug(f'Отправлено сообщение: {message}')
    except TelegramError as e:
        logger.error(f'Ошибка при отправке сообщения: {e}')


def get_api_answer(timestamp):
    """Получает ответ от API на основе предоставленной метки времени."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload,
        )
        assert response.status_code == 200
    except (requests.RequestException, AssertionError,):
        text_error = f'Ошибка при запросе к эндпоинту: {ENDPOINT}'
        logger.error(text_error)
        raise StatusCodeError(text_error)
    logger.info('Ответ API от Яндекс.Домашка получен.')
    data = response.json()
    logger.info(data)
    return data


def check_response(response):
    """Проверяет ответ API на корректность."""
    try:
        if not isinstance(response, dict):
            raise TypeError
        if 'homeworks' not in response:
            raise KeyError
        if not isinstance(response['homeworks'], list):
            raise TypeError
        if 'status' not in response['homeworks'][0]:
            raise KeyError
        if 'homework_name' not in response['homeworks'][0]:
            raise KeyError
    except TypeError:
        text_error = 'Неверная структура ответа'
        logger.error(text_error)
        raise TypeError(text_error)
    except KeyError as e:
        text_error = f'Отсутствует ключ. {e}'
        logger.error(text_error)
        raise KeyError(text_error)

    logger.info('Проверка ответа API прошла успешно.')
    return response['homeworks']


def parse_status(homework):
    """Извлекает статус проверки работы и формирует сообщение."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        text_error = 'Отсутствует ключ "homework_name".'
        logger.error(text_error)
        raise KeyError(text_error)
    verdict = homework['status']
    if verdict not in HOMEWORK_VERDICTS:
        text_error = f'Неизвестный статус работы: {verdict}'
        logger.error(text_error)
        raise VerdictError(text_error)

    text_info = (f'Изменился статус проверки работы '
                 f'"{homework_name}". {HOMEWORK_VERDICTS[verdict]}')
    logger.info(text_info)
    return text_info


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    previous_message = ''

    while True:
        try:
            response = get_api_answer(timestamp - PAST_TIMESTAMP)
            homework = check_response(response)[0]
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        else:
            message = parse_status(homework)
        if message and message != previous_message:
            send_message(bot, message)
            previous_message = message
        else:
            logger.debug('Статус состояния не изменился.')

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
