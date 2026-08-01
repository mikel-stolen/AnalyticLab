"""
AnalyticLab - H6: estado global de engagement de la cuenta.

Calcula:
1) Estado previo de engagement para cada publicación:
   - EG_3
   - EG_5
   - EG_7d
   - median histórico previo
   - Account Temperature

2) Primera observación posterior a la publicación:
   - reach
   - views
   - total interactions
   - interaction rate
   - tiempo desde publicación

3) Comparaciones para H6:
   - EG_3 -> Initial IR
   - EG_5 -> Initial IR
   - EG_7d -> Initial IR
   - EG_5 -> Initial Reach
   - EG_5 -> Initial Views
   - Temperature -> Initial IR
   - Temperature -> Initial Reach
   - Pearson y Spearman cuando hay suficientes pares.

4) Estado agregado de la cuenta:
   - última semana
   - semana anterior
   - histórico completo
   - diferencias absolutas y porcentuales
   - contribución de la última semana al total acumulado
   - comparación del engagement ponderado y no ponderado

No modifica snapshots existentes.
"""

import json
import math
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "instagram"
)

ANALYTICS_DIR = (
    PROCESSED_DIR
    / "analytics"
)


# ============================================================
# FILES / TIME
# ============================================================


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def local_timezone():
    return datetime.now().astimezone().tzinfo


def parse_timestamp(value: str | None) -> datetime | None:
    """Parsea timestamp de Meta y devuelve datetime aware."""

    if not value:
        return None

    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    return None


def snapshot_timestamp(path: Path) -> datetime | None:
    """
    Extrae timestamp del nombre posts_normalized_YYYYMMDD_HHMMSS.json
    y lo interpreta en la zona horaria local del sistema.
    """

    try:
        stamp = path.stem.rsplit("_", 2)
        raw = f"{stamp[-2]}_{stamp[-1]}"

        return datetime.strptime(
            raw,
            "%Y%m%d_%H%M%S",
        ).replace(tzinfo=local_timezone())

    except (ValueError, IndexError):
        return None


def find_processed_snapshots() -> list[Path]:
    files = list(
        PROCESSED_DIR.glob(
            "posts_normalized_*.json"
        )
    )

    return sorted(
        files,
        key=lambda path: (
            snapshot_timestamp(path)
            or datetime.min.replace(
                tzinfo=local_timezone()
            )
        ),
    )


# ============================================================
# METRICS
# ============================================================


def interaction_rate(post: dict) -> float | None:
    reach = post.get("reach")
    interactions = post.get("total_interactions")

    if not isinstance(reach, (int, float)):
        return None

    if not isinstance(interactions, (int, float)):
        return None

    if reach <= 0:
        return None

    return interactions / reach * 100


def median_valid(values: list[float]) -> float | None:
    valid = [
        value
        for value in values
        if isinstance(value, (int, float))
    ]

    if not valid:
        return None

    return statistics.median(valid)


def safe_change(current: Any, previous: Any):
    if not isinstance(current, (int, float)):
        return None

    if not isinstance(previous, (int, float)):
        return None

    return current - previous


def safe_percentage_change(
    current: Any,
    previous: Any,
):
    if not isinstance(current, (int, float)):
        return None

    if not isinstance(previous, (int, float)):
        return None

    if previous == 0:
        return None

    return (current - previous) / previous * 100


# ============================================================
# PRE-PUBLICATION ACCOUNT STATE
# ============================================================


def posts_before(
    posts: list[dict],
    publication_time: datetime,
) -> list[dict]:

    previous = []

    for post in posts:
        timestamp = parse_timestamp(
            post.get("timestamp")
        )

        if timestamp is None:
            continue

        if timestamp < publication_time:
            previous.append(post)

    return sorted(
        previous,
        key=lambda post: (
            parse_timestamp(
                post.get("timestamp")
            )
            or publication_time
        ),
    )


def engagement_state_before_post(
    posts: list[dict],
    publication_time: datetime,
) -> dict:

    previous = posts_before(
        posts,
        publication_time,
    )

    last_3 = previous[-3:]
    last_5 = previous[-5:]

    eg_3 = median_valid([
        interaction_rate(post)
        for post in last_3
    ])

    eg_5 = median_valid([
        interaction_rate(post)
        for post in last_5
    ])

    seven_days_ago = (
        publication_time
        - timedelta(days=7)
    )

    last_7d = [
        post
        for post in previous
        if (
            parse_timestamp(
                post.get("timestamp")
            )
            is not None
            and parse_timestamp(
                post.get("timestamp")
            )
            >= seven_days_ago
        )
    ]

    eg_7d = median_valid([
        interaction_rate(post)
        for post in last_7d
    ])

    historical_rates = [
        interaction_rate(post)
        for post in previous
    ]

    historical_rates = [
        value
        for value in historical_rates
        if value is not None
    ]

    historical_median = median_valid(
        historical_rates
    )

    temperature = None

    if (
        eg_5 is not None
        and historical_median is not None
        and historical_median > 0
    ):
        temperature = (
            eg_5 / historical_median
        )

    return {
        "previous_post_count": len(previous),
        "previous_3_post_count": len(last_3),
        "previous_5_post_count": len(last_5),
        "previous_7d_post_count": len(last_7d),
        "eg_3": round(eg_3, 4)
        if eg_3 is not None else None,
        "eg_5": round(eg_5, 4)
        if eg_5 is not None else None,
        "eg_7d": round(eg_7d, 4)
        if eg_7d is not None else None,
        "historical_median_ir": (
            round(historical_median, 4)
            if historical_median is not None
            else None
        ),
        "account_temperature": (
            round(temperature, 4)
            if temperature is not None
            else None
        ),
    }


# ============================================================
# INITIAL OBSERVATION
# ============================================================


def get_initial_observation(
    post_id: str,
    publication_time: datetime,
    snapshot_paths: list[Path],
    max_initial_hours: float = 48.0,
) -> dict | None:

    candidates = []

    for path in snapshot_paths:
        snap_time = snapshot_timestamp(path)

        if snap_time is None:
            continue

        publication_local = publication_time.astimezone(
            local_timezone()
        )

        delta_hours = (
            snap_time - publication_local
        ).total_seconds() / 3600

        if delta_hours < 0:
            continue

        if delta_hours > max_initial_hours:
            continue

        try:
            dataset = load_json(path)
        except (
            OSError,
            json.JSONDecodeError,
        ):
            continue

        for post in dataset:
            if post.get("post_id") != post_id:
                continue

            candidates.append({
                "snapshot": path.name,
                "snapshot_time": snap_time.isoformat(),
                "hours_after_publication": round(
                    delta_hours,
                    4,
                ),
                "metrics": {
                    "reach": post.get("reach"),
                    "views": post.get("views"),
                    "total_interactions": post.get(
                        "total_interactions"
                    ),
                    "likes": post.get("likes"),
                    "comments": post.get("comments"),
                    "shares": post.get("shares"),
                    "saved": post.get("saved"),
                    "interaction_rate": (
                        round(
                            interaction_rate(post),
                            4,
                        )
                        if interaction_rate(post)
                        is not None
                        else None
                    ),
                },
            })

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item["hours_after_publication"]
    )

    return candidates[0]


# ============================================================
# CORRELATIONS
# ============================================================


def pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) != len(y) or len(x) < 3:
        return None

    mean_x = statistics.mean(x)
    mean_y = statistics.mean(y)

    numerator = sum(
        (a - mean_x) * (b - mean_y)
        for a, b in zip(x, y)
    )

    denominator_x = math.sqrt(
        sum(
            (a - mean_x) ** 2
            for a in x
        )
    )

    denominator_y = math.sqrt(
        sum(
            (b - mean_y) ** 2
            for b in y
        )
    )

    denominator = (
        denominator_x * denominator_y
    )

    if denominator == 0:
        return None

    return numerator / denominator


def rank_values(values: list[float]) -> list[float]:
    """Ranks simples; empates reciben el rango medio."""

    indexed = sorted(
        enumerate(values),
        key=lambda item: item[1],
    )

    ranks = [0.0] * len(values)

    i = 0

    while i < len(indexed):
        j = i

        while (
            j + 1 < len(indexed)
            and indexed[j + 1][1]
            == indexed[i][1]
        ):
            j += 1

        rank = (i + j + 2) / 2

        for k in range(i, j + 1):
            ranks[indexed[k][0]] = rank

        i = j + 1

    return ranks


def spearman(
    x: list[float],
    y: list[float],
) -> float | None:

    if len(x) != len(y) or len(x) < 3:
        return None

    return pearson(
        rank_values(x),
        rank_values(y),
    )


def build_hypothesis_pairs(
    records: list[dict],
) -> dict:

    definitions = {
        "eg_3_vs_initial_ir": (
            "eg_3",
            "interaction_rate",
        ),
        "eg_5_vs_initial_ir": (
            "eg_5",
            "interaction_rate",
        ),
        "eg_7d_vs_initial_ir": (
            "eg_7d",
            "interaction_rate",
        ),
        "eg_5_vs_initial_reach": (
            "eg_5",
            "reach",
        ),
        "eg_5_vs_initial_views": (
            "eg_5",
            "views",
        ),
        "temperature_vs_initial_ir": (
            "account_temperature",
            "interaction_rate",
        ),
        "temperature_vs_initial_reach": (
            "account_temperature",
            "reach",
        ),
    }

    result = {}

    for name, (
        state_key,
        outcome_key,
    ) in definitions.items():

        pairs = []

        for record in records:
            initial = record.get(
                "initial_observation"
            )

            if not initial:
                continue

            state = record[
                "pre_publication_state"
            ].get(state_key)

            outcome = initial[
                "metrics"
            ].get(outcome_key)

            if not isinstance(
                state,
                (int, float),
            ):
                continue

            if not isinstance(
                outcome,
                (int, float),
            ):
                continue

            pairs.append({
                "post_id": record[
                    "post"
                ]["post_id"],
                "timestamp": record[
                    "post"
                ]["timestamp"],
                "media_type": record[
                    "post"
                ]["media_type"],
                "state_value": state,
                "initial_value": outcome,
                "initial_snapshot": initial[
                    "snapshot"
                ],
                "hours_after_publication": (
                    initial[
                        "hours_after_publication"
                    ]
                ),
            })

        x = [
            item["state_value"]
            for item in pairs
        ]

        y = [
            item["initial_value"]
            for item in pairs
        ]

        result[name] = {
            "n": len(pairs),
            "pearson_r": (
                round(pearson(x, y), 4)
                if pearson(x, y)
                is not None
                else None
            ),
            "spearman_rho": (
                round(spearman(x, y), 4)
                if spearman(x, y)
                is not None
                else None
            ),
            "pairs": pairs,
        }

    return result


# ============================================================
# WHOLE ACCOUNT WINDOWS
# ============================================================


def aggregate_post_metrics(
    posts: list[dict],
) -> dict:
    """
    Agrega el estado de la cuenta.

    Important:
    - weighted IR = total interactions / total reach.
    - mean post IR = media simple de los IR.
    - median post IR = mediana de los IR.
    """

    valid = [
        post
        for post in posts
        if isinstance(post, dict)
    ]

    reaches = [
        post.get("reach")
        for post in valid
        if isinstance(post.get("reach"), (int, float))
        and post.get("reach") > 0
    ]

    views = [
        post.get("views")
        for post in valid
        if isinstance(post.get("views"), (int, float))
        and post.get("views") >= 0
    ]

    interactions = [
        post.get("total_interactions")
        for post in valid
        if isinstance(
            post.get("total_interactions"),
            (int, float),
        )
        and post.get("total_interactions") >= 0
    ]

    rates = [
        interaction_rate(post)
        for post in valid
    ]

    rates = [
        value
        for value in rates
        if value is not None
    ]

    total_reach = sum(reaches)
    total_views = sum(views)
    total_interactions = sum(interactions)

    weighted_ir = (
        total_interactions
        / total_reach
        * 100
        if total_reach > 0
        else None
    )

    mean_ir = (
        statistics.mean(rates)
        if rates
        else None
    )

    median_ir = (
        statistics.median(rates)
        if rates
        else None
    )

    return {
        "post_count": len(valid),
        "posts_with_reach": len(reaches),
        "posts_with_views": len(views),
        "posts_with_interactions": len(
            interactions
        ),
        "total_reach": total_reach,
        "total_views": total_views,
        "total_interactions": (
            total_interactions
        ),
        "weighted_interaction_rate": (
            round(weighted_ir, 4)
            if weighted_ir is not None
            else None
        ),
        "mean_post_interaction_rate": (
            round(mean_ir, 4)
            if mean_ir is not None
            else None
        ),
        "median_post_interaction_rate": (
            round(median_ir, 4)
            if median_ir is not None
            else None
        ),
    }


def aggregate_window(
    posts: list[dict],
    start: datetime | None = None,
    end: datetime | None = None,
) -> dict:

    selected = []

    for post in posts:
        timestamp = parse_timestamp(
            post.get("timestamp")
        )

        if timestamp is None:
            continue

        if (
            start is not None
            and timestamp < start
        ):
            continue

        if (
            end is not None
            and timestamp > end
        ):
            continue

        selected.append(post)

    return aggregate_post_metrics(
        selected
    )


def compare_window_metrics(
    current: dict,
    previous: dict,
) -> dict:

    metrics = [
        "post_count",
        "total_reach",
        "total_views",
        "total_interactions",
        "weighted_interaction_rate",
        "mean_post_interaction_rate",
        "median_post_interaction_rate",
    ]

    result = {}

    for metric in metrics:
        current_value = current.get(metric)
        previous_value = previous.get(metric)

        percentage = safe_percentage_change(
            current_value,
            previous_value,
        )

        result[metric] = {
            "current": current_value,
            "previous": previous_value,
            "absolute_change": safe_change(
                current_value,
                previous_value,
            ),
            "percentage_change": (
                round(percentage, 4)
                if percentage is not None
                else None
            ),
        }

    return result


def compare_windows(
    all_posts: list[dict],
    reference_time: datetime,
) -> dict:
    """
    Compara:
        - última semana
        - semana anterior
        - histórico completo

    Además calcula cuánto del total acumulado proviene de los últimos
    7 días, para distinguir crecimiento, acumulación y dependencia reciente.
    """

    week_start = (
        reference_time
        - timedelta(days=7)
    )

    previous_week_start = (
        reference_time
        - timedelta(days=14)
    )

    last_7d = aggregate_window(
        all_posts,
        start=week_start,
        end=reference_time,
    )

    previous_7d = aggregate_window(
        all_posts,
        start=previous_week_start,
        end=week_start,
    )

    all_time = aggregate_window(
        all_posts,
        end=reference_time,
    )

    contribution = {}

    for metric in (
        "total_reach",
        "total_views",
        "total_interactions",
    ):

        weekly_value = last_7d.get(metric)
        total_value = all_time.get(metric)

        contribution[metric] = (
            round(
                weekly_value
                / total_value
                * 100,
                4,
            )
            if (
                isinstance(
                    weekly_value,
                    (int, float),
                )
                and isinstance(
                    total_value,
                    (int, float),
                )
                and total_value > 0
            )
            else None
        )

    return {
        "reference_time": (
            reference_time.isoformat()
        ),
        "last_7d": {
            "window_start": (
                week_start.isoformat()
            ),
            "window_end": (
                reference_time.isoformat()
            ),
            **last_7d,
        },
        "previous_7d": {
            "window_start": (
                previous_week_start.isoformat()
            ),
            "window_end": (
                week_start.isoformat()
            ),
            **previous_7d,
        },
        "all_time": {
            "window_start": None,
            "window_end": (
                reference_time.isoformat()
            ),
            **all_time,
        },
        "last_7d_vs_previous_7d": (
            compare_window_metrics(
                last_7d,
                previous_7d,
            )
        ),
        "last_7d_vs_all_time": (
            compare_window_metrics(
                last_7d,
                all_time,
            )
        ),
        "last_7d_contribution_to_all_time_percent": (
            contribution
        ),
    }


# ============================================================
# RECORDS
# ============================================================


def build_records(
    posts: list[dict],
    snapshot_paths: list[Path],
) -> list[dict]:

    sorted_posts = sorted(
        posts,
        key=lambda post: (
            parse_timestamp(
                post.get("timestamp")
            )
            or datetime.max.replace(
                tzinfo=local_timezone()
            )
        ),
    )

    records = []

    for post in sorted_posts:

        publication_time = parse_timestamp(
            post.get("timestamp")
        )

        if publication_time is None:
            continue

        state = engagement_state_before_post(
            sorted_posts,
            publication_time,
        )

        initial = get_initial_observation(
            post.get("post_id"),
            publication_time,
            snapshot_paths,
        )

        records.append({
            "post": {
                "post_id": post.get(
                    "post_id"
                ),
                "timestamp": post.get(
                    "timestamp"
                ),
                "media_type": post.get(
                    "media_type"
                ),
                "media_product_type": post.get(
                    "media_product_type"
                ),
            },
            "pre_publication_state": state,
            "initial_observation": initial,
        })

    return records


# ============================================================
# SAVE
# ============================================================


def save_snapshot(
    records: list[dict],
    account_windows: dict,
    hypothesis_pairs: dict,
    latest_snapshot: str,
) -> Path:

    ANALYTICS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    output_file = (
        ANALYTICS_DIR
        / (
            "account_engagement_state_"
            f"{timestamp}.json"
        )
    )

    output = {
        "snapshot": {
            "created_at": (
                datetime.now().isoformat()
            ),
            "source_normalized_snapshot": (
                latest_snapshot
            ),
        },
        "study": {
            "name": (
                "Account engagement state "
                "and initial post performance"
            ),
            "hypothesis": (
                "Higher pre-publication account "
                "engagement is associated with "
                "higher initial post engagement "
                "and/or reach."
            ),
            "account_window_analysis": (
                "Compares the last 7 days, the previous "
                "7 days and the full available history."
            ),
            "weighted_ir_definition": (
                "Total interactions divided by total reach."
            ),
            "mean_ir_definition": (
                "Simple mean of publication-level interaction rates."
            ),
            "median_ir_definition": (
                "Median of publication-level interaction rates."
            ),
            "last_7d_contribution_definition": (
                "Share of all observed reach, views and interactions "
                "generated by publications in the last 7 days."
            ),
            "causality_warning": (
                "This is an observational analysis "
                "and does not establish causality."
            ),
        },
        "account_windows": account_windows,
        "hypothesis_pairs": hypothesis_pairs,
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


# ============================================================
# MAIN
# ============================================================


def main():

    print(
        "\nCargando snapshots normalizados..."
    )

    snapshot_paths = (
        find_processed_snapshots()
    )

    if not snapshot_paths:
        raise RuntimeError(
            "No se encontraron snapshots normalizados."
        )

    latest_snapshot = snapshot_paths[-1]
    posts = load_json(latest_snapshot)

    if not isinstance(posts, list):
        raise RuntimeError(
            "El snapshot normalizado debe contener una lista."
        )

    print(
        f"Snapshots normalizados: "
        f"{len(snapshot_paths)}"
    )

    print(
        f"Publicaciones disponibles: "
        f"{len(posts)}"
    )

    reference_time = (
        snapshot_timestamp(
            latest_snapshot
        )
        or datetime.now().astimezone()
    )

    records = build_records(
        posts,
        snapshot_paths,
    )

    valid_initial = [
        record
        for record in records
        if record.get(
            "initial_observation"
        )
    ]

    hypothesis_pairs = (
        build_hypothesis_pairs(
            records
        )
    )

    account_windows = compare_windows(
        posts,
        reference_time,
    )

    print(
        "\n============================================================"
    )

    print(
        "H6 + ESTADO GLOBAL DE LA CUENTA"
    )

    print(
        "============================================================"
    )

    print(
        "\nÚltimos 7 días:"
    )

    last_7d = account_windows[
        "last_7d"
    ]

    print(
        f"  Posts = "
        f"{last_7d['post_count']}"
    )

    print(
        f"  Reach acumulado = "
        f"{last_7d['total_reach']}"
    )

    print(
        f"  Views acumuladas = "
        f"{last_7d['total_views']}"
    )

    print(
        f"  Interacciones = "
        f"{last_7d['total_interactions']}"
    )

    print(
        f"  IR ponderado = "
        f"{last_7d['weighted_interaction_rate']}%"
    )

    print(
        f"  IR medio por post = "
        f"{last_7d['mean_post_interaction_rate']}%"
    )

    print(
        "\nHistórico completo:"
    )

    all_time = account_windows[
        "all_time"
    ]

    print(
        f"  Posts = "
        f"{all_time['post_count']}"
    )

    print(
        f"  Reach acumulado = "
        f"{all_time['total_reach']}"
    )

    print(
        f"  Views acumuladas = "
        f"{all_time['total_views']}"
    )

    print(
        f"  Interacciones = "
        f"{all_time['total_interactions']}"
    )

    print(
        f"  IR ponderado = "
        f"{all_time['weighted_interaction_rate']}%"
    )

    print(
        "\nContribución de la última semana al total:"
    )

    contribution = account_windows[
        "last_7d_contribution_to_all_time_percent"
    ]

    for metric, label in (
        ("total_reach", "Reach"),
        ("total_views", "Views"),
        ("total_interactions", "Interactions"),
    ):
        print(
            f"  {label}: "
            f"{contribution[metric]}%"
        )

    print(
        "\nPares para H6:"
    )

    for name, result in hypothesis_pairs.items():
        print(
            f"  {name}: "
            f"n={result['n']} | "
            f"Pearson={result['pearson_r']} | "
            f"Spearman={result['spearman_rho']}"
        )

    print(
        f"\nPublicaciones con observación inicial: "
        f"{len(valid_initial)}"
    )

    output_file = save_snapshot(
        records,
        account_windows,
        hypothesis_pairs,
        latest_snapshot.name,
    )

    print(
        "\nAnálisis guardado en:"
    )
    print(output_file)


if __name__ == "__main__":
    main()
