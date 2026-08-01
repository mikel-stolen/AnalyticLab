"""
AnalyticLab - Model Arbitrator v0.1

Capa de decisión del motor.

Recibe:

    - model_ensemble
    - bayesian_engine

Decide:

    SINGLE_MODEL
    HYBRID
    FULL_ENSEMBLE


No entrena modelos.
No predice.

Decide estrategia.
"""


from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path



# ============================================================
# Localización
# ============================================================


def find_project_root():

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



ROOT=find_project_root()



ANALYTICS_DIR=(
    ROOT
    /
    "data"
    /
    "processed"
    /
    "instagram"
    /
    "analytics"
)



MODELS=[
    "linear",
    "quadratic",
    "threshold",
    "saturation"
]



# ============================================================
# Utilidades
# ============================================================


def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)



def latest_file(pattern):

    files=sorted(

        ANALYTICS_DIR.glob(pattern),

        key=lambda x:x.stat().st_mtime

    )

    if not files:
        raise RuntimeError(
            f"No existe {pattern}"
        )

    return files[-1]



# ============================================================
# Decision engine
# ============================================================


def calculate_margin(
    posterior
):

    ordered=sorted(
        posterior.items(),
        key=lambda x:x[1],
        reverse=True
    )


    winner=ordered[0]

    second=ordered[1]


    return {

        "winner":
            winner[0],

        "confidence":
            winner[1],

        "runner_up":
            second[0],

        "runner_confidence":
            second[1],

        "margin":
            winner[1]-second[1]

    }



def decide_strategy(
    posterior,
    ensemble_weights
):


    analysis=calculate_margin(
        posterior
    )


    confidence=analysis["confidence"]

    margin=analysis["margin"]



    if (
        confidence >=0.70
        and
        margin >=0.30
    ):

        return {

            "strategy":
                "single_model",

            "models":
                [
                    analysis["winner"]
                ],

            "reason":
                "Existe dominancia clara"

        }



    if (
        confidence >=0.40
        and
        margin >=0.10
    ):


        return {

            "strategy":
                "hybrid",

            "models":
                [
                    analysis["winner"],
                    analysis["runner_up"]
                ],

            "reason":
                "Existe ventaja parcial pero no suficiente"

        }



    return {

        "strategy":
            "full_ensemble",

        "models":
            MODELS,

        "reason":
            "No existe separación suficiente"

    }



# ============================================================
# MAIN
# ============================================================


def main():


    bayes_file=latest_file(
        "bayesian_engine_*.json"
    )


    ensemble_file=latest_file(
        "model_ensemble_*.json"
    )


    bayes=load_json(
        bayes_file
    )


    ensemble=load_json(
        ensemble_file
    )



    results={}



    for pair_name,bayes_result in (

        bayes
        .get(
            "results",
            {}
        )
        .items()

    ):


        posterior=(
            bayes_result
            [
                "posterior_probabilities"
            ]
        )


        ensemble_weights=(

            ensemble
            .get(
                "results",
                {}
            )
            .get(
                pair_name,
                {}
            )
            .get(
                "weights",
                {}
            )

        )



        decision=decide_strategy(
            posterior,
            ensemble_weights
        )



        results[pair_name]={

            "posterior":
                posterior,

            "analysis":
                calculate_margin(
                    posterior
                ),

            "decision":
                decision

        }



    output={


        "analysis":{

            "created_at":
                datetime.now()
                .isoformat(),

            "engine":
                "model_arbitrator_v0.1",

            "purpose":
                "Seleccionar estrategia óptima"

        },


        "results":
            results

    }



    output_path=(

        ANALYTICS_DIR

        /

        (
        "model_arbitrator_"

        +

        datetime.now()
        .strftime(
            "%Y%m%d_%H%M%S"
        )

        +

        ".json"
        )

    )



    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            indent=4,
            ensure_ascii=False
        )



    print()
    print("="*60)
    print("MODEL ARBITRATOR v0.1")
    print("="*60)
    print()



    for name,result in results.items():

        print(name)

        print(
            result["decision"]
        )

        print()



    print(
        "Guardado:",
        output_path
    )



if __name__=="__main__":
    main()