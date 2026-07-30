"""
Obtiene la información general de la cuenta de Instagram
y la guarda en formato JSON.
"""

import json
from datetime import datetime
from pathlib import Path

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

    def save_raw_json(self, data: dict) -> Path:
        """
        Guarda la respuesta original de la cuenta
        en data/raw/instagram/account/.
        """

        ACCOUNT_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = ACCOUNT_DIR / f"account_{timestamp}.json"

        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

        print(f"JSON guardado en: {output_file}")

        return output_file

    def run(self):

        data = self.fetch()
        self.save_raw_json(data)


def main():

    fetcher = AccountFetcher()
    fetcher.run()


if __name__ == "__main__":
    main()