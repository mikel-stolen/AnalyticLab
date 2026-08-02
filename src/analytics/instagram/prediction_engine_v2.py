"""
============================================================
AnalyticLab - Prediction Engine v2.0
============================================================

Motor de inferencia del sistema.

Responsabilidades
-----------------
1. Cargar el contexto generado por Evidence Engine.
2. Evaluar los modelos matemáticos entrenados.
3. Combinar las predicciones mediante Ensemble.
4. Estimar la confianza mediante Bayesian Engine.
5. Calcular el intervalo de incertidumbre.
6. Exportar el resultado final.

Arquitectura

Evidence
    ↓
Prediction
    ↓
Ensemble
    ↓
Bayesian
    ↓
Confidence
    ↓
Reasoning

============================================================
"""

from __future__ import annotations

import json
import math

from pathlib import Path
from datetime import datetime
from typing import Any

# ============================================================
# Project
# ============================================================

def find_project_root() -> Path:

    current = Path(__file__).resolve()

    for parent in [current.parent, *current.parents]:

        candidate = (
            parent
            / "data"
            / "processed"
            / "instagram"
        )

        if candidate.exists():
            return parent

    raise RuntimeError(
        "No se encontró AnalyticLab"
    )


PROJECT_ROOT = find_project_root()

ANALYTICS_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "instagram"
    / "analytics"
)

# ============================================================
# Load Context
# ============================================================

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


def load_json(path: Path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def extract_context(data):

    modules = (

        data

        .get("sources", {})

        .get("modules", {})

    )

    return {

        "pair_name":
            data.get("pair"),

        "h6":
            modules.get("h6", {}),

        "ensemble":
            modules.get("ensemble", {}),

        "consensus":
            modules.get("consensus", {}),

        "bayesian":
            modules.get("bayesian", {})

    }

# ============================================================
# Mathematical Models
# ============================================================

# ------------------------------------------------------------
# Linear
# ------------------------------------------------------------

def predict_linear(
    parameters,
    x: float
):

    return (

        parameters["intercept"]

        +

        parameters["slope"] * x

    )


# ------------------------------------------------------------
# Quadratic
# ------------------------------------------------------------

def predict_quadratic(
    parameters,
    x: float
):

    return (

        parameters["intercept"]

        +

        parameters["linear"] * x

        +

        parameters["quadratic"] * x * x

    )


# ------------------------------------------------------------
# Threshold
# ------------------------------------------------------------

def predict_threshold(
    parameters,
    x: float
):

    if x < parameters["threshold"]:

        return parameters["left_mean"]

    return parameters["right_mean"]


# ------------------------------------------------------------
# Saturation
# ------------------------------------------------------------

def predict_saturation(
    parameters,
    x: float
):

    return (

        parameters["intercept"]

        +

        parameters["amplitude"]

        *

        (

            1

            -

            math.exp(

                -parameters["k"]

                *

                (

                    x

                    -

                    parameters["x_shift"]

                )

            )

        )

    )


# ------------------------------------------------------------
# Dispatcher
# ------------------------------------------------------------

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

# ============================================================
# Bayesian Confidence
# ============================================================

def posterior_probabilities(
    context
):

    return (

        context["bayesian"]

        .get(

            "posterior_probabilities",

            {}

        )

    )

def posterior_confidence(
    context
):

    return (

        context["bayesian"]

        .get(

            "posterior_confidence",

            0

        )

    )

def evidence_state(
    context
):

    return (

        context["bayesian"]

        .get(

            "evidence_state",

            "unknown"

        )

    )

# ============================================================
# Reasoning Engine
# ============================================================

def reasoning_models(

    predictions

):

    highest = max(
        predictions.values()
    )

    lowest = min(
        predictions.values()
    )

    spread = highest - lowest

    return {

        "spread": round(
            spread,
            3
        ),

        "agreement":

            spread < 2,

        "highest":

            highest,

        "lowest":

            lowest

    }

def reasoning_consensus(

    context

):

    decision = (

        context["consensus"]

        .get(
            "decision",
            {}
        )

    )

    return {

        "strategy":

            decision.get(
                "strategy"
            ),

        "reason":

            decision.get(
                "reason"
            ),

        "strength":

            decision.get(
                "consensus_strength"
            )

    }

def reasoning_bayesian(

    posterior,

    confidence,

    evidence

):

    winner = max(

        posterior,

        key=posterior.get

    )

    return {

        "winner":

            winner,

        "winner_probability":

            posterior[winner],

        "confidence":

            confidence,

        "evidence":

            evidence

    }

def build_reasoning(

    context,

    predictions,

    posterior,

    confidence,

    evidence

):

    return {

        "models":

            reasoning_models(
                predictions
            ),

        "consensus":

            reasoning_consensus(
                context
            ),

        "bayesian":

            reasoning_bayesian(

                posterior,

                confidence,

                evidence

            )

    }

# ============================================================
# Prediction Core
# ============================================================

# ------------------------------------------------------------
# Predict all models
# ------------------------------------------------------------

def predict_all_models(

    context,

    predictor_value: float

):

    predictions = {}

    models = (

        context["h6"]

        .get(

            "models",

            {}

        )

    )

    for model_name, model_data in models.items():

        prediction = predict_model(

            model_name,

            model_data["parameters"],

            predictor_value

        )

        predictions[model_name] = prediction

    return predictions

# ------------------------------------------------------------
# Ensemble Prediction
# ------------------------------------------------------------

def ensemble_prediction(

    predictions,

    weights

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

        raise RuntimeError(
            "No existen pesos del ensemble."
        )

    return total / total_weight

def ensemble_weights(
    context
):

    return (

        context["ensemble"]

        .get(
            "weights",
            {}
        )

    )

# ============================================================
# Export
# ============================================================

# export_prediction()

# ============================================================
# MAIN
# ============================================================

# ============================================================
# MAIN / EXECUTION
# ============================================================


def run_prediction():

    """
    Ejecuta el motor predictivo completo.

    Devuelve un diccionario con:
    - relación analizada
    - predicciones individuales
    - ensemble final
    - información bayesiana
    - reasoning
    """

    source = latest_context_file()

    data = load_json(source)

    context = extract_context(data)


    # --------------------------------------------------------
    # Predictor value
    # --------------------------------------------------------

    predictor_value = 17


    # --------------------------------------------------------
    # Model predictions
    # --------------------------------------------------------

    predictions = predict_all_models(

        context,

        predictor_value

    )


    # --------------------------------------------------------
    # Ensemble
    # --------------------------------------------------------

    weights = ensemble_weights(

        context

    )

    final_prediction = ensemble_prediction(

        predictions,

        weights

    )


    # --------------------------------------------------------
    # Bayesian
    # --------------------------------------------------------

    posterior = posterior_probabilities(

        context

    )

    confidence = posterior_confidence(

        context

    )

    state = evidence_state(

        context

    )


    # --------------------------------------------------------
    # Reasoning
    # --------------------------------------------------------

    reasoning = build_reasoning(

        context,

        predictions,

        posterior,

        confidence,

        state

    )


    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    return {

        "timestamp":
            datetime.now().isoformat(),

        "relation":
            context["pair_name"],

        "predictor_value":
            predictor_value,

        "models":
            predictions,

        "ensemble": {

            "prediction":
                final_prediction,

            "weights":
                weights

        },

        "bayesian": {

            "posterior":
                posterior,

            "confidence":
                confidence,

            "evidence_state":
                state

        },

        "reasoning":
            reasoning

    }



def main():

    """
    Punto de entrada para pruebas manuales.
    """

    result = run_prediction()

    print(result)



if __name__ == "__main__":

    main()