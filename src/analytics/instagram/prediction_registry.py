"""
AnalyticLab - Prediction Registry v0.2

Sistema de registro experimental.

Guarda cada predicción como una entidad
independiente preparada para:

    predicción
        |
        v
    publicación real
        |
        v
    calibración

"""

from __future__ import annotations

import json

from datetime import datetime
from pathlib import Path



# ============================================================
# Paths
# ============================================================


def find_root():

    current = Path(__file__).resolve()

    for parent in [
        current.parent,
        *current.parents
    ]:

        if (
            parent
            /
            "data"
            /
            "processed"
            /
            "instagram"
        ).exists():

            return parent

    raise RuntimeError(
        "No se encontró AnalyticLab"
    )



ROOT = find_root()


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



REGISTRY_FILE = (

    ANALYTICS_DIR
    /
    "prediction_registry.json"

)



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



def save_json(
    path,
    data
):

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )



def latest_prediction():

    files = sorted(

        ANALYTICS_DIR.glob(
            "strategy_predictor_*.json"
        ),

        key=lambda x:x.stat().st_mtime

    )


    if not files:

        raise RuntimeError(
            "No existe strategy_predictor"
        )


    return load_json(
        files[-1]
    )



# ============================================================
# Registry
# ============================================================


def load_registry():

    if REGISTRY_FILE.exists():

        return load_json(
            REGISTRY_FILE
        )


    return {

        "created_at":
            datetime.now()
            .isoformat(),

        "next_id":
            1,

        "predictions":[]

    }



def generate_id(
    registry
):

    value = registry["next_id"]

    registry["next_id"] += 1


    return (
        f"pred_{value:06d}"
    )



def exists_prediction(
    registry,
    pair,
    prediction
):

    for item in registry["predictions"]:

        if (

            item["pair"] == pair

            and

            item["prediction"]
            ==
            prediction

        ):

            return True


    return False



def register_predictions(
    prediction_data
):

    registry = load_registry()


    created = 0



    for pair_name,result in (

        prediction_data["results"]
        .items()

    ):


        prediction = result["prediction"]



        value = prediction["prediction"]



        if exists_prediction(

            registry,

            pair_name,

            value

        ):

            continue



        entry = {


            "id":
                generate_id(
                    registry
                ),



            "created_at":
                datetime.now()
                .isoformat(),



            "pair":
                pair_name,



            "content":
            {

                "type":
                    "unknown",

                "id":
                    None,

                "published_at":
                    None

            },



            "prediction":
            {

                "value":
                    value,


                "uncertainty":
                    prediction["uncertainty"]

            },



            "strategy":
            {

                "method":
                    prediction["method"],


                "models":
                    prediction["weights"]

            },



            "learning":

            {

                "status":
                    "waiting_result",


                "actual":
                    None,


                "error":
                    None

            }

        }



        registry["predictions"].append(
            entry
        )


        created += 1



    registry["updated_at"] = (
        datetime.now()
        .isoformat()
    )



    save_json(
        REGISTRY_FILE,
        registry
    )


    return registry, created



# ============================================================
# MAIN
# ============================================================


def main():

    prediction_data = latest_prediction()


    registry, created = register_predictions(
        prediction_data
    )


    print()

    print("="*60)

    print(
        "PREDICTION REGISTRY v0.2"
    )

    print("="*60)

    print()


    print(
        "Nuevas predicciones:",
        created
    )


    print(
        "Total histórico:",
        len(
            registry["predictions"]
        )
    )


    print()

    print(
        "Guardado:",
        REGISTRY_FILE
    )



if __name__ == "__main__":

    main()