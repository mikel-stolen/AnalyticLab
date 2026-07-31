"""
AnalyticLab - Model Ensemble para H6.

Objetivo
--------
En lugar de elegir un único modelo para la relación entre el estado previo
 de la cuenta y el rendimiento inicial, combina varios modelos candidatos:

    - linear
    - quadratic
    - threshold
    - saturation

La combinación se calcula a partir de evidencia fuera de muestra y estabilidad:

    1. LOOCV MAE       -> precisión fuera de muestra
    2. Bootstrap win    -> frecuencia con la que un modelo gana por MAE
    3. Complejidad      -> penalización suave a modelos más flexibles

Los pesos se normalizan para que:

    sum(w_i) = 1

El ensemble devuelve:

    - predicción combinada
    - predicción de cada modelo
    - pesos
    - desacuerdo entre modelos
    - intervalo de incertidumbre aproximado
    - MAE/RMSE fuera de muestra del ensemble mediante LOOCV

Importante
----------
Este módulo NO afirma que exista una función verdadera concreta. El objetivo
es mantener incertidumbre explícita cuando la evidencia no permite decidir
entre modelos.

Fuente
------
data/processed/instagram/analytics/account_engagement_state_*.json

Salida
------
data/processed/instagram/analytics/model_ensemble_*.json

Uso
---
python model_ensemble.py
"""

from __future__ import annotations

import json
import math
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any


# ============================================================
# Localización del proyecto
# ============================================================


def find_project_root() -> Path:
    current = Path(__file__).resolve()

    for parent in [current.parent, *current.parents]:
        candidate = parent / "data" / "processed" / "instagram"
        if candidate.exists():
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


MODEL_NAMES = (
    "linear",
    "quadratic",
    "threshold",
    "saturation",
)

# Penalización de complejidad. Es deliberadamente suave: no queremos
# eliminar modelos complejos, solo exigirles más evidencia.
COMPLEXITY_PENALTY = {
    "linear": 0.00,
    "quadratic": 0.05,
    "threshold": 0.05,
    "saturation": 0.08,
}


# ============================================================
# Utilidades JSON
# ============================================================


def load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def latest_state_snapshot() -> Path:
    files = sorted(
        ANALYTICS_DIR.glob("account_engagement_state_*.json"),
        key=lambda path: path.stat().st_mtime,
    )

    if not files:
        raise RuntimeError(
            "No se encontraron snapshots account_engagement_state_*.json"
        )

    return files[-1]


# ============================================================
# Modelos: importamos el motor ya construido en H6
# ============================================================


def import_model_functions():
    import sys

    module_dir = Path(__file__).resolve().parent
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))

    try:
        from h6_nonlinear_analysis import (
            fit_linear,
            fit_quadratic,
            fit_threshold,
            fit_saturation,
        )
    except ImportError as exc:
        raise RuntimeError(
            "No se pudo importar h6_nonlinear_analysis.py. "
            "Coloca ambos módulos en el mismo directorio."
        ) from exc

    return {
        "linear": fit_linear,
        "quadratic": fit_quadratic,
        "threshold": fit_threshold,
        "saturation": fit_saturation,
    }


FIT_FUNCTIONS = import_model_functions()


# ============================================================
# Métricas
# ============================================================


def mae(y: list[float], predictions: list[float]) -> float | None:
    if not y:
        return None
    return statistics.mean(
        abs(actual - predicted)
        for actual, predicted in zip(y, predictions)
    )


def rmse(y: list[float], predictions: list[float]) -> float | None:
    if not y:
        return None
    return math.sqrt(
        statistics.mean(
            (actual - predicted) ** 2
            for actual, predicted in zip(y, predictions)
        )
    )


def variance(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    return statistics.pvariance(values)


def stdev(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    return statistics.pstdev(values)


# ============================================================
# Ajuste y predicción
# ============================================================


def fit_model(name: str, x: list[float], y: list[float]):
    function = FIT_FUNCTIONS[name]
    return function(x, y)


def predict_model(name: str, model: dict, x_value: float) -> float | None:
    params = model.get("parameters", {})

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
            * max(x_value - params["x_shift"], 0.0)
        )

        return (
            params["intercept"]
            + params["amplitude"] * transformed
        )

    raise ValueError(name)


# ============================================================
# Datos H6
# ============================================================


def load_pair_group(
    snapshot: Path,
    pair_name: str,
) -> tuple[list[float], list[float], list[dict[str, Any]]]:
    data = load_json(snapshot)

    pairs = (
        data.get("hypothesis_pairs", {})
        .get(pair_name, {})
        .get("pairs", [])
    )

    clean_pairs = [
        pair
        for pair in pairs
        if isinstance(pair.get("state_value"), (int, float))
        and isinstance(pair.get("initial_value"), (int, float))
    ]

    x = [pair["state_value"] for pair in clean_pairs]
    y = [pair["initial_value"] for pair in clean_pairs]

    return x, y, clean_pairs


# ============================================================
# LOOCV para cada modelo + ensemble
# ============================================================


def loocv_model_predictions(
    x: list[float],
    y: list[float],
) -> dict[str, Any]:
    n = len(x)

    if n < 5:
        return {
            "status": "insufficient_data",
            "n": n,
        }

    errors = {name: [] for name in MODEL_NAMES}
    squared_errors = {name: [] for name in MODEL_NAMES}
    predictions = {name: [] for name in MODEL_NAMES}
    winners = {name: 0 for name in MODEL_NAMES}

    for held_out in range(n):
        train_x = [value for index, value in enumerate(x) if index != held_out]
        train_y = [value for index, value in enumerate(y) if index != held_out]

        test_x = x[held_out]
        test_y = y[held_out]

        fold_errors: dict[str, float] = {}

        for name in MODEL_NAMES:
            try:
                model = fit_model(name, train_x, train_y)
            except (ArithmeticError, ValueError, OverflowError):
                model = None

            if model is None:
                continue

            prediction = predict_model(name, model, test_x)

            if prediction is None or not math.isfinite(prediction):
                continue

            error = abs(test_y - prediction)

            errors[name].append(error)
            squared_errors[name].append(error * error)
            predictions[name].append(prediction)
            fold_errors[name] = error

        if fold_errors:
            winner = min(fold_errors, key=fold_errors.get)
            winners[winner] += 1

    model_summary = {}

    for name in MODEL_NAMES:
        model_summary[name] = {
            "folds": len(errors[name]),
            "mae": statistics.mean(errors[name]) if errors[name] else None,
            "rmse": math.sqrt(statistics.mean(squared_errors[name])) if squared_errors[name] else None,
            "winner_count": winners[name],
            "winner_share": winners[name] / n if n else None,
            "predictions": predictions[name],
        }

    return {
        "status": "ok",
        "n": n,
        "models": model_summary,
    }


# ============================================================
# Bootstrap: winner share por modelo
# ============================================================


def load_bootstrap_results(
    snapshot: Path,
    pair_name: str,
) -> dict[str, Any] | None:
    """
    Busca el último h6_robustness que utilice el mismo source snapshot.
    Si no existe, devuelve None y el ensemble utiliza pesos derivados
    de LOOCV solamente.
    """

    files = sorted(
        ANALYTICS_DIR.glob("h6_robustness_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    for path in files:
        try:
            data = load_json(path)
        except (OSError, json.JSONDecodeError):
            continue

        if data.get("analysis", {}).get("source_snapshot") != snapshot.name:
            continue

        result = data.get("results", {}).get(pair_name)
        if result:
            return result.get("bootstrap")

    return None


# ============================================================
# Pesos do ensemble
# ============================================================


def safe_inverse(value: float | None, epsilon: float = 1e-9) -> float:
    if value is None or not math.isfinite(value):
        return 0.0
    return 1.0 / max(value, epsilon)


def calculate_weights(
    model_metrics: dict[str, dict[str, Any]],
    bootstrap: dict[str, Any] | None,
) -> dict[str, float]:
    """
    Combina tres señales:

        1. precisão LOOCV       -> inverse MAE
        2. estabilidade Bootstrap -> winner share
        3. complexidade          -> penalización suave

    Não se usa R² in-sample como fuente principal de peso.
    """

    raw_scores = {}

    for name in MODEL_NAMES:
        metrics = model_metrics[name]

        loocv_mae = metrics.get("mae")
        cv_component = safe_inverse(loocv_mae)

        bootstrap_component = 0.0
        if bootstrap and bootstrap.get("status") == "ok":
            bootstrap_component = (
                bootstrap
                .get("models", {})
                .get(name, {})
                .get("winner_share")
                or 0.0
            )

        complexity_factor = 1.0 - COMPLEXITY_PENALTY[name]

        # Mistura conservadora: 75% evidência de erro fora de amostra,
        # 25% estabilidad bootstrap.
        base = (
            0.75 * cv_component
            + 0.25 * bootstrap_component
        )

        raw_scores[name] = max(
            base * complexity_factor,
            0.0,
        )

    total = sum(raw_scores.values())

    if total <= 0:
        equal_weight = 1.0 / len(MODEL_NAMES)
        return {
            name: equal_weight
            for name in MODEL_NAMES
        }

    return {
        name: raw_scores[name] / total
        for name in MODEL_NAMES
    }


# ============================================================
# Predicción ensemble + incertidumbre
# ============================================================


def ensemble_prediction(
    fitted_models: dict[str, dict],
    weights: dict[str, float],
    x_value: float,
) -> dict[str, Any]:
    predictions = {}

    for name, model in fitted_models.items():
        prediction = predict_model(
            name,
            model,
            x_value,
        )
        if prediction is None or not math.isfinite(prediction):
            continue
        predictions[name] = prediction

    active_weights = {
        name: weights[name]
        for name in predictions
        if weights.get(name, 0.0) > 0
    }

    weight_sum = sum(active_weights.values())

    if weight_sum <= 0:
        active_weights = {
            name: 1.0 / len(predictions)
            for name in predictions
        }
        weight_sum = 1.0

    active_weights = {
        name: value / weight_sum
        for name, value in active_weights.items()
    }

    prediction = sum(
        active_weights[name]
        * predictions[name]
        for name in predictions
    )

    weighted_variance = sum(
        active_weights[name]
        * (
            predictions[name]
            - prediction
        ) ** 2
        for name in predictions
    )

    disagreement = math.sqrt(
        max(weighted_variance, 0.0)
    )

    return {
        "prediction": prediction,
        "model_predictions": predictions,
        "weights": active_weights,
        "model_disagreement_stdev": disagreement,
    }


# ============================================================
# Ensemble LOOCV
# ============================================================


def ensemble_loocv(
    x: list[float],
    y: list[float],
    bootstrap: dict[str, Any] | None,
) -> dict[str, Any]:
    n = len(x)

    if n < 5:
        return {
            "status": "insufficient_data",
            "n": n,
        }

    predictions = []
    actuals = []
    fold_disagreement = []
    fold_weights = []

    for held_out in range(n):
        train_x = [value for index, value in enumerate(x) if index != held_out]
        train_y = [value for index, value in enumerate(y) if index != held_out]

        fitted = {}
        model_metrics = {}

        for name in MODEL_NAMES:
            try:
                model = fit_model(name, train_x, train_y)
            except (ArithmeticError, ValueError, OverflowError):
                model = None

            if model is None:
                continue

            fitted[name] = model
            model_metrics[name] = {
                "mae": model.get("mae"),
            }

        if not fitted:
            continue

        # No utilizamos resultados del punto excluido. Los pesos derivan
        # solo del entrenamiento y del resumen bootstrap histórico.
        weights = calculate_weights(
            model_metrics,
            bootstrap,
        )

        pred = ensemble_prediction(
            fitted,
            weights,
            x[held_out],
        )

        predictions.append(
            pred["prediction"]
        )
        actuals.append(
            y[held_out]
        )
        fold_disagreement.append(
            pred["model_disagreement_stdev"]
        )
        fold_weights.append(
            pred["weights"]
        )

    return {
        "status": "ok",
        "n": n,
        "folds": len(predictions),
        "mae": mae(actuals, predictions),
        "rmse": rmse(actuals, predictions),
        "mean_model_disagreement": (
            statistics.mean(fold_disagreement)
            if fold_disagreement
            else None
        ),
        "median_model_disagreement": (
            statistics.median(fold_disagreement)
            if fold_disagreement
            else None
        ),
        "predictions": predictions,
        "actuals": actuals,
        "fold_weights": fold_weights,
    }


# ============================================================
# Análisis principal de una relación
# ============================================================


def analyze_pair(
    snapshot: Path,
    pair_name: str,
    predictor: str,
    outcome: str,
) -> dict[str, Any]:
    x, y, pairs = load_pair_group(
        snapshot,
        pair_name,
    )

    if len(x) < 5:
        return {
            "pair_name": pair_name,
            "predictor": predictor,
            "outcome": outcome,
            "n": len(x),
            "status": "insufficient_data",
        }

    loocv = loocv_model_predictions(
        x,
        y,
    )

    model_metrics = loocv["models"]
    bootstrap = load_bootstrap_results(
        snapshot,
        pair_name,
    )

    weights = calculate_weights(
        model_metrics,
        bootstrap,
    )

    # Ajuste final usando toda la muestra disponible.
    fitted_models = {}
    for name in MODEL_NAMES:
        try:
            model = fit_model(
                name,
                x,
                y,
            )
        except (ArithmeticError, ValueError, OverflowError):
            model = None

        if model is not None:
            fitted_models[name] = model

    # Calidad de cada modelo final.
    final_model_metrics = {}
    for name, model in fitted_models.items():
        final_model_metrics[name] = {
            "r_squared": model.get("r_squared"),
            "mae_in_sample": model.get("mae"),
        }

    # Ensemble sobre las observaciones observadas.
    ensemble_observed_predictions = []
    observed_disagreement = []

    for value in x:
        pred = ensemble_prediction(
            fitted_models,
            weights,
            value,
        )
        ensemble_observed_predictions.append(
            pred["prediction"]
        )
        observed_disagreement.append(
            pred["model_disagreement_stdev"]
        )

    return {
        "pair_name": pair_name,
        "predictor": predictor,
        "outcome": outcome,
        "n": len(x),
        "pairs": pairs,
        "weights": weights,
        "weight_method": {
            "loocv_mae_share": 0.75,
            "bootstrap_winner_share": 0.25,
            "complexity_penalty": COMPLEXITY_PENALTY,
        },
        "bootstrap": bootstrap,
        "loocv_models": model_metrics,
        "final_models": final_model_metrics,
        "ensemble_loocv": ensemble_loocv(
            x,
            y,
            bootstrap,
        ),
        "ensemble_in_sample": {
            "predictions": ensemble_observed_predictions,
            "mae": mae(
                y,
                ensemble_observed_predictions,
            ),
            "rmse": rmse(
                y,
                ensemble_observed_predictions,
            ),
            "mean_model_disagreement": (
                statistics.mean(
                    observed_disagreement
                )
                if observed_disagreement
                else None
            ),
        },
    }


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    source = latest_state_snapshot()

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
    print("MODEL ENSEMBLE - H6")
    print("=" * 60)
    print()
    print("Fuente:", source.name)
    print()

    for pair_name, (
        predictor,
        outcome,
    ) in definitions.items():
        result = analyze_pair(
            source,
            pair_name,
            predictor,
            outcome,
        )

        results[pair_name] = result

        if result.get("status") == "insufficient_data":
            print(
                f"{pair_name}: insufficient_data "
                f"(n={result['n']})"
            )
            continue

        print(pair_name)
        print(
            f"  n = {result['n']}"
        )

        print("  Pesos:")
        for name in MODEL_NAMES:
            print(
                f"    {name}: "
                f"{result['weights'].get(name, 0.0):.4f}"
            )

        ensemble_cv = result[
            "ensemble_loocv"
        ]

        print(
            "  Ensemble LOOCV: "
            f"MAE={ensemble_cv.get('mae')} | "
            f"RMSE={ensemble_cv.get('rmse')}"
        )

        print(
            "  Model disagreement: "
            f"{ensemble_cv.get('mean_model_disagreement')}"
        )

        print()

    output = {
        "analysis": {
            "created_at": datetime.now().isoformat(),
            "source_snapshot": source.name,
            "models": list(MODEL_NAMES),
            "weighting": {
                "loocv_mae_share": 0.75,
                "bootstrap_winner_share": 0.25,
                "complexity_penalty": COMPLEXITY_PENALTY,
            },
            "ensemble_goal": (
                "Mantener varias hipótesis de forma funcional y repartir "
                "la confianza en lugar de seleccionar obligatoriamente un "
                "único modelo."
            ),
            "uncertainty_definition": (
                "El desacuerdo ponderado entre modelos se conserva como "
                "señal de incertidumbre estructural."
            ),
            "warning": (
                "Con n pequeño, los pesos pueden ser inestables. El ensemble "
                "debe reevaluarse mediante validación walk-forward cuando "
                "la serie temporal tenga suficiente longitud."
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
        / f"model_ensemble_{timestamp}.json"
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

    print()
    print("Análisis guardado en:")
    print(output_path)


if __name__ == "__main__":
    main()