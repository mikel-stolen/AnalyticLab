"""
AnalyticLab - Prediction Engine v1.0

Primer motor de predicción del sistema.

Recibe:
    evidence_context_*.json

Genera:
    prediction_engine_*.json

Arquitectura:

Evidence
    ↓
Prediction
    ↓
Confidence
    ↓
Reasoning

v1

- Media ponderada
- Intervalo
- Confianza
- Explicación
"""

from __future__ import annotations

import json

from pathlib import Path
from datetime import datetime
from typing import Any

def find_project_root() -> Path:

    current = Path(__file__).resolve()

    for parent in [
        current.parent,
        *current.parents
    ]:

        candidate = (
            parent
            /
            "data"
            /
            "processed"
            /
            "instagram"
        )

        if candidate.exists():

            return parent

    raise RuntimeError(
        "No se encontró AnalyticLab"
    )

PROJECT_ROOT = find_project_root()

ANALYTICS_DIR = (

    PROJECT_ROOT

    /

    "data"

    /

    "processed"

    /

    "instagram"

    /

    "analytics"

)

def latest_context_file():

    files = sorted(

        ANALYTICS_DIR.glob(

            "evidence_context_*.json"

        ),

        key=lambda p: p.stat().st_mtime

    )

    if not files:

        raise RuntimeError(

            "No existe evidence_context"

        )

    return files[-1]

def load_json(
        path: Path
):

    with open(

        path,

        "r",

        encoding="utf-8"

    ) as file:

        return json.load(file)

# ============================================================
# Prediction Core
# ============================================================

def extract_predictions(
    context
):

    predictions = {}

    h6 = context["h6"]

    models = h6["models"]

    for model_name, model_data in models.items():

        values = model_data.get(
            "predictions",
            []
        )

        print()
        print(model_name)
        print(values)
        print("MEDIA =", sum(values) / len(values))

        predictions[model_name] = (
            sum(values)
            /
            len(values)
        )

    return predictions

def extract_weights(
    context: dict[str, Any]
):

    ensemble = context["ensemble"]

    return ensemble.get(
        "weights",
        {}
    )

def weighted_prediction(

        predictions: dict[str, float],

        weights: dict[str, float]

):

    total = 0.0

    total_weight = 0.0

    for model, prediction in predictions.items():

        weight = weights.get(
            model,
            0
        )

        total += prediction * weight

        total_weight += weight

    if total_weight == 0:

        return None

    return total / total_weight

def estimate_confidence(
        context: dict[str, Any]
):

    bayesian = context["bayesian"]

    confidence = bayesian.get(
        "posterior_confidence",
        0
    )

    consensus = context[
        "consensus"
    ]

    strength = consensus.get(
        "consensus_strength",
        0
    )

    return round(

        (
            confidence
            +
            strength
        )
        / 2,

        3

    )

def estimate_interval(

        prediction,

        confidence

):

    if prediction is None:

        return None

    uncertainty = (

        1
        -
        confidence

    ) * 10

    return {

        "lower":

            round(
                prediction - uncertainty,
                2
            ),

        "upper":

            round(
                prediction + uncertainty,
                2
            )

    }

def prediction_quality(
        confidence
):

    if confidence >= 0.85:

        return "very_high"

    if confidence >= 0.70:

        return "high"

    if confidence >= 0.50:

        return "medium"

    return "low"



def extract_context(
    data: dict[str, Any]
):

    modules = (
        data
        .get(
            "sources",
            {}
        )
        .get(
            "modules",
            {}
        )
    )

    return {

        "pair_name":
            data.get(
                "pair"
            ),

        "h6":
            modules.get(
                "h6",
                {}
            ),

        "ensemble":
            modules.get(
                "ensemble",
                {}
            ),

        "consensus":
            modules.get(
                "consensus",
                {}
            ),

        "bayesian":
            modules.get(
                "bayesian",
                {}
            )

    }
# ============================================================
# Mathematical Predictors
# ============================================================

import math


def predict_linear(
    parameters,
    x: float
):

    intercept = parameters["intercept"]

    slope = parameters["slope"]

    return intercept + slope * x


def predict_quadratic(
    parameters,
    x: float
):

    intercept = parameters["intercept"]

    linear = parameters["linear"]

    quadratic = parameters["quadratic"]

    return (

        intercept

        +

        linear * x

        +

        quadratic * x * x

    )


def predict_threshold(
    parameters,
    x: float
):

    if x < parameters["threshold"]:

        return parameters["left_mean"]

    else:

        return parameters["right_mean"]


def predict_saturation(
    parameters,
    x: float
):

    a = parameters["intercept"]

    b = parameters["amplitude"]

    k = parameters["k"]

    x0 = parameters["x_shift"]

    return (

        a

        +

        b

        *

        (

            1

            -

            math.exp(

                -k * (x - x0)

            )

        )

    )


def predict_model(

    model_name: str,

    parameters,

    x: float

):

    if model_name == "linear":

        return predict_linear(
            parameters,
            x
        )

    if model_name == "quadratic":

        return predict_quadratic(
            parameters,
            x
        )

    if model_name == "threshold":

        return predict_threshold(
            parameters,
            x
        )

    if model_name == "saturation":

        return predict_saturation(
            parameters,
            x
        )

    raise ValueError(
        f"Modelo desconocido: {model_name}"
    )
def main():

    source = latest_context_file()

    data = load_json(
        source
    )

    context = extract_context(
        data
    )

    predictions = extract_predictions(
        context
    )

    weights = extract_weights(
        context
    )

    prediction = weighted_prediction(

        predictions,

        weights

    )

    confidence = estimate_confidence(
        context
    )

    interval = estimate_interval(

        prediction,

        confidence

    )

    quality = prediction_quality(
        confidence
    )
    h6 = context["h6"]

    models = h6["models"]

    print()

    print("=" * 60)

    print("PRUEBA MODELOS")

    print("=" * 60)

    x = 17

    for name, model in models.items():
        prediction = predict_model(

            name,

            model["parameters"],

            x

        )

        print(

            f"{name:12}",

            round(prediction, 3)

        )
    print()
    print("ENSEMBLE")
    print(context["ensemble"])

    print()
    print("CONSENSUS")
    print(context["consensus"])

    print()
    print("BAYESIAN")
    print(context["bayesian"])
    print()

    print("=" * 60)

    print(
        "Prediction Engine v1"
    )

    print("=" * 60)

    print()

    print(

        "Contexto cargado correctamente."

    )

    print()

    print(

        "Relación:",

        context["pair_name"]

    )

    print()

    print(

        "H6:",

        bool(
            context["h6"]
        )

    )

    print(

        "Ensemble:",

        bool(
            context["ensemble"]
        )

    )

    print(

        "Consensus:",

        bool(
            context["consensus"]
        )

    )

    print(

        "Bayesian:",

        bool(
            context["bayesian"]
        )

    )
    print()

    print("Predicciones medias")

    for model, value in predictions.items():
        print(

            f"{model:12}",

            round(value, 2)

        )

    print()

    print(

        "Predicción final:",

        round(prediction, 2)

    )

    print(

        "Confianza:",

        confidence

    )

    print(

        "Intervalo:",

        interval

    )

    print(

        "Calidad:",

        quality

    )

if __name__ == "__main__":

    main()


