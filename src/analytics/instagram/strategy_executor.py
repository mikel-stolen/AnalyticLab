"""
AnalyticLab - Strategy Executor v0.2

Ejecuta las decisiones del Model Arbitrator.

Mejoras v0.2:

- Respeta pesos del Model Ensemble.
- Mantiene pesos bayesianos en estrategias híbridas.
- Añade trazabilidad de decisión.
- Preparado para futuros módulos:
    - Bayesian avanzado
    - modelos temporales
    - neural models
    - nuevos sistemas de evidencia

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



ROOT = find_project_root()


ANALYTICS_DIR = (
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



MODELS = [
    "linear",
    "quadratic",
    "threshold",
    "saturation",
]



# ============================================================
# Utils
# ============================================================


def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)



def latest_file(pattern):

    files = sorted(
        ANALYTICS_DIR.glob(pattern),
        key=lambda x:x.stat().st_mtime
    )


    if not files:

        raise RuntimeError(
            f"No existe {pattern}"
        )


    return files[-1]



def normalize(weights):

    total = sum(weights.values())


    if total <= 0:

        equal = 1 / len(weights)

        return {
            k: equal
            for k in weights
        }


    return {

        k: v / total

        for k,v in weights.items()

    }



# ============================================================
# Execution logic
# ============================================================


def execute_strategy(
    decision,
    posterior,
    ensemble_weights
):


    strategy = decision["strategy"]



    # --------------------------------------------------------
    # Modelo único
    # --------------------------------------------------------

    if strategy == "single_model":


        model = decision["models"][0]


        return {

            "execution_type":
                "single_model",


            "models":
            {
                model:1.0
            },


            "method":
                f"use_{model}"

        }



    # --------------------------------------------------------
    # Híbrido
    # --------------------------------------------------------

    if strategy == "hybrid":


        selected = {}


        for model in decision["models"]:

            selected[model] = (

                posterior
                .get(
                    model,
                    0
                )

            )


        return {


            "execution_type":
                "hybrid",


            "models":
                normalize(selected),


            "method":
                "bayesian_hybrid"

        }



    # --------------------------------------------------------
    # Ensemble completo
    # --------------------------------------------------------

    return {


        "execution_type":
            "full_ensemble",


        "models":
            normalize(
                ensemble_weights
            ),


        "method":
            "ensemble_weighted_average"

    }



# ============================================================
# MAIN
# ============================================================


def main():


    arbitrator_file = latest_file(
        "model_arbitrator_*.json"
    )


    ensemble_file = latest_file(
        "model_ensemble_*.json"
    )



    arbitrator = load_json(
        arbitrator_file
    )


    ensemble = load_json(
        ensemble_file
    )



    results = {}



    for pair_name,data in (

        arbitrator
        .get(
            "results",
            {}
        )
        .items()

    ):


        decision = data["decision"]


        posterior = data["posterior"]



        ensemble_weights = (

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



        execution = execute_strategy(
            decision,
            posterior,
            ensemble_weights
        )



        results[pair_name] = {


            "decision":
                decision,


            "execution":
                execution,


            "decision_trace":
            {

                "bayesian_winner":

                    max(
                        posterior,
                        key=posterior.get
                    ),


                "bayesian_confidence":

                    max(
                        posterior.values()
                    ),


                "ensemble_weights":

                    ensemble_weights,


                "final_strategy":

                    execution["execution_type"]

            }

        }




    output = {


        "analysis":
        {

            "created_at":
                datetime.now()
                .isoformat(),


            "engine":
                "strategy_executor_v0.2",


            "source":

                {

                "arbitrator":
                    arbitrator_file.name,

                "ensemble":
                    ensemble_file.name

                }

        },


        "results":
            results

    }



    output_path = (

        ANALYTICS_DIR

        /

        (
            "strategy_executor_"

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
    ) as file:


        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False
        )



    print()
    print("="*60)
    print("STRATEGY EXECUTOR v0.2")
    print("="*60)
    print()



    for name,result in results.items():

        print(name)

        print(
            result["execution"]
        )

        print()



    print(
        "Guardado:",
        output_path
    )



if __name__ == "__main__":

    main()