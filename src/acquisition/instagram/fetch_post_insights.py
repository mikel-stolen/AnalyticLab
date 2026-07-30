import json
import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

GRAPH_API_VERSION = "v23.0"
GRAPH_API_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

def save_raw_insights(data: dict, post_id: str) -> Path:
    """
    Guarda la respuesta original de insights en
    data/raw/instagram/insights/
    """

    project_root = Path(__file__).resolve().parents[3]

    output_dir = (
        project_root
        / "data"
        / "raw"
        / "instagram"
        / "insights"
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"insights_{post_id}_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    print(f"JSON guardado en: {output_file}")

    return output_file


def fetch_post_insights(access_token: str, post_id: str) -> dict:
    """
    Obtiene las métricas disponibles para una publicación.

    Si Meta no permite obtener insights porque la publicación es
    anterior a la conversión de la cuenta a profesional/empresarial,
    devuelve un estado 'unavailable' en lugar de tratarlo como error.
    """

    url = f"{GRAPH_API_URL}/{post_id}/insights"

    params = {
        "metric": ",".join([
            "likes",
            "comments",
            "shares",
            "saved",
            "reach",
            "total_interactions",
            "views"
        ]),
        "access_token": access_token,
    }

    response = requests.get(url, params=params, timeout=30)

    if not response.ok:
        data = response.json()
        error = data.get("error", {})

        if error.get("error_subcode") == 2108006:
            unavailable_data = {
                "post_id": post_id,
                "status": "unavailable",
                "reason": "published_before_professional_account_conversion"
            }

            save_raw_insights(unavailable_data, post_id)

            return unavailable_data

        print(f"\nError obteniendo insights para {post_id}:")
        print(response.text)
        response.raise_for_status()

    data = response.json()

    save_raw_insights(data, post_id)

    return data

if __name__ == "__main__":

    load_dotenv()

    ACCESS_TOKEN = os.getenv("IG_TOKEN")
    IG_USER_ID = os.getenv("IG_ACCOUNT_ID")

    if not ACCESS_TOKEN:
        raise ValueError("No se encontró IG_TOKEN en el archivo .env")

    if not IG_USER_ID:
        raise ValueError("No se encontró IG_ACCOUNT_ID en el archivo .env")

    from fetch_posts import fetch_posts

    posts = fetch_posts(
        access_token=ACCESS_TOKEN,
        ig_user_id=IG_USER_ID
    )

    print(f"\nPublicaciones encontradas: {len(posts)}")
    print("Iniciando recopilación de insights...\n")

    successful = 0
    unavailable = 0
    failed = 0

    for index, post in enumerate(posts, start=1):

        post_id = post.get("id")

        print(f"[{index}/{len(posts)}] Procesando {post_id}...")

        try:
            result = fetch_post_insights(
                access_token=ACCESS_TOKEN,
                post_id=post_id
            )

            if result.get("status") == "unavailable":
                unavailable += 1
                print("  ⚠ Insights no disponibles: publicación anterior a la conversión de la cuenta.")
            else:
                successful += 1
                print("  ✓ Insights guardados.")

        except requests.HTTPError:
            failed += 1
            print("  ✗ Error obteniendo insights.")

    print("\n" + "=" * 60)
    print("Recopilación finalizada")
    print("=" * 60)
    print(f"Correctos:      {successful}")
    print(f"No disponibles: {unavailable}")
    print(f"Errores:        {failed}")