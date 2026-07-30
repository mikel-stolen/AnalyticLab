import json
from pathlib import Path
from statistics import mean, median

from load_dataset import load_latest_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[3]

ANALYTICS_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "instagram"
    / "analytics"
)


def classify_format(post: dict) -> str:
    """
    Normaliza el formato del contenido para el estudio.

    Categorías:
    - REELS
    - CAROUSEL
    - IMAGE
    - OTHER
    """

    if post.get("media_product_type") == "REELS":
        return "REELS"

    if post.get("media_type") == "CAROUSEL_ALBUM":
        return "CAROUSEL"

    if post.get("media_type") == "IMAGE":
        return "IMAGE"

    return "OTHER"


def get_interaction_rate(post: dict) -> float | None:
    """
    Calcula interacciones por alcance.

    Esta es una métrica descriptiva propia de AnalyticLab.
    No representa una métrica oficial de Instagram.
    """

    reach = post.get("reach")
    interactions = post.get("total_interactions")

    if reach is None or interactions is None:
        return None

    if reach <= 0:
        return None

    return (interactions / reach) * 100


def build_sequence_records(dataset: list) -> list:
    """
    Construye la ventana temporal alrededor de cada Reel:

        R-3 → R-2 → R-1 → REEL → R+1 → R+2 → R+3

    La secuencia utiliza todas las publicaciones para mantener
    el orden temporal correcto.

    Los cálculos de rendimiento solo se realizan cuando existen
    insights disponibles.
    """

    posts = sorted(
        dataset,
        key=lambda post: post.get("timestamp", "")
    )

    sequence_records = []

    for index, post in enumerate(posts):

        if classify_format(post) != "REELS":
            continue

        previous_3 = posts[index - 3] if index >= 3 else None
        previous_2 = posts[index - 2] if index >= 2 else None
        previous_1 = posts[index - 1] if index >= 1 else None

        next_1 = (
            posts[index + 1]
            if index + 1 < len(posts)
            else None
        )

        next_2 = (
            posts[index + 2]
            if index + 2 < len(posts)
            else None
        )

        next_3 = (
            posts[index + 3]
            if index + 3 < len(posts)
            else None
        )

        previous_posts = [
            previous_3,
            previous_2,
            previous_1,
        ]

        next_posts = [
            next_1,
            next_2,
            next_3,
        ]

        current_rate = get_interaction_rate(post)

        def build_context_record(item):
            if item is None:
                return None

            item_rate = get_interaction_rate(item)

            return {
                "post_id": item.get("post_id"),
                "timestamp": item.get("timestamp"),
                "format": classify_format(item),
                "reach": item.get("reach"),
                "views": item.get("views"),
                "likes": item.get("likes"),
                "comments": item.get("comments"),
                "saved": item.get("saved"),
                "shares": item.get("shares"),
                "total_interactions": item.get(
                    "total_interactions"
                ),
                "interaction_rate_by_reach": (
                    round(item_rate, 2)
                    if item_rate is not None
                    else None
                ),
                "insights_status": item.get(
                    "insights_status"
                ),
            }

        record = {
            "reel": build_context_record(post),

            "previous": {
                "r-3": build_context_record(previous_3),
                "r-2": build_context_record(previous_2),
                "r-1": build_context_record(previous_1),
            },

            "next": {
                "r+1": build_context_record(next_1),
                "r+2": build_context_record(next_2),
                "r+3": build_context_record(next_3),
            },

            "study_variables": {
                "previous_sequence": [
                    classify_format(item)
                    for item in previous_posts
                    if item is not None
                ],
                "next_sequence": [
                    classify_format(item)
                    for item in next_posts
                    if item is not None
                ],
                "reel_interaction_rate_by_reach": (
                    round(current_rate, 2)
                    if current_rate is not None
                    else None
                ),
            },
        }

        sequence_records.append(record)

    return sequence_records


def calculate_group_statistics(
    records: list,
    context_position: str,
) -> dict:
    """
    Agrupa los Reels según el formato existente en
    una posición concreta de la ventana temporal.

    Ejemplos:
    - R-1
    - R+1
    - R+2
    """

    groups = {}

    for record in records:

        context = record

        if context_position.startswith("R-"):
            item = record["previous"].get(
                context_position.lower()
            )
        else:
            item = record["next"].get(
                context_position.lower()
            )

        if item is None:
            group = "NONE"
        else:
            group = item.get("format", "OTHER")

        groups.setdefault(group, []).append(record)

    results = {}

    for group, items in groups.items():

        reaches = [
            item["reel"]["reach"]
            for item in items
            if item["reel"].get("reach") is not None
        ]

        interactions = [
            item["reel"]["total_interactions"]
            for item in items
            if item["reel"].get(
                "total_interactions"
            ) is not None
        ]

        rates = [
            item["reel"][
                "interaction_rate_by_reach"
            ]
            for item in items
            if item["reel"].get(
                "interaction_rate_by_reach"
            ) is not None
        ]

        results[group] = {
            "sample_size": len(items),

            "average_reach": (
                round(mean(reaches), 2)
                if reaches
                else None
            ),

            "median_reach": (
                round(median(reaches), 2)
                if reaches
                else None
            ),

            "average_interactions": (
                round(mean(interactions), 2)
                if interactions
                else None
            ),

            "average_interaction_rate_by_reach": (
                round(mean(rates), 2)
                if rates
                else None
            ),
        }

    return results


def calculate_sequence_statistics(
    records: list,
    positions: list[str],
) -> dict:
    """
    Analiza combinaciones de formatos previos.

    Ejemplo:
    R-3 → R-2 → R-1
    """

    groups = {}

    for record in records:

        sequence = []

        for position in positions:

            if position.startswith("R-"):
                item = record["previous"].get(
                    position.lower()
                )
            else:
                item = record["next"].get(
                    position.lower()
                )

            if item is None:
                sequence.append("NONE")
            else:
                sequence.append(
                    item.get("format", "OTHER")
                )

        sequence_name = " → ".join(sequence)

        groups.setdefault(
            sequence_name,
            []
        ).append(record)

    results = {}

    for sequence, items in groups.items():

        reaches = [
            item["reel"]["reach"]
            for item in items
            if item["reel"].get("reach") is not None
        ]

        rates = [
            item["reel"][
                "interaction_rate_by_reach"
            ]
            for item in items
            if item["reel"].get(
                "interaction_rate_by_reach"
            ) is not None
        ]

        results[sequence] = {
            "sample_size": len(items),

            "average_reach": (
                round(mean(reaches), 2)
                if reaches
                else None
            ),

            "median_reach": (
                round(median(reaches), 2)
                if reaches
                else None
            ),

            "average_interaction_rate_by_reach": (
                round(mean(rates), 2)
                if rates
                else None
            ),
        }

    return results


def save_analysis(
    records: list,
    r3_stats: dict,
    r2_stats: dict,
    r1_stats: dict,
    rplus1_stats: dict,
    rplus2_stats: dict,
    rplus3_stats: dict,
    previous_sequence_stats: dict,
) -> Path:
    """
    Guarda todos los resultados del estudio.
    """

    ANALYTICS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        ANALYTICS_DIR
        / "sequence_analysis.json"
    )

    output = {
        "study": {
            "name": (
                "Instagram Reel performance "
                "according to temporal context"
            ),
            "window": [
                "R-3",
                "R-2",
                "R-1",
                "R",
                "R+1",
                "R+2",
                "R+3",
            ],
            "format_categories": [
                "REELS",
                "CAROUSEL",
                "IMAGE",
                "OTHER",
            ],
            "methodology": (
                "Exploratory observational analysis "
                "of Reel performance according to "
                "preceding and following content."
            ),
            "causality_warning": (
                "Differences do not establish causality."
            ),
        },

        "context_statistics": {
            "R-3": r3_stats,
            "R-2": r2_stats,
            "R-1": r1_stats,
            "R+1": rplus1_stats,
            "R+2": rplus2_stats,
            "R+3": rplus3_stats,
        },

        "previous_sequence_statistics": (
            previous_sequence_stats
        ),

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

    print("\nConstruyendo ventanas temporales...")

    records = build_sequence_records(dataset)

    print(
        f"Reels analizados: {len(records)}"
    )

    print("\nAnalizando R-3...")

    r3_stats = calculate_group_statistics(
        records,
        "R-3",
    )

    print("\nAnalizando R-2...")

    r2_stats = calculate_group_statistics(
        records,
        "R-2",
    )

    print("\nAnalizando R-1...")

    r1_stats = calculate_group_statistics(
        records,
        "R-1",
    )

    print("\nAnalizando R+1...")

    rplus1_stats = calculate_group_statistics(
        records,
        "R+1",
    )

    print("\nAnalizando R+2...")

    rplus2_stats = calculate_group_statistics(
        records,
        "R+2",
    )

    print("\nAnalizando R+3...")

    rplus3_stats = calculate_group_statistics(
        records,
        "R+3",
    )

    print(
        "\nAnalizando secuencias anteriores..."
    )

    previous_sequence_stats = (
        calculate_sequence_statistics(
            records,
            ["R-3", "R-2", "R-1"],
        )
    )

    output_file = save_analysis(
        records=records,
        r3_stats=r3_stats,
        r2_stats=r2_stats,
        r1_stats=r1_stats,
        rplus1_stats=rplus1_stats,
        rplus2_stats=rplus2_stats,
        rplus3_stats=rplus3_stats,
        previous_sequence_stats=(
            previous_sequence_stats
        ),
    )

    print("\n" + "=" * 60)
    print("ESTUDIO TEMPORAL DE REELS")
    print("=" * 60)

    print("\nR-3:")
    for group, stats in r3_stats.items():
        print(
            f"  {group}: "
            f"n={stats['sample_size']} | "
            f"reach={stats['average_reach']} | "
            f"IR={stats['average_interaction_rate_by_reach']}%"
        )

    print("\nR-2:")
    for group, stats in r2_stats.items():
        print(
            f"  {group}: "
            f"n={stats['sample_size']} | "
            f"reach={stats['average_reach']} | "
            f"IR={stats['average_interaction_rate_by_reach']}%"
        )

    print("\nR-1:")
    for group, stats in r1_stats.items():
        print(
            f"  {group}: "
            f"n={stats['sample_size']} | "
            f"reach={stats['average_reach']} | "
            f"IR={stats['average_interaction_rate_by_reach']}%"
        )

    print("\nR+1:")
    for group, stats in rplus1_stats.items():
        print(
            f"  {group}: "
            f"n={stats['sample_size']} | "
            f"reach={stats['average_reach']} | "
            f"IR={stats['average_interaction_rate_by_reach']}%"
        )

    print("\nR+2:")
    for group, stats in rplus2_stats.items():
        print(
            f"  {group}: "
            f"n={stats['sample_size']} | "
            f"reach={stats['average_reach']} | "
            f"IR={stats['average_interaction_rate_by_reach']}%"
        )

    print("\nR+3:")
    for group, stats in rplus3_stats.items():
        print(
            f"  {group}: "
            f"n={stats['sample_size']} | "
            f"reach={stats['average_reach']} | "
            f"IR={stats['average_interaction_rate_by_reach']}%"
        )

    print(
        "\n" + "=" * 60
    )

    print(
        "\nAnálisis guardado en:"
    )
    print(output_file)