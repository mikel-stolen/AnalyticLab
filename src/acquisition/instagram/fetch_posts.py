import os

import requests
from dotenv import load_dotenv
import json
from pathlib import Path
from datetime import datetime
GRAPH_API_VERSION = "v23.0"
GRAPH_API_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def fetch_posts(access_token: str, ig_user_id: str) -> list:
    """
    Obtiene todas las publicaciones de una cuenta de Instagram
    recorriendo automáticamente todas las páginas de la Graph API.
    """

    url = f"{GRAPH_API_URL}/{ig_user_id}/media"

    params = {
        "fields": (
            "id,"
            "caption,"
            "media_type,"
            "media_product_type,"
            "timestamp,"
            "permalink,"
            "media_url,"
            "thumbnail_url,"
            "username"
        ),
        "access_token": access_token,
    }

    all_posts = []
    raw_responses = []

    while url:

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        raw_responses.append(data)

        all_posts.extend(data.get("data", []))

        paging = data.get("paging", {})
        url = paging.get("next")

        # El access_token ya va incluido en la URL "next"
        params = None

    save_raw_json(raw_responses)

    return all_posts

def save_raw_json(data: list) -> Path:
    output_dir = Path("C:/AnalyticLab/data/raw/instagram/posts")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"posts_{timestamp}.json"

    print(f"Guardando JSON en: {output_file}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print("JSON guardado correctamente.")

    return output_file

if __name__ == "__main__":

    load_dotenv()

    ACCESS_TOKEN = os.getenv("IG_TOKEN")
    IG_USER_ID = os.getenv("IG_ACCOUNT_ID")

    if not ACCESS_TOKEN:
        raise ValueError("No se encontró la variable IG_TOKEN en el archivo .env")

    if not IG_USER_ID:
        raise ValueError("No se encontró la variable IG_ACCOUNT_ID en el archivo .env")

    posts = fetch_posts(ACCESS_TOKEN, IG_USER_ID)

    print(f"\nPublicaciones encontradas: {len(posts)}\n")
