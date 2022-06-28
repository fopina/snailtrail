import requests


class Notifier:
    def __init__(self, token):
        self.__token = token

    def notify(self, message, format='Markdown'):
        if self.__token:
            return requests.post(
                f'https://tgbots.skmobi.com/pushit/{self.__token}',
                json={'msg': message, 'format': format},
            )
