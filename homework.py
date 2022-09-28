import logging
import os
import time
import requests
import telegram
from telegram.ext import CommandHandler, Updater
from dotenv import load_dotenv

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
    level=logging.INFO)


def send_message(bot, message):
    """Отправляет сообщение в telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Бот отправил сообщение {message}')
    except telegram.TelegramError:
        logging.error('Бот не отправил сообщение')


def get_api_answer(current_timestamp):
    """Получение API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == requests.codes.ok:
        logging.info('Ответ от API получен')
        return response.json()
    else:
        logging.error(f'Сбой в работе, {ENDPOINT} недоступен'
                      f'код ответа API: {response.status_code}')
        raise Exception(f'{ENDPOINT} недоступен'
                        f'код ответа API: {response.status_code}')


def check_response(response):
    """Проверка ответа от API."""
    if len(response['homeworks']) == 0:
        logging.info('Домашних работ нет')
    elif ('homeworks' not in response) or ('current_date' not in response):
        logging.error('Ответ API пустой')
    elif not isinstance(response['homeworks'], list):
        logging.error('homeworks не список')
        raise TypeError('Домашки пришли не в виде списка')
    elif not isinstance(response, dict):
        logging.error('response не словарь')
    return response.get('homeworks')


def parse_status(homework):
    """Получение статуса домашней работы."""
    homework_name = homework.get('homework_name')
    try:
        homework_status = homework.get('status')
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError:
        logging.error('Неверный статус работы')
        raise KeyError('Неверный статус работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности токенов."""
    if (all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])):
        return True
    else:
        logging.critical('Переменные не доступны')
        return False


def main():
    """Основная логика работы бота."""
    updater = Updater(token=TELEGRAM_TOKEN)
    updater.dispatcher.add_handler(CommandHandler('start', check_tokens()))
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_response = None
    error_message = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            response = check_response(response)
            response = parse_status(response[0])
            current_timestamp = response.get('current_date')
            if last_response != response:
                send_message(bot, response)
                last_response = response
            else:
                logging.debug('Статус домашней работы не изменился')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if error_message != message:
                send_message(bot, message)
            error_message = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
