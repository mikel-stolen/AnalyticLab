import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "instagram"
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


def load_json(path: Path) -> Any:
    """Carga un JSON."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def file_timestamp(path: Path) -> datetime | None:
    """Extrae YYYYMMDD_HHMMSS desde el nombre del archivo."""
    match = TIMESTAMP_PATTERN.search(path.name)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%d_%H%M%S")
    except ValueError:
        return None


def safe_change(current: Any, previous: Any) -> float | None:
    """Calcula cambio absoluto si ambos valores son numéricos."""
    if not isinstance(current, (int, float)) or not isinstance(previous, (int, float)):
        return None
    return current - previous


def safe_percentage_change(current: Any, previous: Any) -> float | None:
    """Calcula crecimiento porcentual respecto al valor anterior."""
    if not isinstance(current, (int, float)) or not isinstance(previous, (int, float)):
        return None
    if previous == 0:
        return None
    return (current - previous) / previous * 100


def safe_velocity(change: float | None, t0: datetime | None, t1: datetime | None) -> float | None:
    """Calcula la velocidad media del cambio por hora."""
    if change is None or t0 is None or t1 is None:
        return None
    hours = (t1 - t0).total_seconds() / 3600
    return change / hours if hours > 0 else None


def find_snapshots(pattern: str) -> list[Path]:
    """Encuentra snapshots de analytics ordenados por timestamp."""
    return sorted(
        ANALYTICS_DIR.glob(pattern),
        key=lambda path: file_timestamp(path) or datetime.min,
    )


def is_valid_processed_snapshot(path: Path) -> bool:
    """Valida un dataset normalizado."""
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, list) or not data:
        return False

    return any(
        isinstance(post, dict)
        and post.get("insights_status") == "available"
        and any(isinstance(post.get(metric), (int, float)) for metric in METRICS)
        for post in data
    )


def find_valid_processed_snapshots() -> list[Path]:
    """Encuentra datasets normalizados válidos."""
    files = sorted(
        PROCESSED_DIR.glob("posts_normalized_*.json"),
        key=lambda path: file_timestamp(path) or datetime.min,
    )
    return [path for path in files if is_valid_processed_snapshot(path)]


def is_valid_engagement_snapshot(path: Path) -> bool:
    """Comprueba que un snapshot de engagement tenga observaciones."""
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError):
        return False
    summary = data.get("summary", {}) if isinstance(data, dict) else {}
    posts_analyzed = summary.get("posts_analyzed")
    return isinstance(posts_analyzed, int) and posts_analyzed > 0


def find_valid_engagement_snapshots() -> list[Path]:
    """Encuentra snapshots de engagement válidos."""
    return [
        path
        for path in find_snapshots("engagement_analysis_*.json")
        if is_valid_engagement_snapshot(path)
    ]


def nearest_snapshot(
    target_timestamp: datetime | None,
    snapshots: list[Path],
    max_delta_seconds: int = 300,
) -> Path | None:
    """Encuentra el snapshot analítico temporalmente más cercano."""
    if target_timestamp is None:
        return None

    candidates = []
    for path in snapshots:
        timestamp = file_timestamp(path)
        if timestamp is None:
            continue
        delta = abs((timestamp - target_timestamp).total_seconds())
        if delta <= max_delta_seconds:
            candidates.append((delta, path))

    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def index_posts(dataset: list[dict]) -> dict[str, dict]:
    """Indexa publicaciones por post_id."""
    return {
        post.get("post_id"): post
        for post in dataset
        if isinstance(post, dict) and post.get("post_id")
    }


def compare_post_metrics(
    previous_post: dict,
    current_post: dict,
    previous_time: datetime | None,
    current_time: datetime | None,
) -> dict:
    """Compara métricas y velocidad de crecimiento."""
    delta_hours = None
    if previous_time is not None and current_time is not None:
        delta_hours = (current_time - previous_time).total_seconds() / 3600

    result = {
        "delta_hours": round(delta_hours, 4) if delta_hours is not None else None,
        "metrics": {},
    }

    for metric in METRICS:
        previous_value = previous_post.get(metric)
        current_value = current_post.get(metric)
        absolute_change = safe_change(current_value, previous_value)
        percentage_change = safe_percentage_change(current_value, previous_value)
        velocity = safe_velocity(absolute_change, previous_time, current_time)

        result["metrics"][metric] = {
            "previous": previous_value,
            "current": current_value,
            "absolute_change": absolute_change,
            "percentage_change": round(percentage_change, 4) if percentage_change is not None else None,
            "velocity_per_hour": round(velocity, 4) if velocity is not None else None,
        }

    return result


def compare_processed_snapshots(previous_file: Path, current_file: Path) -> dict:
    """Compara dos datasets normalizados válidos."""
    previous_data = load_json(previous_file)
    current_data = load_json(current_file)

    if not isinstance(previous_data, list) or not isinstance(current_data, list):
        raise ValueError("Los snapshots normalizados deben contener listas.")

    previous_posts = index_posts(previous_data)
    current_posts = index_posts(current_data)
    previous_time = file_timestamp(previous_file)
    current_time = file_timestamp(current_file)

    common_ids = sorted(set(previous_posts) & set(current_posts))
    new_ids = sorted(set(current_posts) - set(previous_posts))
    missing_ids = sorted(set(previous_posts) - set(current_posts))

    changes = []
    for post_id in common_ids:
        previous_post = previous_posts[post_id]
        current_post = current_posts[post_id]
        changes.append({
            "post_id": post_id,
            "timestamp": current_post.get("timestamp"),
            "media_type": current_post.get("media_type"),
            "media_product_type": current_post.get("media_product_type"),
            "comparison": compare_post_metrics(
                previous_post,
                current_post,
                previous_time,
                current_time,
            ),
        })

    new_posts = [
        {
            "post_id": post_id,
            "timestamp": current_posts[post_id].get("timestamp"),
            "media_type": current_posts[post_id].get("media_type"),
            "media_product_type": current_posts[post_id].get("media_product_type"),
            "reach": current_posts[post_id].get("reach"),
            "views": current_posts[post_id].get("views"),
            "total_interactions": current_posts[post_id].get("total_interactions"),
        }
        for post_id in new_ids
    ]

    return {
        "previous_snapshot": previous_file.name,
        "current_snapshot": current_file.name,
        "snapshot_delta_hours": round((current_time - previous_time).total_seconds() / 3600, 4)
        if previous_time is not None and current_time is not None else None,
        "previous_post_count": len(previous_posts),
        "current_post_count": len(current_posts),
        "common_post_count": len(common_ids),
        "new_post_count": len(new_ids),
        "new_post_ids": new_ids,
        "new_posts": new_posts,
        "missing_post_count": len(missing_ids),
        "missing_post_ids": missing_ids,
        "post_changes": changes,
    }


def rank_post_changes(post_changes: list[dict], metric: str, field: str, limit: int = 5) -> list[dict]:
    """Ordena publicaciones por cambio absoluto, porcentual o velocidad."""
    ranked = []
    for post in post_changes:
        metric_data = post["comparison"]["metrics"].get(metric, {})
        value = metric_data.get(field)
        if isinstance(value, (int, float)):
            ranked.append({
                "post_id": post["post_id"],
                "timestamp": post.get("timestamp"),
                "media_type": post.get("media_type"),
                "media_product_type": post.get("media_product_type"),
                "previous": metric_data.get("previous"),
                "current": metric_data.get("current"),
                "change": value,
            })
    ranked.sort(key=lambda item: item["change"], reverse=True)
    return ranked[:limit]


def build_top_changes(processed: dict) -> dict:
    """Construye rankings absolutos, porcentuales y de velocidad."""
    return {
        metric: {
            "absolute": rank_post_changes(processed["post_changes"], metric, "absolute_change"),
            "percentage": rank_post_changes(processed["post_changes"], metric, "percentage_change"),
            "velocity_per_hour": rank_post_changes(processed["post_changes"], metric, "velocity_per_hour"),
        }
        for metric in ("reach", "views", "total_interactions")
    }


def compare_engagement_snapshots(previous_file: Path, current_file: Path) -> dict:
    """Compara resúmenes de engagement."""
    previous = load_json(previous_file)
    current = load_json(current_file)
    previous_summary = previous.get("summary", {})
    current_summary = current.get("summary", {})

    result = {}
    for metric in (
        "posts_analyzed",
        "average_engagement_rate",
        "max_engagement_rate",
        "min_engagement_rate",
    ):
        previous_value = previous_summary.get(metric)
        current_value = current_summary.get(metric)
        percentage_change = safe_percentage_change(current_value, previous_value)
        result[metric] = {
            "previous": previous_value,
            "current": current_value,
            "absolute_change": safe_change(current_value, previous_value),
            "percentage_change": round(percentage_change, 4) if percentage_change is not None else None,
        }

    return {
        "previous_snapshot": previous_file.name,
        "current_snapshot": current_file.name,
        "metrics": result,
    }


def compare_relative_performance_snapshots(previous_file: Path, current_file: Path) -> dict:
    """Compara Relative Performance por contexto."""
    previous = load_json(previous_file)
    current = load_json(current_file)
    previous_groups = previous.get("summary_by_previous_format", {})
    current_groups = current.get("summary_by_previous_format", {})

    result = {}
    for group in sorted(set(previous_groups) | set(current_groups)):
        previous_stats = previous_groups.get(group, {})
        current_stats = current_groups.get(group, {})
        group_result = {}

        for metric in (
            "sample_size",
            "median_relative_reach",
            "median_log2_relative_reach",
            "median_relative_interaction_rate",
        ):
            previous_value = previous_stats.get(metric)
            current_value = current_stats.get(metric)
            group_result[metric] = {
                "previous": previous_value,
                "current": current_value,
                "absolute_change": safe_change(current_value, previous_value),
            }

        result[group] = group_result

    return {
        "previous_snapshot": previous_file.name,
        "current_snapshot": current_file.name,
        "groups": result,
    }


def build_pair_report(
    previous_processed: Path,
    current_processed: Path,
    previous_engagement: Path | None = None,
    current_engagement: Path | None = None,
    previous_relative: Path | None = None,
    current_relative: Path | None = None,
) -> dict:
    """Construye el informe de una transición consecutiva."""
    processed = compare_processed_snapshots(previous_processed, current_processed)
    report = {
        "previous_snapshot": previous_processed.name,
        "current_snapshot": current_processed.name,
        "processed_data": processed,
        "top_changes": build_top_changes(processed),
    }

    if previous_engagement and current_engagement:
        report["engagement"] = compare_engagement_snapshots(previous_engagement, current_engagement)

    if previous_relative and current_relative:
        report["relative_performance"] = compare_relative_performance_snapshots(previous_relative, current_relative)

    return report


def timestamp_from_filename(filename: str) -> datetime | None:
    """Extrae timestamp desde un nombre de snapshot."""
    match = TIMESTAMP_PATTERN.search(filename)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%d_%H%M%S")
    except ValueError:
        return None


def build_post_growth_profile(post_id: str, post_info: dict) -> dict:
    """Construye la curva longitudinal de crecimiento de una publicación."""
    snapshots = post_info.get("snapshots", [])
    growth_steps = []

    for index in range(1, len(snapshots)):
        previous = snapshots[index - 1]
        current = snapshots[index]
        previous_time = timestamp_from_filename(previous["snapshot"])
        current_time = timestamp_from_filename(current["snapshot"])

        growth_steps.append({
            "from_snapshot": previous["snapshot"],
            "to_snapshot": current["snapshot"],
            "metrics": compare_post_metrics(
                previous["metrics"],
                current["metrics"],
                previous_time,
                current_time,
            ),
        })

    lifetime = {}
    if snapshots:
        first_metrics = snapshots[0]["metrics"]
        last_metrics = snapshots[-1]["metrics"]
        for metric in METRICS:
            initial = first_metrics.get(metric)
            final = last_metrics.get(metric)
            percentage_change = safe_percentage_change(final, initial)
            lifetime[metric] = {
                "initial": initial,
                "final": final,
                "absolute_change": safe_change(final, initial),
                "percentage_change": round(percentage_change, 4)
                if percentage_change is not None else None,
            }

    return {
        "post_id": post_id,
        "timestamp": post_info.get("timestamp"),
        "media_type": post_info.get("media_type"),
        "media_product_type": post_info.get("media_product_type"),
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
        "growth_steps": growth_steps,
        "lifetime": lifetime,
    }


def build_all_evolution_report() -> dict:
    """Construye todas las comparaciones consecutivas y perfiles longitudinales."""
    processed = find_valid_processed_snapshots()
    if len(processed) < 2:
        raise RuntimeError("Se necesitan al menos dos snapshots normalizados válidos.")

    engagement = find_valid_engagement_snapshots()
    relative = find_snapshots("relative_performance_*.json")

    pair_reports = []
    for index in range(1, len(processed)):
        previous_processed = processed[index - 1]
        current_processed = processed[index]
        t0 = file_timestamp(previous_processed)
        t1 = file_timestamp(current_processed)

        pair_reports.append(build_pair_report(
            previous_processed,
            current_processed,
            nearest_snapshot(t0, engagement),
            nearest_snapshot(t1, engagement),
            nearest_snapshot(t0, relative),
            nearest_snapshot(t1, relative),
        ))

    all_posts: dict[str, dict] = {}
    for snapshot_index, processed_file in enumerate(processed):
        data = load_json(processed_file)
        posts = index_posts(data)
        for post_id, post in posts.items():
            all_posts.setdefault(post_id, {
                "post_id": post_id,
                "timestamp": post.get("timestamp"),
                "media_type": post.get("media_type"),
                "media_product_type": post.get("media_product_type"),
                "snapshots": [],
            })
            all_posts[post_id]["snapshots"].append({
                "snapshot_index": snapshot_index,
                "snapshot": processed_file.name,
                "metrics": {metric: post.get(metric) for metric in METRICS},
            })

    profiles = [
        build_post_growth_profile(post_id, info)
        for post_id, info in all_posts.items()
    ]

    return {
        "created_at": datetime.now().isoformat(),
        "processed_snapshot_count": len(processed),
        "pair_count": len(pair_reports),
        "pair_reports": pair_reports,
        "post_evolution": list(all_posts.values()),
        "post_growth_profiles": profiles,
    }


def save_report(report: dict, prefix: str) -> Path:
    """Guarda un informe sin sobrescribir históricos."""
    COMPARISONS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = COMPARISONS_DIR / f"{prefix}_{timestamp}.json"
    with open(output, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)
    return output


def print_pair_report(report: dict) -> None:
    """Imprime el resumen de una comparación."""
    processed = report["processed_data"]
    print("\n" + "=" * 60)
    print("COMPARACIÓN DE SNAPSHOTS")
    print("=" * 60)
    print(f"Snapshot anterior: {processed['previous_snapshot']}")
    print(f"Snapshot actual:   {processed['current_snapshot']}")
    print(f"Δ tiempo: {processed['snapshot_delta_hours']} h")
    print(f"Publicaciones anteriores: {processed['previous_post_count']}")
    print(f"Publicaciones actuales:   {processed['current_post_count']}")
    print(f"Publicaciones nuevas:     {processed['new_post_count']}")

    if processed["new_posts"]:
        print("\nNuevas publicaciones:")
        for post in processed["new_posts"]:
            print(
                f"  {post['post_id']} | {post['timestamp']} | "
                f"{post['media_type']} | {post['media_product_type']} | "
                f"Reach={post['reach']} | Views={post['views']} | "
                f"Interactions={post['total_interactions']}"
            )

    if "engagement" in report:
        metric = report["engagement"]["metrics"]["average_engagement_rate"]
        print(f"\nEngagement medio: {metric['previous']} → {metric['current']}")

    if "relative_performance" in report:
        print("\nRelative Reach:")
        for group, values in report["relative_performance"]["groups"].items():
            metric = values["median_relative_reach"]
            print(f"  {group}: {metric['previous']} → {metric['current']}")

    for metric, label in (("reach", "Reach"), ("views", "Views"), ("total_interactions", "Interactions")):
        for field, title in (
            ("absolute", "Top cambios absolutos"),
            ("percentage", "Top crecimiento porcentual"),
            ("velocity_per_hour", "Top velocidad por hora"),
        ):
            print(f"\n{title} de {label}:")
            for item in report["top_changes"][metric][field]:
                if field == "percentage":
                    change = f"{item['change']:.2f}%"
                elif field == "velocity_per_hour":
                    change = f"{item['change']:.4f}/h"
                else:
                    change = str(item["change"])
                print(
                    f"  {item['post_id']} | "
                    f"{item['previous']} → {item['current']} | "
                    f"Δ {change}"
                )


def print_all_summary(report: dict) -> None:
    """Imprime resumen de la evolución completa."""
    print("\n" + "=" * 60)
    print("EVOLUCIÓN COMPLETA DE SNAPSHOTS")
    print("=" * 60)
    print(f"Snapshots válidos: {report['processed_snapshot_count']}")
    print(f"Comparaciones consecutivas: {report['pair_count']}")

    for pair in report["pair_reports"]:
        processed = pair["processed_data"]
        print(f"\n{processed['previous_snapshot']} → {processed['current_snapshot']}")
        print(f"  Δ tiempo: {processed['snapshot_delta_hours']} h")
        print(f"  Nuevas publicaciones: {processed['new_post_count']}")
        for post in processed["new_posts"]:
            print(
                f"  + Nuevo: {post['post_id']} | "
                f"{post['timestamp']} | {post['media_type']}"
            )
        top = pair["top_changes"]["reach"]["absolute"]
        if top:
            print(f"  Mayor Δ Reach: {top[0]['post_id']} ({top[0]['change']})")

    print("\nLos perfiles longitudinales están en 'post_growth_profiles'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compara snapshots de AnalyticLab.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Genera evolución completa y curvas de crecimiento por publicación.",
    )
    args = parser.parse_args()
    print("\nBuscando snapshots...")

    if args.all:
        report = build_all_evolution_report()
        output = save_report(report, "snapshot_evolution")
        print_all_summary(report)
        print("\nInforme completo guardado en:")
        print(output)
        return

    processed = find_valid_processed_snapshots()
    if len(processed) < 2:
        raise RuntimeError("Se necesitan al menos dos snapshots normalizados válidos para comparar.")

    engagement = find_valid_engagement_snapshots()
    relative = find_snapshots("relative_performance_*.json")

    previous_processed = processed[-2]
    current_processed = processed[-1]
    previous_time = file_timestamp(previous_processed)
    current_time = file_timestamp(current_processed)

    report = build_pair_report(
        previous_processed,
        current_processed,
        nearest_snapshot(previous_time, engagement),
        nearest_snapshot(current_time, engagement),
        nearest_snapshot(previous_time, relative),
        nearest_snapshot(current_time, relative),
    )

    output = save_report(report, "snapshot_comparison")
    print_pair_report(report)
    print("\nInforme guardado en:")
    print(output)


if __name__ == "__main__":
    main()
