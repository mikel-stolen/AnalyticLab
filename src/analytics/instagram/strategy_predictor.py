"""
AnalyticLab - Strategy Predictor v0.2

Transforma la estrategia decidida por el motor
en una predicción ejecutable.

Flujo:

    model_ensemble
          |
          v
    reconstrucción modelos H6
          |
          v
    strategy_executor
          |
          v
    predicción final


Soporta:

    single_model
    hybrid
    full_ensemble


"""

from __future__ import annotations

import json
import math
import sys

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



# ============================================================
# Import H6 models
# ============================================================


def import_models():

    module_dir = Path(__file__).resolve().parent

    if str(module_dir) not in sys.path:
        sys.path.insert(
            0,
            str(module_dir)
        )


    from h6_nonlinear_analysis import (

        fit_linear,
        fit_quadratic,
        fit_threshold,
        fit_saturation,

    )


    return {

        "linear":
            fit_linear,

        "quadratic":
            fit_quadratic,

        "threshold":
            fit_threshold,

        "saturation":
            fit_saturation,

    }



FIT_FUNCTIONS = import_models()



# ============================================================
# Utils
# ============================================================


def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)



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



# ============================================================
# Reconstrucción modelos
# ============================================================


def rebuild_models(
    pairs
):

    x=[
        p["state_value"]
        for p in pairs
    ]

    y=[
        p["initial_value"]
        for p in pairs
    ]


    models={}


    for name,function in FIT_FUNCTIONS.items():

        try:

            models[name]=function(
                x,
                y
            )

        except (
            ArithmeticError,
            ValueError,
            OverflowError
        ):

            continue


    return models



# ============================================================
# Predicción individual
# ============================================================


def predict_model(
    name,
    model,
    x
):

    params=model["parameters"]



    if name=="linear":

        return (
            params["intercept"]
            +
            params["slope"]*x
        )



    if name=="quadratic":

        return (

            params["intercept"]

            +

            params["linear"]*x

            +

            params["quadratic"]*x*x

        )



    if name=="threshold":

        if x <= params["threshold"]:

            return params["left_mean"]

        return params["right_mean"]




    if name=="saturation":


        transformed=(

            1-

            math.exp(

                -params["k"]

                *

                max(
                    x-params["x_shift"],
                    0
                )

            )

        )


        return (

            params["intercept"]

            +

            params["amplitude"]
            *
            transformed

        )



    return None



# ============================================================
# Ejecutar estrategia
# ============================================================


def run_prediction(

    execution,

    models,

    x

):


    predictions={}


    for name in execution["models"]:


        if name not in models:
            continue


        value=predict_model(

            name,

            models[name],

            x

        )


        if value is not None:

            predictions[name]=value



    weights=execution["models"]



    final_prediction=sum(

        weights[name]
        *
        predictions[name]

        for name in predictions

    )



    variance=sum(

        weights[name]

        *

        (
            predictions[name]
            -
            final_prediction
        )**2

        for name in predictions

    )


    uncertainty=math.sqrt(
        max(
            variance,
            0
        )
    )



    return {

        "prediction":
            final_prediction,


        "uncertainty":
            uncertainty,


        "individual_predictions":
            predictions,


        "weights":
            weights,


        "method":
            execution["method"]

    }



# ============================================================
# MAIN
# ============================================================


def main():

    executor_file=latest_file(
        "strategy_executor_*.json"
    )


    ensemble_file=latest_file(
        "model_ensemble_*.json"
    )


    executor=load_json(
        executor_file
    )


    ensemble=load_json(
        ensemble_file
    )



    results={}



    for pair_name,data in (

        executor["results"]
        .items()

    ):


        ensemble_result=(

            ensemble["results"]
            [pair_name]

        )


        pairs=ensemble_result["pairs"]



        models=rebuild_models(
            pairs
        )



        last_state=pairs[-1]["state_value"]



        prediction=run_prediction(

            data["execution"],

            models,

            last_state

        )



        results[pair_name]={

            "prediction_point":
            {

                "state_value":
                    last_state,

                "source":
                    "latest_observation"

            },


            "execution":
                data["execution"],


            "prediction":
                prediction

        }




    output={


        "analysis":

        {

            "created_at":
                datetime.now()
                .isoformat(),


            "engine":
                "strategy_predictor_v0.2",


            "executor_source":
                executor_file.name


        },


        "results":
            results

    }



    output_path=(

        ANALYTICS_DIR

        /

        (

        "strategy_predictor_"

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
    print("STRATEGY PREDICTOR v0.2")
    print("="*60)
    print()


    for name,result in results.items():

        print(name)

        print(
            result["prediction"]
        )

        print()



    print(
        "Guardado:",
        output_path
    )



if __name__=="__main__":

    main()