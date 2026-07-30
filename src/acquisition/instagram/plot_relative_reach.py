import json
from pathlib import Path
from statistics import median
from datetime import datetime
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[3]

ANALYTICS_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "instagram"
    / "analytics"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "instagram"
    / "analytics"
    / "plots"
)


def load_relative_performance() -> tuple[list, str]:
    """
    Carga el snapshot más reciente de Relative Performance.
    """

    files = sorted(
        ANALYTICS_DIR.glob(
            "relative_performance_*.json"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not files:
        raise FileNotFoundError(
            "No se encontraron snapshots de "
            "relative_performance."
        )

    latest_file = files[0]

    with open(
        latest_file,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    records = data.get("records", [])

    return records, latest_file.name

def prepare_data(records: list) -> list:
    """
    Prepara y ordena las observaciones cronológicamente.
    """

    prepared = []

    for record in records:

        relative_reach = record.get(
            "relative_performance",
            {}
        ).get("relative_reach")

        context = record.get(
            "sequence_context",
            {}
        ).get("immediate_previous_format")

        timestamp = record.get(
            "reel",
            {}
        ).get("timestamp")

        post_id = record.get(
            "reel",
            {}
        ).get("post_id")

        if relative_reach is None:
            continue

        if context not in {"CAROUSEL", "REELS"}:
            continue

        prepared.append({
            "timestamp": timestamp,
            "post_id": post_id,
            "context": context,
            "relative_reach": relative_reach,
        })

    prepared.sort(
        key=lambda item: item["timestamp"]
    )

    return prepared


def calculate_evolution(records: list) -> tuple:
    """
    Calcula la evolución acumulada de la mediana
    de Relative Reach para cada grupo.
    """

    carousel_values = []
    reels_values = []

    carousel_medians = []
    reels_medians = []
    observation_numbers = []

    for index, record in enumerate(records, start=1):

        if record["context"] == "CAROUSEL":
            carousel_values.append(
                record["relative_reach"]
            )

        elif record["context"] == "REELS":
            reels_values.append(
                record["relative_reach"]
            )

        carousel_medians.append(
            median(carousel_values)
            if carousel_values
            else None
        )

        reels_medians.append(
            median(reels_values)
            if reels_values
            else None
        )

        observation_numbers.append(index)

    return (
        observation_numbers,
        carousel_medians,
        reels_medians,
    )


def create_plot(
    records: list,
    observation_numbers: list,
    carousel_medians: list,
    reels_medians: list,
    snapshot_name: str,
):

    """Genera el gráfico del experimento.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.figure(figsize=(11, 6))

    # Observaciones individuales
    carousel_x = []
    carousel_y = []

    reels_x = []
    reels_y = []

    for index, record in enumerate(
        records,
        start=1,
    ):

        if record["context"] == "CAROUSEL":
            carousel_x.append(index)
            carousel_y.append(
                record["relative_reach"]
            )

        elif record["context"] == "REELS":
            reels_x.append(index)
            reels_y.append(
                record["relative_reach"]
            )

    plt.scatter(
        carousel_x,
        carousel_y,
        label="CAROUSEL → REEL",
    )

    plt.scatter(
        reels_x,
        reels_y,
        label="REEL → REEL",
    )

    # Evolución de medianas
    valid_carousel = [
        value
        for value in carousel_medians
        if value is not None
    ]

    valid_reels = [
        value
        for value in reels_medians
        if value is not None
    ]

    carousel_x_median = [
        observation_numbers[index]
        for index, value in enumerate(
            carousel_medians
        )
        if value is not None
    ]

    reels_x_median = [
        observation_numbers[index]
        for index, value in enumerate(
            reels_medians
        )
        if value is not None
    ]

    plt.plot(
        carousel_x_median,
        valid_carousel,
        label="Mediana acumulada CAROUSEL → REEL",
    )

    plt.plot(
        reels_x_median,
        valid_reels,
        label="Mediana acumulada REEL → REEL",
    )

    # Baseline
    plt.axhline(
        y=1,
        linestyle="--",
        label="Baseline = 1",
    )

    plt.xlabel("Observación de Reel")
    plt.ylabel("Relative Reach")
    plt.title(
        "Evolución del Relative Reach según contexto previo\n"
        f"Snapshot: {snapshot_name}"
    )

    plt.grid(
        True,
        alpha=0.3,
    )

    plt.legend()

    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_file = (
            OUTPUT_DIR
            / f"relative_reach_evolution_{timestamp}.png"
    )

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight",
    )

    plt.show()

    print(
        f"\nGráfico guardado en:\n{output_file}"
    )


if __name__ == "__main__":

    print("\nCargando análisis relativo...")

    records, snapshot_name = load_relative_performance()

    print(
        f"Snapshot utilizado: {snapshot_name}"
    )

    records = prepare_data(records)

    print(
        f"Observaciones disponibles: {len(records)}"
    )

    if not records:
        raise ValueError(
            "No existen observaciones válidas para graficar."
        )

    (
        observation_numbers,
        carousel_medians,
        reels_medians,
    ) = calculate_evolution(records)

    create_plot(
        records=records,
        observation_numbers=observation_numbers,
        carousel_medians=carousel_medians,
        reels_medians=reels_medians,
        snapshot_name=snapshot_name,
    )