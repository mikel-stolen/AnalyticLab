"""
Obtiene la información general de la cuenta de Instagram
y la guarda en formato JSON.
"""

import json
from datetime import datetime

from src.acquisition.instagram.config import ACCOUNT_DIR, IG_USER_ID
from src.acquisition.instagram.instagram_client import InstagramClient


class AccountFetcher:

    def __init__(self):
        self.client = InstagramClient()

    def fetch(self):

        return self.client.get(
            endpoint=IG_USER_ID,
            params={
                "fields": "username,followers_count,follows_count,media_count"
            }
        )

    def save(self, data):

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        file_path = ACCOUNT_DIR / f"account_{timestamp}.json"

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        print(f"✅ Archivo guardado en:\n{file_path}")

    def run(self):

        data = self.fetch()

        self.save(data)


def main():

    fetcher = AccountFetcher()

    fetcher.run()


if __name__ == "__main__":
    main()