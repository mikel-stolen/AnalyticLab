"""
AnalyticLab
Evidence Engine v1.0

============================================================

Este módulo constituye el núcleo de conocimiento
compartido de AnalyticLab.

Su objetivo NO es realizar cálculos.

Su objetivo es reunir toda la evidencia generada por
los distintos motores para que cualquier módulo
(Bayes, Prediction, Feedback, IA Conversacional...)
trabaje exactamente sobre el mismo contexto.

Arquitectura

H6
 │
 ▼
Ensemble
 │
 ▼
Consensus
 │
 ▼
Bayesian
 │
 ▼
Prediction
 │
 ▼
Feedback
 │
 ▼
Calibration

↓

Evidence Engine

↓

EvidenceContext

↓

Todos los módulos consumidores

============================================================
"""

from __future__ import annotations

import json

from copy import deepcopy

from pathlib import Path

from datetime import datetime

from typing import Any



# ============================================================
# Localización del proyecto
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

        "No se encontró la carpeta raíz de AnalyticLab"

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
# Fuentes de conocimiento
# ============================================================

SOURCES = {

    "h6":

        "h6_nonlinear_analysis_*.json",

    "ensemble":

        "model_ensemble_*.json",

    "consensus":

        "consensus_engine_*.json",

    "bayesian":

        "bayesian_engine_*.json",

}



# ============================================================
# Caché
# ============================================================

_CACHE = {

    "loaded_at": None,

    "sources": None

}



# ============================================================
# Utilidades
# ============================================================


def load_json(path: Path) -> dict[str, Any]:

    with open(

        path,

        "r",

        encoding="utf-8"

    ) as file:

        return json.load(file)



def latest_file(pattern: str) -> Path:

    files = sorted(

        ANALYTICS_DIR.glob(pattern),

        key=lambda p: p.stat().st_mtime

    )

    if not files:

        raise RuntimeError(

            f"No existe ningún archivo '{pattern}'"

        )

    return files[-1]



# ============================================================
# Carga de fuentes
# ============================================================


def load_sources(
    force_reload: bool = False
) -> dict[str, Any]:

    """
    Carga todos los módulos más recientes.

    Si ya estaban cargados y no se solicita
    recarga, utiliza la caché.
    """

    global _CACHE

    if (

        _CACHE["sources"] is not None

        and

        not force_reload

    ):

        return deepcopy(

            _CACHE["sources"]

        )



    loaded = {}



    for source_name, pattern in SOURCES.items():

        file = latest_file(pattern)

        loaded[source_name] = {

            "file": file.name,

            "loaded_at":

                datetime.now().isoformat(),

            "data":

                load_json(file)

        }



    _CACHE = {

        "loaded_at":

            datetime.now().isoformat(),

        "sources":

            deepcopy(loaded)

    }



    return loaded



# ============================================================
# Evidence Context
# ============================================================


class EvidenceContext:

    """
    Contenedor central de evidencia.

    Todos los módulos de AnalyticLab deberán
    trabajar sobre este objeto.

    No realiza cálculos.

    Únicamente organiza información.
    """

    def __init__(

        self,

        pair: str,

        sources: dict[str, Any]

    ):

        self.pair = pair

        self.sources = sources



    def to_dict(self):

        return {

            "pair":

                self.pair,

            "sources":

                self.sources

        }



    def __repr__(self):

        return (

            f"EvidenceContext(pair='{self.pair}')"

        )

# ============================================================
# Extracción de relaciones
# ============================================================


def extract_pair_data(
    source_name: str,
    source_data: dict[str, Any],
    pair: str
) -> Any:
    """
    Extrae únicamente la información de una relación
    concreta desde un módulo.

    Si no existe devuelve None.
    """

    data = source_data.get("data", {})

    # Caso estándar
    if "results" in data:

        result = data["results"]

        if isinstance(result, dict):

            return deepcopy(
                result.get(pair)
            )

        if isinstance(result, list):

            for item in result:

                if (
                    item.get("pair_name") == pair
                    or
                    item.get("pair") == pair
                ):

                    return deepcopy(item)

    # Algunos módulos utilizan "analysis"

    if "analyses" in data:

        analyses = data["analyses"]

        if pair in analyses:
            return deepcopy(
                analyses[pair]
            )

    # H6 utiliza directamente el nombre de la relación

    if pair in data:

        return deepcopy(
            data[pair]
        )

    return None


# ============================================================
# Constructor del contexto
# ============================================================


def build_context(
    pair: str,
    force_reload: bool = False
) -> EvidenceContext:
    """
    Construye el contexto completo de una relación.

    Devuelve toda la evidencia conocida
    por AnalyticLab para esa relación.
    """

    loaded = load_sources(
        force_reload=force_reload
    )

    context = {}

    metadata = {}

    for source_name, source in loaded.items():

        metadata[source_name] = {

            "file":
                source["file"],

            "loaded_at":
                source["loaded_at"]

        }

        context[source_name] = extract_pair_data(

            source_name,

            source,

            pair

        )

    return EvidenceContext(

        pair=pair,

        sources={

            "metadata":
                metadata,

            "modules":
                context

        }

    )


# ============================================================
# API pública
# ============================================================


def get_context(
    pair: str
) -> dict[str, Any]:
    """
    Devuelve directamente un diccionario.

    Pensado para módulos que no necesiten
    trabajar con la clase EvidenceContext.
    """

    return build_context(
        pair
    ).to_dict()


def available_pairs():

    """
    Devuelve todas las relaciones
    utilizando H6 como referencia.
    """

    loaded = load_sources()

    h6 = loaded["h6"]["data"]

    analyses = h6.get(
        "analyses",
        {}
    )

    if not isinstance(
        analyses,
        dict
    ):
        return []

    return sorted(
        analyses.keys()
    )

# ============================================================
# Validaciones
# ============================================================


def context_exists(
    pair: str
):

    return pair in available_pairs()


def module_exists(
    module: str
):

    return module in SOURCES

# ============================================================
# Diagnóstico
# ============================================================


def system_status():

    """
    Comprueba el estado general
    de todas las fuentes.
    """

    report = {}

    loaded = load_sources()

    for module, source in loaded.items():

        report[module] = {

            "file": source["file"],

            "loaded_at": source["loaded_at"],

            "available": True

        }

    return report



def context_summary(
    context: EvidenceContext
):

    modules = context.sources["modules"]

    available = []

    missing = []

    for name, value in modules.items():

        if value is None:

            missing.append(name)

        else:

            available.append(name)

    return {

        "pair": context.pair,

        "available_modules": available,

        "missing_modules": missing,

        "total_modules": len(modules)

    }



# ============================================================
# Exportación
# ============================================================


def export_context(
    context: EvidenceContext
):

    output = (

        ANALYTICS_DIR

        /

        (

            "evidence_context_"

            +

            context.pair

            +

            "_"

            +

            datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )

            +

            ".json"

        )

    )

    with open(

        output,

        "w",

        encoding="utf-8"

    ) as file:

        json.dump(

            context.to_dict(),

            file,

            indent=4,

            ensure_ascii=False

        )

    return output



# ============================================================
# MAIN
# ============================================================


def main():

    print()

    print("=" * 60)
    print("EVIDENCE ENGINE v1.0")
    print("=" * 60)
    print()

    print("Fuentes detectadas")
    print()

    status = system_status()

    for module, info in status.items():

        print(

            f"{module:12}"

            f" OK"

            f"   {info['file']}"

        )

    print()

    print("-" * 60)
    print()

    pairs = available_pairs()

    print(

        f"Relaciones detectadas: {len(pairs)}"

    )

    print()

    for pair in pairs:

        print(pair)

    print()

    if not pairs:

        print(

            "No existen relaciones."

        )

        return

    print("-" * 60)
    print()

    pair = pairs[0]

    print(

        "Construyendo contexto de ejemplo"

    )

    print(pair)

    print()

    context = build_context(pair)

    summary = context_summary(context)

    print("Resumen")

    print()

    print(

        "Módulos disponibles:",

        ", ".join(

            summary["available_modules"]

        )

    )

    print()

    if summary["missing_modules"]:

        print(

            "Módulos ausentes:",

            ", ".join(

                summary["missing_modules"]

            )

        )

        print()

    exported = export_context(context)

    print(

        "Contexto exportado"

    )

    print(exported)

    print()

    print("=" * 60)

    print(

        "Evidence Engine listo."

    )

    print("=" * 60)

    print()



if __name__ == "__main__":

    main()