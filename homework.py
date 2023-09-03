import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv
from telegram import TelegramError

from exceptions import RequiredEnvVariables, StatusCodeError, VerdictError, \
    HomeWorkNameError, HomeWorksNameError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TEXT_ERROR = 'Отсутствуют обязательные переменные окружения'

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

verdict = ''

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
logger.addHandler(handler)

# Создаём форматер
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
# Применяем его к хэндлеру
handler.setFormatter(formatter)


def check_tokens():
    if not all(
        [
            PRACTICUM_TOKEN,
            TELEGRAM_TOKEN,
            TELEGRAM_CHAT_ID,
        ]
    ):
        logger.critical(TEXT_ERROR)
        raise RequiredEnvVariables(TEXT_ERROR)
    else:
        logger.debug('Обнаружены обязательные переменные окружения')


def send_message(bot, message):
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.debug(f'Отправлено сообщение: {message}')
    except TelegramError as e:
        logger.error(f'Ошибка при отправке сообщения: {e}')


def get_api_answer(timestamp):
    payload = {'from_date': timestamp}
    text_error = f'Ошибка при запросе к эндпоинту: {ENDPOINT}'
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload,
        )
    except requests.RequestException:
        logger.error(text_error)
    # raise requests.RequestException(text_error)
    else:
        if response.status_code != 200:
            logger.error(text_error)
            raise StatusCodeError(text_error)
        else:
            logger.info('Ответ API от Яндекс.Домашка получен.')
            data = response.json()
            logger.info(data)
            return data


def check_response(response):
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


def parse_status(homework):
    try:
        homework_name = homework['homework_name']
    except KeyError:
        text_error = 'Отсутствует ключ "homework_name".'
        logger.error(text_error)
        raise KeyError(text_error)
    global verdict
    if (status := homework.get('status')) == verdict:
        logger.debug('Статус проверки работы не изменился.')
    else:
        verdict = status
        if verdict in HOMEWORK_VERDICTS:
            text_info = (f'Изменился статус проверки работы '
                         f'"{homework_name}". {HOMEWORK_VERDICTS[verdict]}')
            logger.info(text_info)
            return text_info
        else:
            text_error = f'Неизвестный статус работы: {verdict}'
            logger.error(text_error)
            raise VerdictError(text_error)


def main():
    """Основная логика работы бота."""

    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(
                timestamp - 3 * 7 * 24 * 60 * 60
            )
            check_response(response)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        else:
            print()
            print('*'*50)
            print(response)
            print('*'*50)
            message = parse_status(response['homeworks'][0])
        if message:
            send_message(bot, message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
