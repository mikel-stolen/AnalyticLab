import json
from pathlib import Path
from statistics import median
from datetime import datetime
from load_dataset import load_latest_dataset
from sequence_analysis import classify_format, get_interaction_rate


PROJECT_ROOT = Path(__file__).resolve().parents[3]

ANALYTICS_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "instagram"
    / "analytics"
)


def build_relative_records(dataset: list) -> list:
    """
    Calcula el rendimiento relativo de cada Reel respecto
    a una línea base construida únicamente con los 3 Reels
    anteriores disponibles.

    Métricas:
    - Relative Reach
    - Relative Interaction Rate

    La referencia utiliza únicamente publicaciones anteriores
    al Reel analizado.
    """

    posts = sorted(
        dataset,
        key=lambda post: post.get("timestamp", "")
    )

    reel_posts = [
        post
        for post in posts
        if classify_format(post) == "REELS"
        and post.get("insights_status") == "available"
    ]

    results = []

    for index, reel in enumerate(reel_posts):

        # Necesitamos al menos 3 Reels anteriores.
        if index < 3:
            continue

        previous_reels = reel_posts[index - 3:index]

        previous_reaches = [
            post.get("reach")
            for post in previous_reels
            if post.get("reach") is not None
            and post.get("reach") > 0
        ]

        previous_rates = [
            get_interaction_rate(post)
            for post in previous_reels
            if get_interaction_rate(post) is not None
        ]

        current_reach = reel.get("reach")
        current_rate = get_interaction_rate(reel)

        if not previous_reaches or current_reach is None:
            continue

        baseline_reach = median(previous_reaches)

        baseline_rate = (
            median(previous_rates)
            if previous_rates
            else None
        )

        relative_reach = (
            current_reach / baseline_reach
            if baseline_reach > 0
            else None
        )

        relative_rate = (
            current_rate / baseline_rate
            if (
                current_rate is not None
                and baseline_rate is not None
                and baseline_rate > 0
            )
            else None
        )

        previous_formats = [
            classify_format(post)
            for post in posts
            if post.get("timestamp", "")
            < reel.get("timestamp", "")
        ]

        previous_formats = previous_formats[-3:]

        record = {
            "reel": {
                "post_id": reel.get("post_id"),
                "timestamp": reel.get("timestamp"),
                "reach": current_reach,
                "interaction_rate_by_reach": (
                    round(current_rate, 4)
                    if current_rate is not None
                    else None
                ),
            },

            "baseline": {
                "previous_reels": [
                    {
                        "post_id": post.get("post_id"),
                        "timestamp": post.get("timestamp"),
                        "reach": post.get("reach"),
                        "interaction_rate_by_reach": (
                            round(
                                get_interaction_rate(post),
                                4
                            )
                            if get_interaction_rate(post)
                            is not None
                            else None
                        ),
                    }
                    for post in previous_reels
                ],
                "baseline_reach": baseline_reach,
                "baseline_interaction_rate_by_reach": (
                    round(baseline_rate, 4)
                    if baseline_rate is not None
                    else None
                ),
            },

            "sequence_context": {
                "previous_3_formats": previous_formats,
                "immediate_previous_format": (
                    previous_formats[-1]
                    if previous_formats
                    else None
                ),
            },

            "relative_performance": {
                "relative_reach": (
                    round(relative_reach, 4)
                    if relative_reach is not None
                    else None
                ),
                "relative_interaction_rate": (
                    round(relative_rate, 4)
                    if relative_rate is not None
                    else None
                ),
            },
        }

        results.append(record)

    return results


def summarize_by_context(records: list) -> dict:
    """
    Compara Relative Reach y Relative Interaction Rate
    según el formato de la publicación inmediatamente anterior.
    """

    groups = {}

    for record in records:

        context = record["sequence_context"].get(
            "immediate_previous_format"
        )

        if context is None:
            context = "NONE"

        groups.setdefault(context, []).append(record)

    summary = {}

    for context, items in groups.items():

        relative_reaches = [
            item["relative_performance"]["relative_reach"]
            for item in items
            if item["relative_performance"].get(
                "relative_reach"
            ) is not None
        ]

        relative_rates = [
            item["relative_performance"][
                "relative_interaction_rate"
            ]
            for item in items
            if item["relative_performance"].get(
                "relative_interaction_rate"
            ) is not None
        ]

        summary[context] = {
            "sample_size": len(items),

            "median_relative_reach": (
                round(median(relative_reaches), 4)
                if relative_reaches
                else None
            ),

            "median_relative_interaction_rate": (
                round(median(relative_rates), 4)
                if relative_rates
                else None
            ),

            "relative_reach_values": (
                relative_reaches
            ),

            "relative_interaction_rate_values": (
                relative_rates
            ),
        }

    return summary


def save_analysis(
    records: list,
    summary: dict,
) -> Path:
    """
    Guarda el estudio de rendimiento relativo como snapshot.
    """

    ANALYTICS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_file = (
        ANALYTICS_DIR
        / f"relative_performance_{timestamp}.json"
    )

    output = {
        "snapshot": {
            "timestamp": timestamp,
        },
        "study": {
            "name": "Relative Instagram Reel performance",
            "baseline_definition": (
                "Median performance of the three previous available Reels."
            ),
            "relative_reach_definition": (
                "Current Reel reach divided by baseline Reel reach."
            ),
            "relative_interaction_rate_definition": (
                "Current interaction rate divided by baseline interaction rate."
            ),
            "causality_warning": (
                "This is an observational analysis and does not establish causality."
            ),
        },
        "summary_by_previous_format": summary,
        "records": records,
    }

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as file:
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

    print(
        f"Registros disponibles: {len(dataset)}"
    )

    print(
        "\nConstruyendo rendimiento relativo..."
    )

    records = build_relative_records(dataset)

    print(
        f"Reels con baseline disponible: "
        f"{len(records)}"
    )

    summary = summarize_by_context(records)

    output_file = save_analysis(
        records=records,
        summary=summary,
    )

    print("\n" + "=" * 60)
    print("RENDIMIENTO RELATIVO DE REELS")
    print("=" * 60)

    for context, stats in summary.items():

        print(f"\nAnterior = {context}")

        print(
            f"  n = {stats['sample_size']}"
        )

        print(
            "  Mediana Relative Reach = "
            f"{stats['median_relative_reach']}"
        )

        print(
            "  Mediana Relative IR = "
            f"{stats['median_relative_interaction_rate']}"
        )

        print(
            "  Relative Reach individuales = "
            f"{stats['relative_reach_values']}"
        )

    print("\n" + "=" * 60)

    print(
        "\nAnálisis guardado en:"
    )

    print(output_file)