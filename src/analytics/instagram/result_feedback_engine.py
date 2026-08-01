"""
AnalyticLab - Result Feedback Engine v0.1

Primer módulo de aprendizaje.

Compara:

predicción realizada
vs
resultado real

y genera memoria para calibración.

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


MEMORY_FILE = (

    ANALYTICS_DIR
    /
    "calibration_memory.json"

)
FEEDBACK_FILE = (
    ANALYTICS_DIR
    /
    "feedback_input.json"
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



# ============================================================
# Calibration Memory
# ============================================================


def load_memory():

    if MEMORY_FILE.exists():

        memory = load_json(
            MEMORY_FILE
        )

        if "results" not in memory:
            memory["results"] = []

        return memory


    return {

        "created_at":
            datetime.now()
            .isoformat(),

        "results": []

    }



# ============================================================
# Feedback
# ============================================================


def calculate_error(
    prediction,
    actual
):

    absolute = abs(
        actual - prediction
    )


    relative = (

        absolute / actual

        if actual != 0

        else None

    )


    return {

        "absolute_error":
            absolute,

        "relative_error":
            relative

    }



def apply_feedback(
    prediction_id,
    actual
):

    registry = load_json(
        REGISTRY_FILE
    )


    memory = load_memory()


    updated = False



    for item in registry["predictions"]:


        if item["id"] != prediction_id:

            continue



        if item.get("learning", {}).get("status") == "completed":

            return False



        prediction = item["prediction"]


        error = calculate_error(
            prediction,
            actual
        )


        item["learning"] = {

            "status":
                "completed",

            "actual":
                actual,

            "error":
                error

        }


        memory["results"].append({

            "prediction_id":
                prediction_id,

            "pair":
                item["pair"],

            "prediction":
                prediction,

            "actual":
                actual,

            "error":
                error,

            "timestamp":
                datetime.now()
                .isoformat()

        })


        updated = True



    if updated:

        save_json(
            REGISTRY_FILE,
            registry
        )


        memory["updated_at"] = (
            datetime.now()
            .isoformat()
        )


        save_json(
            MEMORY_FILE,
            memory
        )


    return updated



# ============================================================
# MAIN TEST
# ============================================================

def load_feedback():

    if not FEEDBACK_FILE.exists():

        raise RuntimeError(
            "No existe feedback_input.json"
        )

    return load_json(
        FEEDBACK_FILE
    )



def main():

    print()

    print("="*60)
    print(
        "RESULT FEEDBACK ENGINE v0.2"
    )
    print("="*60)

    print()


    feedback = load_feedback()


    prediction_id = (
        feedback["prediction_id"]
    )

    actual = (
        feedback["actual_value"]
    )


    print(
        "Aplicando feedback:"
    )

    print(
        "ID:",
        prediction_id
    )

    print(
        "Resultado real:",
        actual
    )


    success = apply_feedback(
        prediction_id,
        actual
    )


    if success:

        print()

        print(
            "Feedback aplicado correctamente"
        )

        print(
            "Memoria de calibración actualizada"
        )

    else:

        print()

        print(
            "No se pudo aplicar feedback"
        )



if __name__ == "__main__":

    main()