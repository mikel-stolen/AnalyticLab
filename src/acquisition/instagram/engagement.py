import json
from pathlib import Path

from load_dataset import load_latest_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ANALYTICS_DIR = PROJECT_ROOT / "data" / "processed" / "instagram" / "analytics"


def calculate_engagement_rate(post: dict) -> float | None:
    """
    Calcula el engagement rate respecto al alcance.

    Fórmula:
        (interacciones totales / alcance) * 100
    """

    reach = post.get("reach")
    total_interactions = post.get("total_interactions")

    if reach is None or total_interactions is None:
        return None

    if reach <= 0:
        return None

    return round((total_interactions / reach) * 100, 2)


def analyze_engagement(dataset: list) -> list:
    """
    Añade métricas de engagement a cada publicación.
    """

    analyzed_data = []

    for post in dataset:

        record = post.copy()

        engagement_rate = calculate_engagement_rate(post)

        record["engagement_rate"] = engagement_rate

        analyzed_data.append(record)

    return analyzed_data


def calculate_summary(dataset: list) -> dict:
    """
    Calcula un resumen general del engagement.
    """

    available_rates = [
        post["engagement_rate"]
        for post in dataset
        if post.get("engagement_rate") is not None
    ]

    if not available_rates:
        return {
            "posts_analyzed": 0,
            "average_engagement_rate": None,
            "max_engagement_rate": None,
            "min_engagement_rate": None,
        }

    return {
        "posts_analyzed": len(available_rates),
        "average_engagement_rate": round(
            sum(available_rates) / len(available_rates),
            2,
        ),
        "max_engagement_rate": max(available_rates),
        "min_engagement_rate": min(available_rates),
    }


def save_analysis(data: list, summary: dict) -> Path:
    """
    Guarda los resultados del análisis.
    """

    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

    output_file = ANALYTICS_DIR / "engagement_analysis.json"

    output = {
        "summary": summary,
        "posts": data,
    }

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False,
        )

    return output_file


if __name__ == "__main__":

    print("\nCargando dataset...")

    dataset = load_latest_dataset()

    print("\nCalculando engagement...")

    analyzed_data = analyze_engagement(dataset)

    summary = calculate_summary(analyzed_data)

    output_file = save_analysis(
        analyzed_data,
        summary,
    )

    print("\n" + "=" * 60)
    print("ANÁLISIS DE ENGAGEMENT")
    print("=" * 60)

    print(f"Publicaciones analizadas: {summary['posts_analyzed']}")
    print(
        f"Engagement medio: "
        f"{summary['average_engagement_rate']}%"
    )
    print(
        f"Engagement máximo: "
        f"{summary['max_engagement_rate']}%"
    )
    print(
        f"Engagement mínimo: "
        f"{summary['min_engagement_rate']}%"
    )

    print("\nTop 5 publicaciones:")

    ranked_posts = sorted(
        [
            post
            for post in analyzed_data
            if post.get("engagement_rate") is not None
        ],
        key=lambda post: post["engagement_rate"],
        reverse=True,
    )

    for index, post in enumerate(ranked_posts[:5], start=1):
        print(
            f"{index}. "
            f"{post['post_id']} | "
            f"{post['media_product_type']} | "
            f"{post['engagement_rate']}%"
        )

    print(f"\nAnálisis guardado en:")
    print(output_file)