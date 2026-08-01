"""
============================================================
H7 - DECISION ENGINE
============================================================

Motor de decisión científica de AnalyticLab.

Este módulo integra toda la evidencia generada por los
análisis anteriores para producir decisiones con un nivel
de confianza cuantificado.

Actualmente carga:

- Account Engagement State
- H6 Nonlinear Analysis
- H6 Robustness
- Model Ensemble
- Relative Performance
- Sequence Analysis

Autor:
AnalyticLab
"""

from pathlib import Path
import json


class DecisionEngine:

    def __init__(self):

        self.analytics_path = (
            Path(__file__).resolve().parents[3]
            / "data"
            / "processed"
            / "instagram"
            / "analytics"
        )

        self.account = {}
        self.nonlinear = {}
        self.robustness = {}
        self.ensemble = {}
        self.relative = {}
        self.sequence = {}

    # -----------------------------------------------------

    def _load_latest(self, pattern):
        """
        Carga el JSON más reciente que coincida
        con el patrón indicado.
        """

        files = sorted(self.analytics_path.glob(pattern))

        if not files:
            raise FileNotFoundError(
                f"No existe ningún archivo para: {pattern}"
            )

        latest = files[-1]

        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data, latest.name

    # -----------------------------------------------------

    def load(self):

        (
            self.account,
            account_name,
        ) = self._load_latest(
            "account_engagement_state_*.json"
        )

        (
            self.nonlinear,
            nonlinear_name,
        ) = self._load_latest(
            "h6_nonlinear_analysis_*.json"
        )

        (
            self.robustness,
            robustness_name,
        ) = self._load_latest(
            "h6_robustness_*.json"
        )

        (
            self.ensemble,
            ensemble_name,
        ) = self._load_latest(
            "model_ensemble_*.json"
        )

        (
            self.relative,
            relative_name,
        ) = self._load_latest(
            "relative_performance_*.json"
        )

        (
            self.sequence,
            sequence_name,
        ) = self._load_latest(
            "sequence_analysis_*.json"
        )

        print()
        print("=" * 60)
        print("H7 - DECISION ENGINE")
        print("=" * 60)
        print()

        print("Archivos cargados:")
        print(f"  ✓ {account_name}")
        print(f"  ✓ {nonlinear_name}")
        print(f"  ✓ {robustness_name}")
        print(f"  ✓ {ensemble_name}")
        print(f"  ✓ {relative_name}")
        print(f"  ✓ {sequence_name}")

        print()
        print("Todos los análisis han sido cargados correctamente.")

    def analyse_consensus(self):

        print()
        print("=" * 60)
        print("ANÁLISIS DE CONSENSO")
        print("=" * 60)

        results = self.ensemble["results"]

        self.consensus = {}

        for variable, data in results.items():

            # -----------------------------
            # Pesos del ensemble
            # -----------------------------
            weights = data["weights"]

            ordered = sorted(
                weights.items(),
                key=lambda x: x[1],
                reverse=True
            )

            best_name, best_weight = ordered[0]
            second_name, second_weight = ordered[1]

            margin = best_weight - second_weight

            # -----------------------------
            # Disagreement
            # -----------------------------

            if "model_disagreement" in data:

                disagreement = data["model_disagreement"]

            else:
                # Mientras H6 no lo exporte,
                # usamos una medida basada
                # en la dispersión de pesos.

                values = list(weights.values())

                disagreement = max(values) - min(values)

            # -----------------------------
            # Fuerza del consenso
            # -----------------------------

            if margin >= 0.20:
                consensus_strength = "VERY HIGH"

            elif margin >= 0.10:
                consensus_strength = "HIGH"

            elif margin >= 0.05:
                consensus_strength = "MEDIUM"

            else:
                consensus_strength = "LOW"

            self.consensus[variable] = {

                "best_model": best_name,
                "best_weight": best_weight,

                "second_model": second_name,
                "second_weight": second_weight,

                "margin": margin,

                "disagreement": disagreement,

                "consensus_strength": consensus_strength
            }

            print()
            print(variable)

            print(
                f"  Mejor modelo : {best_name}"
            )

            print(
                f"  Peso         : {best_weight:.3f}"
            )

            print(
                f"  Segundo      : {second_name}"
            )

            print(
                f"  Peso         : {second_weight:.3f}"
            )

            print(
                f"  Margen       : {margin:.3f}"
            )

            print(
                f"  Disagreement : {disagreement:.3f}"
            )

            print(
                f"  Consenso     : {consensus_strength}"
            )

    # -----------------------------------------------------

    def run(self):
        """
        Punto de entrada del motor.

        De momento únicamente carga todos los
        análisis disponibles.

        En siguientes versiones construirá el
        Scientific State y calculará la confianza.
        """

        self.load()


# ============================================================


def main():

    engine = DecisionEngine()

    engine.run()

    engine.analyse_consensus()


if __name__ == "__main__":
    main()