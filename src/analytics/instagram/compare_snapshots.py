"""
Compara snapshots históricos de AnalyticLab.

Modos:
    python compare_snapshots.py
        Compara los dos últimos snapshots normalizados válidos.

    python compare_snapshots.py --all
        Compara todos los snapshots normalizados válidos consecutivos
        y construye la evolución completa T0 -> T1 -> T2 -> ...

El módulo:
- Ignora datasets normalizados defectuosos.
- Ignora snapshots de engagement sin observaciones válidas.
- Calcula cambios absolutos y porcentuales por publicación.
- Compara engagement y Relative Performance.
- Destaca publicaciones con mayores cambios.
- Conserva históricos de comparación.
- En modo --all construye la evolución cronológica por publicación.

No modifica ningún snapshot existente.
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "instagram"
)

ANALYTICS_DIR = PROCESSED_DIR / "analytics"
COMPARISONS_DIR = ANALYTICS_DIR / "comparisons"

METRICS = [
    "likes",
    "comments",
    "shares",
    "saved",
    "reach",
    "total_interactions",
    "views",
]

TIMESTAMP_PATTERN = re.compile(r"(\d{8}_\d{6})")


# ============================================================
# UTILIDADES GENERALES
# ============================================================


def load_json(path: Path):
    """Carga un JSON."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def file_timestamp(path: Path) -> datetime | None:
    """Extrae YYYYMMDD_HHMMSS del nombre del archivo."""

    match = TIMESTAMP_PATTERN.search(path.name)
    if not match:
        return None

    try:
        return datetime.strptime(
            match.group(1),
            "%Y%m%d_%H%M%S",
        )
    except ValueError:
        return None


def find_snapshots(pattern: str) -> list[Path]:
    """Encuentra snapshots de analytics ordenados por timestamp."""

    return sorted(
        ANALYTICS_DIR.glob(pattern),
        key=lambda path: file_timestamp(path) or datetime.min,
    )


def nearest_snapshot(
    target_timestamp: datetime | None,
    snapshots: list[Path],
    max_delta_seconds: int = 300,
) -> Path | None:
    """
    Busca el snapshot analítico más cercano al dataset normalizado.

    Esto evita asumir que los índices coinciden entre listas de snapshots,
    ya que algunos runs pueden fallar o producir un snapshot inválido.
    """

    if target_timestamp is None or not snapshots:
        return None

    candidates = []

    for path in snapshots:
        timestamp = file_timestamp(path)
        if timestamp is None:
            continue

        delta = abs(
            (timestamp - target_timestamp).total_seconds()
        )

        if delta <= max_delta_seconds:
            candidates.append((delta, path))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def safe_change(current, previous):
    """Calcula cambio absoluto."""

    if not isinstance(current, (int, float)):
        return None

    if not isinstance(previous, (int, float)):
        return None

    return current - previous


def safe_percentage_change(current, previous):
    """Calcula crecimiento porcentual respecto al valor anterior."""

    if not isinstance(current, (int, float)):
        return None

    if not isinstance(previous, (int, float)):
        return None

    if previous == 0:
        return None

    return ((current - previous) / previous) * 100


# ============================================================
# VALIDACIÓN DE SNAPSHOTS
# ============================================================


def is_valid_processed_snapshot(path: Path) -> bool:
    """Valida un dataset normalizado."""

    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError):
        return False

    if not isinstance(data, list) or not data:
        return False

    for post in data:
        if not isinstance(post, dict):
            continue

        if post.get("insights_status") != "available":
            continue

        if any(
            isinstance(post.get(metric), (int, float))
            for metric in METRICS
        ):
            return True

    return False


def find_valid_processed_snapshots() -> list[Path]:
    """Encuentra datasets normalizados válidos."""

    return [
        path
        for path in sorted(
            PROCESSED_DIR.glob("posts_normalized_*.json"),
            key=lambda file: file_timestamp(file) or datetime.min,
        )
        if is_valid_processed_snapshot(path)
    ]


def is_valid_engagement_snapshot(path: Path) -> bool:
    """Valida un snapshot de engagement."""

    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError):
        return False

    summary = data.get("summary", {})
    posts_analyzed = summary.get("posts_analyzed")

    return (
        isinstance(posts_analyzed, int)
        and posts_analyzed > 0
    )


def find_valid_engagement_snapshots() -> list[Path]:
    """Encuentra snapshots de engagement válidos."""

    return [
        path
        for path in find_snapshots("engagement_analysis_*.json")
        if is_valid_engagement_snapshot(path)
    ]


def load_analysis_snapshots() -> dict:
    """Carga todos los tipos de snapshots analíticos."""

    return {
        "engagement": find_valid_engagement_snapshots(),
        "sequence": find_snapshots("sequence_analysis_*.json"),
        "relative_performance": find_snapshots(
            "relative_performance_*.json"
        ),
    }


# ============================================================
# PUBLICACIONES
# ============================================================


def index_posts(dataset: list) -> dict:
    """Indexa publicaciones por post_id."""

    return {
        post.get("post_id"): post
        for post in dataset
        if isinstance(post, dict)
        and post.get("post_id")
    }


def compare_post_metrics(
    previous_post: dict,
    current_post: dict,
) -> dict:
    """Compara las métricas de una publicación."""

    comparison = {}

    for metric in METRICS:
        previous_value = previous_post.get(metric)
        current_value = current_post.get(metric)
        percentage_change = safe_percentage_change(
            current_value,
            previous_value,
        )

        comparison[metric] = {
            "previous": previous_value,
            "current": current_value,
            "absolute_change": safe_change(
                current_value,
                previous_value,
            ),
            "percentage_change": (
                round(percentage_change, 4)
                if percentage_change is not None
                else None
            ),
        }

    return comparison


def compare_processed_snapshots(
    previous_file: Path,
    current_file: Path,
) -> dict:
    """Compara dos datasets normalizados válidos."""

    previous_data = load_json(previous_file)
    current_data = load_json(current_file)

    if not isinstance(previous_data, list):
        raise ValueError(
            f"El snapshot no contiene una lista: {previous_file}"
        )

    if not isinstance(current_data, list):
        raise ValueError(
            f"El snapshot no contiene una lista: {current_file}"
        )

    previous_posts = index_posts(previous_data)
    current_posts = index_posts(current_data)

    common_post_ids = sorted(
        set(previous_posts).intersection(current_posts)
    )

    new_post_ids = sorted(
        set(current_posts).difference(previous_posts)
    )

    missing_post_ids = sorted(
        set(previous_posts).difference(current_posts)
    )

    post_changes = []

    for post_id in common_post_ids:
        previous_post = previous_posts[post_id]
        current_post = current_posts[post_id]

        post_changes.append({
            "post_id": post_id,
            "timestamp": current_post.get("timestamp"),
            "media_type": current_post.get("media_type"),
            "media_product_type": current_post.get(
                "media_product_type"
            ),
            "comparison": compare_post_metrics(
                previous_post,
                current_post,
            ),
        })

    return {
        "previous_snapshot": previous_file.name,
        "current_snapshot": current_file.name,
        "previous_post_count": len(previous_posts),
        "current_post_count": len(current_posts),
        "common_post_count": len(common_post_ids),
        "new_post_count": len(new_post_ids),
        "new_post_ids": new_post_ids,
        "missing_post_count": len(missing_post_ids),
        "missing_post_ids": missing_post_ids,
        "post_changes": post_changes,
    }


def rank_post_changes(
    post_changes: list,
    metric: str,
    by: str = "absolute_change",
    descending: bool = True,
    limit: int = 5,
) -> list:
    """Ordena publicaciones por cambio absoluto o porcentual."""

    ranked = []

    for post in post_changes:
        metric_data = post.get("comparison", {}).get(metric, {})
        value = metric_data.get(by)

        if isinstance(value, (int, float)):
            ranked.append({
                "post_id": post.get("post_id"),
                "timestamp": post.get("timestamp"),
                "media_type": post.get("media_type"),
                "media_product_type": post.get(
                    "media_product_type"
                ),
                "previous": metric_data.get("previous"),
                "current": metric_data.get("current"),
                "change": value,
            })

    ranked.sort(
        key=lambda item: item["change"],
        reverse=descending,
    )

    return ranked[:limit]


def build_top_changes(
    processed_comparison: dict,
) -> dict:
    """Construye rankings absolutos y relativos."""

    post_changes = processed_comparison.get(
        "post_changes",
        [],
    )

    return {
        metric: {
            "absolute": rank_post_changes(
                post_changes,
                metric,
                by="absolute_change",
                descending=True,
            ),
            "percentage": rank_post_changes(
                post_changes,
                metric,
                by="percentage_change",
                descending=True,
            ),
        }
        for metric in (
            "reach",
            "views",
            "total_interactions",
        )
    }


# ============================================================
# ANALYTICS SNAPSHOT COMPARISON
# ============================================================


def compare_engagement_snapshots(
    previous_file: Path,
    current_file: Path,
) -> dict:
    """Compara los resúmenes de engagement."""

    previous = load_json(previous_file)
    current = load_json(current_file)

    previous_summary = previous.get("summary", {})
    current_summary = current.get("summary", {})

    metrics = [
        "posts_analyzed",
        "average_engagement_rate",
        "max_engagement_rate",
        "min_engagement_rate",
    ]

    result = {}

    for metric in metrics:
        previous_value = previous_summary.get(metric)
        current_value = current_summary.get(metric)
        percentage_change = safe_percentage_change(
            current_value,
            previous_value,
        )

        result[metric] = {
            "previous": previous_value,
            "current": current_value,
            "absolute_change": safe_change(
                current_value,
                previous_value,
            ),
            "percentage_change": (
                round(percentage_change, 4)
                if percentage_change is not None
                else None
            ),
        }

    return {
        "previous_snapshot": previous_file.name,
        "current_snapshot": current_file.name,
        "metrics": result,
    }


def compare_relative_performance_snapshots(
    previous_file: Path,
    current_file: Path,
) -> dict:
    """Compara Relative Performance por contexto."""

    previous = load_json(previous_file)
    current = load_json(current_file)

    previous_groups = previous.get(
        "summary_by_previous_format",
        {},
    )

    current_groups = current.get(
        "summary_by_previous_format",
        {},
    )

    groups = sorted(
        set(previous_groups).union(current_groups)
    )

    result = {}

    for group in groups:
        previous_stats = previous_groups.get(group, {})
        current_stats = current_groups.get(group, {})

        metrics = [
            "sample_size",
            "median_relative_reach",
            "median_log2_relative_reach",
            "median_relative_interaction_rate",
        ]

        group_result = {}

        for metric in metrics:
            previous_value = previous_stats.get(metric)
            current_value = current_stats.get(metric)

            group_result[metric] = {
                "previous": previous_value,
                "current": current_value,
                "absolute_change": safe_change(
                    current_value,
                    previous_value,
                ),
            }

        result[group] = group_result

    return {
        "previous_snapshot": previous_file.name,
        "current_snapshot": current_file.name,
        "groups": result,
    }


# ============================================================
# MATCHING ANALYTICS TO PROCESSED SNAPSHOTS
# ============================================================


def build_processed_analytics_map(
    processed_files: list[Path],
    analysis_files: list[Path],
) -> dict[str, Path | None]:
    """
    Asocia cada processed snapshot con el analytics snapshot más cercano.

    No se basa en índices porque puede haber snapshots inválidos,
    fallos de ejecución o runs sin un tipo de análisis concreto.
    """

    result = {}

    for processed_file in processed_files:
        timestamp = file_timestamp(processed_file)
        result[processed_file.name] = nearest_snapshot(
            timestamp,
            analysis_files,
        )

    return result


# ============================================================
# CONSECUTIVE SNAPSHOT EVOLUTION
# ============================================================


def build_pair_report(
    previous_processed: Path,
    current_processed: Path,
    previous_engagement: Path | None = None,
    current_engagement: Path | None = None,
    previous_relative: Path | None = None,
    current_relative: Path | None = None,
) -> dict:
    """Construye el informe de un par consecutivo."""

    processed = compare_processed_snapshots(
        previous_processed,
        current_processed,
    )

    report = {
        "previous_snapshot": previous_processed.name,
        "current_snapshot": current_processed.name,
        "processed_data": processed,
        "top_changes": build_top_changes(processed),
    }

    if previous_engagement and current_engagement:
        report["engagement"] = compare_engagement_snapshots(
            previous_engagement,
            current_engagement,
        )

    if previous_relative and current_relative:
        report["relative_performance"] = (
            compare_relative_performance_snapshots(
                previous_relative,
                current_relative,
            )
        )

    return report


def build_all_evolution_report() -> dict:
    """
    Compara todos los snapshots válidos consecutivos.

    Produce:
        T0 -> T1
        T1 -> T2
        T2 -> T3
        ...

    También construye la trayectoria de cada publicación a través
    de todos los snapshots normalizados disponibles.
    """

    processed_files = find_valid_processed_snapshots()
    analysis_files = load_analysis_snapshots()

    if len(processed_files) < 2:
        raise RuntimeError(
            "Se necesitan al menos dos snapshots normalizados válidos."
        )

    engagement_map = build_processed_analytics_map(
        processed_files,
        analysis_files["engagement"],
    )

    relative_map = build_processed_analytics_map(
        processed_files,
        analysis_files["relative_performance"],
    )

    pair_reports = []

    for index in range(1, len(processed_files)):
        previous_processed = processed_files[index - 1]
        current_processed = processed_files[index]

        previous_engagement = engagement_map.get(
            previous_processed.name
        )
        current_engagement = engagement_map.get(
            current_processed.name
        )

        previous_relative = relative_map.get(
            previous_processed.name
        )
        current_relative = relative_map.get(
            current_processed.name
        )

        pair_report = build_pair_report(
            previous_processed,
            current_processed,
            previous_engagement,
            current_engagement,
            previous_relative,
            current_relative,
        )

        pair_reports.append(pair_report)

    # Evolución cronológica por publicación.
    all_posts: dict[str, dict] = {}

    for snapshot_index, processed_file in enumerate(processed_files):
        data = load_json(processed_file)
        posts = index_posts(data)

        for post_id, post in posts.items():
            if post_id not in all_posts:
                all_posts[post_id] = {
                    "post_id": post_id,
                    "timestamp": post.get("timestamp"),
                    "media_type": post.get("media_type"),
                    "media_product_type": post.get(
                        "media_product_type"
                    ),
                    "snapshots": [],
                }

            all_posts[post_id]["snapshots"].append({
                "snapshot_index": snapshot_index,
                "snapshot": processed_file.name,
                "metrics": {
                    metric: post.get(metric)
                    for metric in METRICS
                },
            })

    return {
        "created_at": datetime.now().isoformat(),
        "processed_snapshot_count": len(processed_files),
        "pair_count": len(pair_reports),
        "pair_reports": pair_reports,
        "post_evolution": list(all_posts.values()),
    }


# ============================================================
# SAVE
# ============================================================


def save_comparison(
    report: dict,
    filename_prefix: str,
) -> Path:
    """Guarda un informe sin sobrescribir históricos."""

    COMPARISONS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    output_file = (
        COMPARISONS_DIR
        / f"{filename_prefix}_{timestamp}.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False,
        )

    return output_file


# ============================================================
# CONSOLE OUTPUT
# ============================================================


def print_pair_report(report: dict):
    """Imprime el resumen de una comparación."""

    processed = report["processed_data"]

    print("\n" + "=" * 60)
    print("COMPARACIÓN DE SNAPSHOTS")
    print("=" * 60)

    print(
        f"Snapshot anterior: {processed['previous_snapshot']}"
    )
    print(
        f"Snapshot actual:   {processed['current_snapshot']}"
    )
    print(
        f"Publicaciones anteriores: {processed['previous_post_count']}"
    )
    print(
        f"Publicaciones actuales:   {processed['current_post_count']}"
    )
    print(
        f"Publicaciones nuevas:     {processed['new_post_count']}"
    )

    if "engagement" in report:
        engagement = report["engagement"]["metrics"]
        print(
            "\nEngagement medio: "
            f"{engagement['average_engagement_rate']['previous']} "
            "→ "
            f"{engagement['average_engagement_rate']['current']}"
        )

    if "relative_performance" in report:
        groups = report["relative_performance"]["groups"]
        print("\nRelative Reach:")

        for group, values in groups.items():
            metric = values.get("median_relative_reach", {})
            print(
                f"  {group}: "
                f"{metric.get('previous')} → "
                f"{metric.get('current')}"
            )

    for metric, label in (
        ("reach", "Reach"),
        ("views", "Views"),
        ("total_interactions", "Interactions"),
    ):
        print(f"\nTop cambios absolutos de {label}:")

        for item in report["top_changes"][metric]["absolute"]:
            print(
                f"  {item['post_id']} | "
                f"{item['previous']} → {item['current']} | "
                f"Δ {item['change']}"
            )

        print(f"Top crecimiento porcentual de {label}:")

        for item in report["top_changes"][metric]["percentage"]:
            print(
                f"  {item['post_id']} | "
                f"{item['previous']} → {item['current']} | "
                f"Δ {item['change']:.2f}%"
            )


def print_all_summary(report: dict):
    """Imprime resumen de la evolución completa."""

    print("\n" + "=" * 60)
    print("EVOLUCIÓN COMPLETA DE SNAPSHOTS")
    print("=" * 60)

    print(
        f"Snapshots válidos: {report['processed_snapshot_count']}"
    )
    print(
        f"Comparaciones consecutivas: {report['pair_count']}"
    )

    for pair in report["pair_reports"]:
        processed = pair["processed_data"]
        print(
            f"\n{processed['previous_snapshot']}"
            f" → "
            f"{processed['current_snapshot']}"
        )

        print(
            f"  Nuevas publicaciones: "
            f"{processed['new_post_count']}"
        )

        reach_items = pair["top_changes"]["reach"]["absolute"]

        if reach_items:
            top = reach_items[0]
            print(
                f"  Mayor Δ Reach: {top['post_id']} "
                f"({top['change']})"
            )

    print(
        "\nLa evolución detallada por publicación queda almacenada "
        "en post_evolution."
    )


# ============================================================
# MAIN
# ============================================================


def main():
    parser = argparse.ArgumentParser(
        description="Compara snapshots de AnalyticLab."
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "Compara todos los snapshots válidos consecutivos "
            "y genera la evolución completa."
        ),
    )

    args = parser.parse_args()

    print("\nBuscando snapshots...")

    if args.all:
        report = build_all_evolution_report()

        output_file = save_comparison(
            report,
            "snapshot_evolution",
        )

        print_all_summary(report)

        print("\nInforme completo guardado en:")
        print(output_file)
        return

    processed_snapshots = find_valid_processed_snapshots()

    if len(processed_snapshots) < 2:
        raise RuntimeError(
            "Se necesitan al menos dos snapshots normalizados "
            "válidos para comparar."
        )

    analysis_snapshots = load_analysis_snapshots()

    previous_processed = processed_snapshots[-2]
    current_processed = processed_snapshots[-1]

    previous_timestamp = file_timestamp(previous_processed)
    current_timestamp = file_timestamp(current_processed)

    previous_engagement = nearest_snapshot(
        previous_timestamp,
        analysis_snapshots["engagement"],
    )
    current_engagement = nearest_snapshot(
        current_timestamp,
        analysis_snapshots["engagement"],
    )

    previous_relative = nearest_snapshot(
        previous_timestamp,
        analysis_snapshots["relative_performance"],
    )
    current_relative = nearest_snapshot(
        current_timestamp,
        analysis_snapshots["relative_performance"],
    )

    report = build_pair_report(
        previous_processed,
        current_processed,
        previous_engagement,
        current_engagement,
        previous_relative,
        current_relative,
    )

    output_file = save_comparison(
        report,
        "snapshot_comparison",
    )

    print_pair_report(report)

    print("\nInforme guardado en:")
    print(output_file)


if __name__ == "__main__":
    main()
