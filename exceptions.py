class SendMessageError(Exception):
    """Класс для обработки ошибки при отправлении сообщения."""

    pass


class DictIsEmptyError(Exception):
    """Ошибка при пустом словаре."""

    pass


class EndPointError(Exception):
    """Класс для обработки ошибок сервера."""

    pass
