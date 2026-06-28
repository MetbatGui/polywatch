import requests


class TelegramAdapter:
    def __init__(self, token: str, chat_id: str) -> None:
        self._url = f"https://api.telegram.org/bot{token}/sendMessage"
        self._chat_id = chat_id

    def send(self, message: str) -> None:
        resp = requests.post(
            self._url,
            json={"chat_id": self._chat_id, "text": message},
            timeout=10,
        )
        resp.raise_for_status()
