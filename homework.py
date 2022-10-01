import logging
import os
import sys
import time
import requests
import telegram
from telegram.ext import CommandHandler, Updater
from dotenv import load_dotenv
from exceptions import (DictIsEmptyError, SendMessageError,
                        EndPointError)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRAKTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)


def send_message(bot, message):
    """Отправляет сообщение в telegram."""
    try:
        logger.debug('Начали отправку сообщения')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение {message}')
    except telegram.TelegramError as error:
        raise SendMessageError(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(current_timestamp):
    """Получение API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != requests.codes.ok:
            raise Exception(f'{ENDPOINT} недоступен'
                            f'код ответа API: {response.status_code}')
        return response.json()
    except requests.exceptions.RequestException:
        raise EndPointError(f'Проблема при обращении к {ENDPOINT}')


def check_response(response):
    """Проверка ответа от API."""
    if not isinstance(response, dict):
        raise TypeError(f'Неверный тип данных.'
                        f'Ожидается dict, получен {type(response)}')
    elif 'homeworks' not in response:
        raise KeyError('Ключа homeworks нет в ответе API')
    elif not isinstance(response['homeworks'], list):
        raise TypeError('homeworks не является списком')
    elif len(response) < 1:
        raise DictIsEmptyError('Словарь ответа API пуст')
    return response['homeworks']


def parse_status(homework):
    """Получение статуса домашней работы."""
    homework_name = homework.get('homework_name')
    try:
        homework_status = homework.get('status')
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError:
        raise KeyError('Неверный статус работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности токенов."""
    return (all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Программа была остановлена из-за отсутствие токена')
        sys.exit('Отсутствует один или несколько токенов')
    updater = Updater(token=TELEGRAM_TOKEN)
    updater.dispatcher.add_handler(CommandHandler('start', check_tokens()))
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_response = None
    error_message = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            current_timestamp = response.get('current_date')
            if homework:
                status_homework = parse_status(homework)
                if status_homework not in last_response:
                    last_response = status_homework
                    send_message(bot, last_response)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if error_message != message:
                send_message(bot, message)
            error_message = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
