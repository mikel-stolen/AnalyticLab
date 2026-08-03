"""
============================================================
AnalyticLab - Prediction Registry v1.0
============================================================

Sistema histórico de predicciones.

Responsabilidades
-----------------
1. Cargar predicción actual.
2. Mantener histórico.
3. Registrar experimentos.

============================================================
"""


from pathlib import Path
import sys
import json
from datetime import datetime
import uuid


CURRENT_DIR = Path(__file__).resolve().parent

INSTAGRAM_DIR = CURRENT_DIR.parent

sys.path.append(str(INSTAGRAM_DIR))

REGISTRY_FILE = (
    Path(__file__)
    .resolve()
    .parents[4]
    / "data"
    / "processed"
    / "instagram"
    / "analytics"
    / "prediction_registry.json"
)
print("REGISTRY FILE:", REGISTRY_FILE)
from prediction_engine_v2 import run_prediction



# ===========================================================
# Paths
# ============================================================


def registry_path():

    current = Path(__file__).resolve()

    project_root = current.parents[3]


    directory = (

        project_root

        / "data"

        / "processed"

        / "instagram"

        / "registry"

    )


    directory.mkdir(

        parents=True,

        exist_ok=True

    )


    return directory / "predictions_registry.json"



# ============================================================
# Registry
# ============================================================


def load_registry():

    if not REGISTRY_FILE.exists():
        return {
            "created_at": datetime.now().isoformat(),
            "predictions": []
        }

    try:
        with open(
            REGISTRY_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except json.JSONDecodeError:

        print(
            "[WARN] Registry vacío/corrupto. "
            "Regenerando."
        )

        return {
            "created_at": datetime.now().isoformat(),
            "predictions": []
        }



def save_registry(registry):

    temp_file = REGISTRY_FILE.with_suffix(".tmp")

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as file:
        def json_serializer(obj):

            if isinstance(obj, set):
                return list(obj)

            if obj is Ellipsis:
                return None

            raise TypeError(
                f"Objeto no serializable: {type(obj)} -> {obj}"
            )

        json.dump(
            registry,
            file,
            indent=4,
            default=json_serializer
        )

    temp_file.replace(REGISTRY_FILE)



def register_prediction(result):

    registry = load_registry()

    entry = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now().isoformat(),
        "pair": result.get("pair", "unknown"),
        "metric": result.get("metric", "unknown"),
        "strategy": result.get("strategy"),
        "prediction": result.get("prediction"),
        "uncertainty": result.get("uncertainty"),
        "models": result.get("models", {}),
        "status": "waiting_result"
    }

    registry["predictions"].append(entry)

    registry["updated_at"] = datetime.now().isoformat()

    save_registry(registry)

    return entry



# ============================================================
# Main
# ============================================================


def main():

    result = run_prediction()


    entry = register_prediction(result)


    print(

        "Prediction registered:"

    )


    print(entry)



if __name__ == "__main__":

    main()