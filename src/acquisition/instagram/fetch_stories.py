"""
Obtiene las Stories activas/disponibles de la cuenta de Instagram
y guarda las respuestas originales de la API en formato JSON.
"""

import json
from datetime import datetime
from pathlib import Path

from src.acquisition.instagram.config import IG_USER_ID, STORIES_DIR
from src.acquisition.instagram.instagram_client import InstagramClient


class StoriesFetcher:

    def __init__(self):
        self.client = InstagramClient()

    def fetch(self):
        """
        Obtiene las Stories disponibles para la cuenta.
        """

        return self.client.get(
            endpoint=f"{IG_USER_ID}/stories",
            params={
                "fields": (
                    "id,"
                    "media_type,"
                    "media_product_type,"
                    "timestamp,"
                    "media_url,"
                    "thumbnail_url,"
                    "permalink"
                )
            }
        )

    def save_raw_json(self, data: dict) -> Path:
        """
        Guarda la respuesta original de Stories.
        """

        STORIES_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        output_file = (
            STORIES_DIR
            / f"stories_{timestamp}.json"
        )

        with open(
            output_file,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False,
            )

        print(
            f"JSON de Stories guardado en: "
            f"{output_file}"
        )

        return output_file

    def run(self):

        data = self.fetch()

        self.save_raw_json(data)

        stories = data.get("data", [])

        print(
            f"Stories encontradas: {len(stories)}"
        )

        return stories


def main():

    fetcher = StoriesFetcher()

    fetcher.run()


if __name__ == "__main__":
    main()