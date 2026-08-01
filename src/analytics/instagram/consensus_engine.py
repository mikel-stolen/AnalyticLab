"""
AnalyticLab - Consensus Engine v0.2

Capa de decisión superior al sistema de modelos.

Decide si la evidencia recomienda:

    - single_model
    - ensemble
    - conditional (futuro)

No entrena modelos.
No modifica H6.

Evolución:
v0.1 -> decisión básica
v0.2 -> diagnóstico de consenso

Preparado para:
    - Bayesian models
    - probabilistic models
    - ML models
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any


# ============================================================
# Localización
# ============================================================


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
        "No se pudo localizar AnalyticLab"
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


# ============================================================
# Configuración
# ============================================================


DOMINANCE_THRESHOLD = 0.60

AMBIGUITY_MARGIN = 0.15


# ============================================================
# Utilidades
# ============================================================


def load_json(path: Path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)



def latest_ensemble_file():

    files = sorted(
        ANALYTICS_DIR.glob(
            "model_ensemble_*.json"
        ),
        key=lambda p:p.stat().st_mtime
    )

    if not files:

        raise RuntimeError(
            "No hay resultados del ensemble"
        )

    return files[-1]


# ============================================================
# Información del consenso
# ============================================================


def entropy(
    values:list[float]
):

    clean = [
        x for x in values
        if x > 0
    ]

    if not clean:
        return 0


    return -sum(
        x * math.log(x)
        for x in clean
    )



def normalized_entropy(
    weights:dict[str,float]
):

    values = list(
        weights.values()
    )


    if len(values)<=1:

        return 0


    current = entropy(values)

    maximum = math.log(
        len(values)
    )


    if maximum == 0:

        return 0


    return current / maximum



def model_dominance(
    weights:dict[str,float]
):

    if not weights:

        return 0


    ordered = sorted(
        weights.values(),
        reverse=True
    )


    if len(ordered)==1:

        return ordered[0]


    return (
        ordered[0]
        -
        ordered[1]
    )



def consensus_strength(
    weights:dict[str,float]
):

    """
    Fuerza de la decisión de consenso.

    Si los modelos están muy repartidos:
    aumenta la confianza en usar ensemble.
    """

    ent = normalized_entropy(
        weights
    )


    return round(
        ent,
        4
    )



def evidence_state(
    dominance:float,
    strategy:str
):

    if strategy == "single_model":

        return "model_dominance"


    if dominance < 0.10:

        return "high_model_uncertainty"


    return "stable_consensus"



# ============================================================
# Decisión
# ============================================================


def decide_strategy(
    weights:dict[str,float]
):

    ordered = sorted(
        weights.items(),
        key=lambda x:x[1],
        reverse=True
    )


    if not ordered:

        return {
            "strategy":
                "no_decision"
        }



    best_model,best_weight = ordered[0]


    second_weight = (
        ordered[1][1]
        if len(ordered)>1
        else 0
    )


    dominance = (
        best_weight
        -
        second_weight
    )


    if (
        best_weight >= DOMINANCE_THRESHOLD
        and
        dominance >= AMBIGUITY_MARGIN
    ):

        strategy = "single_model"

        result = {

            "strategy":
                strategy,

            "selected_model":
                best_model,

            "reason":
                "Existe un modelo dominante"
        }


    else:

        strategy = "ensemble"

        result = {

            "strategy":
                strategy,

            "models":
                list(weights.keys()),

            "reason":
                "No existe separación suficiente entre modelos"
        }


    result.update({

        "dominance":
            round(
                dominance,
                4
            ),

        "consensus_strength":
            consensus_strength(
                weights
            ),

        "evidence_state":
            evidence_state(
                dominance,
                strategy
            )

    })


    return result



# ============================================================
# Analizar resultados
# ============================================================


def analyze_pair(
    pair_name,
    pair_data
):

    weights = (
        pair_data
        .get("weights",{})
    )


    decision = decide_strategy(
        weights
    )


    return {

        "pair_name":
            pair_name,

        "weights":
            weights,

        "decision":
            decision

    }



# ============================================================
# MAIN
# ============================================================


def main():

    source = latest_ensemble_file()


    data = load_json(
        source
    )


    results={}


    for pair_name,pair_data in (
        data
        .get("results",{})
        .items()
    ):

        results[pair_name]=analyze_pair(
            pair_name,
            pair_data
        )



    output={

        "analysis":{

            "created_at":
                datetime.now()
                .isoformat(),

            "engine":
                "consensus_engine_v0.2",

            "source":
                source.name
        },


        "results":
            results
    }



    output_path=(
        ANALYTICS_DIR
        /
        (
            "consensus_engine_"
            +
            datetime.now()
            .strftime("%Y%m%d_%H%M%S")
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
    print("CONSENSUS ENGINE v0.2")
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