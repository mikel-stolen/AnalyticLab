import json
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

POSTS_DIR = PROJECT_ROOT / "data" / "raw" / "instagram" / "posts"
INSIGHTS_DIR = PROJECT_ROOT / "data" / "raw" / "instagram" / "insights"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "instagram"


def load_latest_posts() -> list:
    """
    Carga el archivo de posts más reciente y devuelve todas las publicaciones.
    """

    files = sorted(
        POSTS_DIR.glob("posts_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not files:
        raise FileNotFoundError(
            f"No se encontraron archivos de publicaciones en {POSTS_DIR}"
        )

    latest_file = files[0]

    with open(latest_file, "r", encoding="utf-8") as file:
        raw_data = json.load(file)

    posts = []

    # fetch_posts.py guarda las páginas como una lista.
    if isinstance(raw_data, list):
        for page in raw_data:
            posts.extend(page.get("data", []))

    # Compatibilidad por si en el futuro se guarda una respuesta única.
    elif isinstance(raw_data, dict):
        posts.extend(raw_data.get("data", []))

    return posts


def load_latest_insights() -> dict:
    """
    Carga el archivo de insights más reciente de cada publicación.
    """

    insight_files = list(INSIGHTS_DIR.glob("insights_*.json"))

    if not insight_files:
        raise FileNotFoundError(
            f"No se encontraron archivos de insights en {INSIGHTS_DIR}"
        )

    latest_by_post = {}

    for file_path in insight_files:
        filename = file_path.stem

        # Formato:
        # insights_<post_id>_<timestamp>
        parts = filename.split("_")

        if len(parts) < 3:
            continue

        post_id = parts[1]

        current_timestamp = file_path.stat().st_mtime

        if (
            post_id not in latest_by_post
            or current_timestamp > latest_by_post[post_id]["mtime"]
        ):
            latest_by_post[post_id] = {
                "path": file_path,
                "mtime": current_timestamp,
            }

    insights = {}

    for post_id, metadata in latest_by_post.items():
        with open(metadata["path"], "r", encoding="utf-8") as file:
            insights[post_id] = json.load(file)

    return insights


def extract_metric(insights_data: dict, metric_name: str):
    """
    Extrae el valor de una métrica desde la respuesta de Meta.
    """

    for metric in insights_data.get("../../acquisition/instagram/data", []):
        if metric.get("name") != metric_name:
            continue

        values = metric.get("values", [])

        if values:
            return values[0].get("value")

        value = metric.get("value")

        if value is not None:
            return value

    return None


def normalize_posts(posts: list, insights: dict) -> list:
    """
    Combina publicaciones e insights en registros normalizados.
    """

    normalized = []

    for post in posts:

        post_id = post.get("id")
        post_insights = insights.get(post_id)

        record = {
            "post_id": post_id,
            "timestamp": post.get("timestamp"),
            "media_type": post.get("media_type"),
            "media_product_type": post.get("media_product_type"),
            "permalink": post.get("permalink"),
            "caption": post.get("caption"),
            "username": post.get("username"),
            "insights_status": "unavailable",
            "likes": None,
            "comments": None,
            "shares": None,
            "saved": None,
            "reach": None,
            "total_interactions": None,
            "views": None,
        }

        if post_insights:
            if post_insights.get("status") == "unavailable":
                record["insights_status"] = "unavailable"

            elif "data" in post_insights:
                record["insights_status"] = "available"

                record["likes"] = extract_metric(
                    post_insights, "likes"
                )
                record["comments"] = extract_metric(
                    post_insights, "comments"
                )
                record["shares"] = extract_metric(
                    post_insights, "shares"
                )
                record["saved"] = extract_metric(
                    post_insights, "saved"
                )
                record["reach"] = extract_metric(
                    post_insights, "reach"
                )
                record["total_interactions"] = extract_metric(
                    post_insights, "total_interactions"
                )
                record["views"] = extract_metric(
                    post_insights, "views"
                )

        normalized.append(record)

    return normalized


def save_normalized_data(data: list) -> Path:
    """
    Guarda el dataset normalizado.
    """

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_file = OUTPUT_DIR / f"posts_normalized_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    return output_file


if __name__ == "__main__":

    print("\nCargando publicaciones...")

    posts = load_latest_posts()

    print(f"Publicaciones cargadas: {len(posts)}")

    print("\nCargando insights...")

    insights = load_latest_insights()

    print(f"Archivos de insights encontrados: {len(insights)}")

    print("\nNormalizando datos...")

    normalized_data = normalize_posts(
        posts=posts,
        insights=insights,
    )

    output_file = save_normalized_data(normalized_data)

    available = sum(
        1
        for item in normalized_data
        if item["insights_status"] == "available"
    )

    unavailable = sum(
        1
        for item in normalized_data
        if item["insights_status"] == "unavailable"
    )

    print("\n" + "=" * 60)
    print("Procesamiento finalizado")
    print("=" * 60)
    print(f"Publicaciones:       {len(normalized_data)}")
    print(f"Insights disponibles: {available}")
    print(f"No disponibles:       {unavailable}")
    print(f"\nDataset generado:")
    print(output_file)