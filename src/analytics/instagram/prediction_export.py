"""
============================================================
AnalyticLab - Prediction Export v1.0
============================================================

Exportador de resultados predictivos.

Responsabilidades
-----------------
1. Ejecutar Prediction Engine.
2. Preparar estructura persistente.
3. Exportar predicción en formato JSON.

============================================================
"""


from pathlib import Path
from datetime import datetime
import json


from prediction_engine_v2 import run_prediction



# ============================================================
# Paths
# ============================================================


def export_directory():

    current = Path(__file__).resolve()

    project_root = current.parents[3]

    directory = (

        project_root

        / "data"

        / "processed"

        / "instagram"

        / "predictions"

    )

    directory.mkdir(

        parents=True,

        exist_ok=True

    )

    return directory



# ============================================================
# Export
# ============================================================


def prepare_export(result):

    """

    Reduce el resultado del engine
    a una estructura preparada
    para almacenamiento.

    """

    reasoning = result["reasoning"]

    bayesian = result["bayesian"]


    return {

        "timestamp":
            result["timestamp"],


        "relation":
            result["relation"],


        "predictor_value":
            result["predictor_value"],


        "prediction": {

            "ensemble":
                result["ensemble"]["prediction"]

        },


        "models":
            result["models"],


        "winner": {

            "model":
                reasoning["bayesian"]["winner"],


            "probability":
                reasoning["bayesian"]["winner_probability"]

        },


        "confidence":
            bayesian["confidence"],


        "evidence_state":
            bayesian["evidence_state"]

    }



def export_prediction(result):


    directory = export_directory()


    timestamp = datetime.now().strftime(

        "%Y%m%d_%H%M%S"

    )


    filename = (

        f"prediction_{timestamp}.json"

    )


    path = directory / filename


    data = prepare_export(result)


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


    return path



# ============================================================
# Main
# ============================================================


def main():

    result = run_prediction()


    path = export_prediction(result)


    print(

        f"Prediction exported: {path}"

    )



if __name__ == "__main__":

    main()