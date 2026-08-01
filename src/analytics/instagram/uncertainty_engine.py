"""
============================================================
UNCERTAINTY ENGINE
============================================================

Combina:

- Bootstrap
- LOOCV
- Ensemble
- Desacuerdo entre modelos

y produce un índice global de confianza.

Autor:
AnalyticLab
"""
from pathlib import Path
import json
import numpy as np
def load_latest_ensemble():

    analytics_dir = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "processed"
        / "instagram"
        / "analytics"
    )

    files = sorted(
        analytics_dir.glob("model_ensemble_*.json")
    )

    if not files:
        raise FileNotFoundError(
            "No existe ningún model_ensemble."
        )

    latest = files[-1]

    with open(latest, encoding="utf-8") as f:
        data = json.load(f)

    return data, latest.name

def load_latest_robustness():

    analytics_dir = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "processed"
        / "instagram"
        / "analytics"
    )

    files = sorted(
        analytics_dir.glob("h6_robustness_*.json")
    )

    latest = files[-1]

    with open(latest, encoding="utf-8") as f:
        data = json.load(f)

    return data

def main():

    ensemble, ensemble_name = load_latest_ensemble()

    robustness = load_latest_robustness()

    print()

    print("=" * 60)
    print("UNCERTAINTY ENGINE")
    print("=" * 60)

    print()

    print("Fuente ensemble:")
    print(ensemble_name)

    print()

    for relation in ensemble:

        print(relation)

if __name__ == "__main__":
    main()