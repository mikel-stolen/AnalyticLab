"""
AnalyticLab - Calibration Engine v0.1

Aprende del rendimiento histórico del motor.

Compara:

Predicción
    vs
Resultado real

y genera memoria de precisión.

"""


from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
import statistics



# ============================================================
# Paths
# ============================================================


def find_root():

    current=Path(__file__).resolve()

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
        "No encontrado"
    )



ROOT=find_root()


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



MEMORY_FILE=(
    ANALYTICS_DIR
    /
    "calibration_memory.json"
)



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



def save_json(path,data):

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )



def latest_prediction():

    files=sorted(

        ANALYTICS_DIR.glob(
            "strategy_predictor_*.json"
        ),

        key=lambda x:x.stat().st_mtime

    )


    if not files:
        return None


    return load_json(
        files[-1]
    )



# ============================================================
# Memory
# ============================================================


def load_memory():

    if MEMORY_FILE.exists():

        return load_json(
            MEMORY_FILE
        )


    return {

        "created_at":
            datetime.now()
            .isoformat(),

        "models":{}

    }



# ============================================================
# Calibration
# ============================================================


def calibrate():

    prediction_file=latest_prediction()


    if prediction_file is None:

        return None



    memory=load_memory()



    # En esta fase esperamos
    # que los resultados reales
    # se añadan manualmente/API


    for pair,data in (

        prediction_file["results"]
        .items()

    ):


        prediction=(

            data["prediction"]
            ["prediction"]

        )


        memory.setdefault(
            "pairs",
            {}
        )


        memory["pairs"].setdefault(
            pair,
            {

            "samples":0,

            "errors":[]

            }

        )


        # todavía no hay real
        # se deja preparado


    memory["updated_at"]=(
        datetime.now()
        .isoformat()
    )


    save_json(
        MEMORY_FILE,
        memory
    )


    return memory



# ============================================================
# MAIN
# ============================================================


def main():

    result=calibrate()


    print()
    print("="*60)
    print("CALIBRATION ENGINE v0.1")
    print("="*60)
    print()


    if result:

        print(
            "Memoria actualizada:"
        )

        print(
            MEMORY_FILE
        )

    else:

        print(
            "No hay predicciones"
        )



if __name__=="__main__":

    main()