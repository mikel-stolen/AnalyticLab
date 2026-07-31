import json
import math
import random
import statistics
import sys
from datetime import datetime
from pathlib import Path


def find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        if (
            parent
            / "data"
            / "processed"
            / "instagram"
        ).exists():
            return parent
    raise RuntimeError(
        "No se pudo localizar la raíz de AnalyticLab."
    )


PROJECT_ROOT = find_project_root()
ANALYTICS_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "instagram"
    / "analytics"
)

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from h6_nonlinear_analysis import (
        fit_linear,
        fit_quadratic,
        fit_threshold,
        fit_saturation,
    )
except ImportError as exc:
    raise RuntimeError(
        "Coloca h6_robustness.py junto a "
        "h6_nonlinear_analysis.py."
    ) from exc


MODEL_NAMES = (
    "linear",
    "quadratic",
    "threshold",
    "saturation",
)


def load_json(path: Path) -> dict:
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def latest_state_snapshot() -> Path:
    files = sorted(
        ANALYTICS_DIR.glob(
            "account_engagement_state_*.json"
        ),
        key=lambda path: path.stat().st_mtime,
    )
    if not files:
        raise RuntimeError(
            "No se encontraron snapshots "
            "account_engagement_state_*.json"
        )
    return files[-1]


def calc_mae(y, predictions):
    if not y:
        return None
    return statistics.mean(
        abs(actual - pred)
        for actual, pred in zip(
            y,
            predictions,
        )
    )


def calc_rmse(y, predictions):
    if not y:
        return None
    return math.sqrt(
        statistics.mean(
            (actual - pred) ** 2
            for actual, pred in zip(
                y,
                predictions,
            )
        )
    )


def calc_r2(y, predictions):
    if not y:
        return None

    mean_y = statistics.mean(y)

    sse = sum(
        (actual - pred) ** 2
        for actual, pred in zip(
            y,
            predictions,
        )
    )

    sst = sum(
        (actual - mean_y) ** 2
        for actual in y
    )

    if sst == 0:
        return None

    return 1 - sse / sst


def predict_model(
    name,
    model,
    x_value,
):
    params = model.get(
        "parameters",
        {},
    )

    if name == "linear":
        return (
            params["intercept"]
            + params["slope"] * x_value
        )

    if name == "quadratic":
        return (
            params["intercept"]
            + params["linear"] * x_value
            + params["quadratic"] * x_value * x_value
        )

    if name == "threshold":
        return (
            params["left_mean"]
            if x_value <= params["threshold"]
            else params["right_mean"]
        )

    if name == "saturation":
        transformed = 1 - math.exp(
            -params["k"]
            * max(
                x_value - params["x_shift"],
                0.0,
            )
        )
        return (
            params["intercept"]
            + params["amplitude"] * transformed
        )

    return None


def fit_model(name, x, y):
    if name == "linear":
        return fit_linear(x, y)
    if name == "quadratic":
        return fit_quadratic(x, y)
    if name == "threshold":
        return fit_threshold(x, y)
    if name == "saturation":
        return fit_saturation(x, y)
    raise ValueError(name)


def percentile(values, p):
    if not values:
        return None

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    pos = (len(ordered) - 1) * p
    low = math.floor(pos)
    high = math.ceil(pos)

    if low == high:
        return ordered[low]

    fraction = pos - low

    return (
        ordered[low]
        + fraction * (
            ordered[high]
            - ordered[low]
        )
    )


def summarize(values):
    if not values:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "p025": None,
            "p975": None,
        }

    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "p025": percentile(values, 0.025),
        "p975": percentile(values, 0.975),
    }


def bootstrap_model(
    x,
    y,
    iterations=5000,
    seed=20260731,
):
    n = len(x)

    if n < 4:
        return {
            "status": "insufficient_data",
            "n": n,
            "iterations_requested": iterations,
        }

    rng = random.Random(seed)

    r2_values = {
        name: []
        for name in MODEL_NAMES
    }

    mae_values = {
        name: []
        for name in MODEL_NAMES
    }

    winners = {
        name: 0
        for name in MODEL_NAMES
    }

    successful = 0

    for _ in range(iterations):
        indices = [
            rng.randrange(n)
            for _ in range(n)
        ]

        bx = [x[i] for i in indices]
        by = [y[i] for i in indices]

        fitted = {}

        for name in MODEL_NAMES:
            try:
                model = fit_model(
                    name,
                    bx,
                    by,
                )
            except Exception:
                model = None

            if model is None:
                continue

            predictions = model.get(
                "predictions"
            )

            if not predictions:
                continue

            fitted[name] = model

            model_mae = calc_mae(
                by,
                predictions,
            )
            model_r2 = calc_r2(
                by,
                predictions,
            )

            if model_mae is not None:
                mae_values[name].append(
                    model_mae
                )

            if model_r2 is not None:
                r2_values[name].append(
                    model_r2
                )

        if not fitted:
            continue

        successful += 1

        winner = min(
            fitted,
            key=lambda name: calc_mae(
                by,
                fitted[name]["predictions"],
            ),
        )

        winners[winner] += 1

    models = {}

    for name in MODEL_NAMES:
        models[name] = {
            "winner_count": winners[name],
            "winner_share": (
                winners[name] / successful
                if successful
                else None
            ),
            "r_squared": summarize(
                r2_values[name]
            ),
            "mae": summarize(
                mae_values[name]
            ),
        }

    return {
        "status": "ok",
        "n": n,
        "iterations_requested": iterations,
        "successful_iterations": successful,
        "seed": seed,
        "models": models,
    }


def loocv_model(
    x,
    y,
):
    n = len(x)

    if n < 5:
        return {
            "status": "insufficient_data",
            "n": n,
        }

    errors = {
        name: []
        for name in MODEL_NAMES
    }

    squared_errors = {
        name: []
        for name in MODEL_NAMES
    }

    winners = {
        name: 0
        for name in MODEL_NAMES
    }

    predictions = {
        name: []
        for name in MODEL_NAMES
    }

    for held_out in range(n):
        train_x = [
            value
            for i, value in enumerate(x)
            if i != held_out
        ]

        train_y = [
            value
            for i, value in enumerate(y)
            if i != held_out
        ]

        test_x = x[held_out]
        test_y = y[held_out]

        fold = {}

        for name in MODEL_NAMES:
            try:
                model = fit_model(
                    name,
                    train_x,
                    train_y,
                )
            except Exception:
                model = None

            if model is None:
                continue

            prediction = predict_model(
                name,
                model,
                test_x,
            )

            if prediction is None:
                continue

            error = abs(
                test_y - prediction
            )

            errors[name].append(
                error
            )
            squared_errors[name].append(
                error ** 2
            )
            predictions[name].append(
                prediction
            )

            fold[name] = error

        if fold:
            winner = min(
                fold,
                key=fold.get,
            )
            winners[winner] += 1

    models = {}

    for name in MODEL_NAMES:
        if not errors[name]:
            models[name] = {
                "folds": 0,
                "mae": None,
                "rmse": None,
                "winner_count": 0,
                "winner_share": 0,
                "predictions": [],
            }
            continue

        models[name] = {
            "folds": len(errors[name]),
            "mae": statistics.mean(
                errors[name]
            ),
            "rmse": math.sqrt(
                statistics.mean(
                    squared_errors[name]
                )
            ),
            "winner_count": winners[name],
            "winner_share": (
                winners[name] / n
            ),
            "predictions": predictions[name],
        }

    available = [
        (name, result["mae"])
        for name, result in models.items()
        if result["mae"] is not None
    ]

    preferred = (
        min(
            available,
            key=lambda item: item[1],
        )[0]
        if available
        else None
    )

    return {
        "status": "ok",
        "n": n,
        "models": models,
        "preferred_by_out_of_sample_mae": preferred,
    }


def main():
    source = latest_state_snapshot()
    data = load_json(source)

    definitions = {
        "eg_3_vs_initial_ir": (
            "EG_3",
            "Initial IR",
        ),
        "eg_5_vs_initial_ir": (
            "EG_5",
            "Initial IR",
        ),
        "eg_7d_vs_initial_ir": (
            "EG_7d",
            "Initial IR",
        ),
        "eg_5_vs_initial_reach": (
            "EG_5",
            "Initial Reach",
        ),
        "eg_5_vs_initial_views": (
            "EG_5",
            "Initial Views",
        ),
        "temperature_vs_initial_ir": (
            "Account Temperature",
            "Initial IR",
        ),
        "temperature_vs_initial_reach": (
            "Account Temperature",
            "Initial Reach",
        ),
    }

    results = {}

    print()
    print("=" * 60)
    print("H6 - ROBUSTEZ ESTADÍSTICA")
    print("=" * 60)
    print(f"Fuente: {source.name}")
    print("Bootstrap: 5000 iteraciones")
    print("LOOCV: sí")
    print()

    for pair_name, (predictor, outcome) in definitions.items():
        pairs = (
            data.get("hypothesis_pairs", {})
            .get(pair_name, {})
            .get("pairs", [])
        )

        clean_pairs = [
            pair
            for pair in pairs
            if isinstance(
                pair.get("state_value"),
                (int, float),
            )
            and isinstance(
                pair.get("initial_value"),
                (int, float),
            )
        ]

        x = [
            pair["state_value"]
            for pair in clean_pairs
        ]
        y = [
            pair["initial_value"]
            for pair in clean_pairs
        ]

        bootstrap = bootstrap_model(
            x,
            y,
        )

        loocv = loocv_model(
            x,
            y,
        )

        results[pair_name] = {
            "predictor": predictor,
            "outcome": outcome,
            "n": len(x),
            "pairs": clean_pairs,
            "bootstrap": bootstrap,
            "leave_one_out": loocv,
        }

        print(pair_name)
        print(f"  n = {len(x)}")

        if bootstrap.get("status") == "ok":
            for name in MODEL_NAMES:
                model = bootstrap["models"][name]
                print(
                    f"  {name}: "
                    f"win={model['winner_share']} | "
                    f"R2 CI="
                    f"{model['r_squared']['p025']}.."
                    f"{model['r_squared']['p975']} | "
                    f"MAE CI="
                    f"{model['mae']['p025']}.."
                    f"{model['mae']['p975']}"
                )
        else:
            print("  Bootstrap: insufficient_data")

        preferred = loocv.get(
            "preferred_by_out_of_sample_mae"
        )
        print(
            f"  LOOCV preferido = {preferred}"
        )

        for name in MODEL_NAMES:
            model = loocv.get(
                "models",
                {},
            ).get(name)

            if model and model["mae"] is not None:
                print(
                    f"    {name}: "
                    f"MAE={model['mae']:.4f} | "
                    f"RMSE={model['rmse']:.4f} | "
                    f"wins={model['winner_share']:.2%}"
                )

        print()

    output = {
        "analysis": {
            "created_at": datetime.now().isoformat(),
            "source_snapshot": source.name,
            "bootstrap_iterations": 5000,
            "bootstrap_seed": 20260731,
            "methods": {
                "bootstrap": (
                    "Paired non-parametric bootstrap "
                    "with replacement."
                ),
                "loocv": (
                    "Leave-One-Out Cross-Validation."
                ),
            },
            "warning": (
                "Con n pequeño, cualquier modelo "
                "puede ser inestable. La robustez "
                "debe reevaluarse al crecer la muestra."
            ),
        },
        "results": results,
    }

    ANALYTICS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    output_path = (
        ANALYTICS_DIR
        / f"h6_robustness_{timestamp}.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print(
        "Análisis guardado en:",
        output_path,
    )


if __name__ == "__main__":
    main()