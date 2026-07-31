"""
AnalyticLab - modelo lineal.

Primera extracción del motor de modelos.

Este modelo conserva la misma matemática que la implementación actual de
h6_nonlinear_analysis.py:

    y = intercept + slope * x

El objetivo de esta fase es separar el modelo sin cambiar su comportamiento.
El evaluador/ensemble seguirá siendo el encargado de decidir cuándo usarlo.
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    from src.analytics.instagram.model_engine.base import (
        BaseModel,
        ModelMetadata,
    )
except ModuleNotFoundError:
    from ...model_engine.base import (
        BaseModel,
        ModelMetadata,
    )


@dataclass
class LinearModel(BaseModel):
    """Modelo de regresión lineal simple."""

    metadata = ModelMetadata(
        name="linear",
        version="1.0",
        description="Regresión lineal simple y = a + b*x.",
        parameter_count=2,
        tags=("regression", "linear"),
        capabilities=("fit", "predict"),
    )

    intercept: float | None = None
    slope: float | None = None

    def fit(
        self,
        x: list[float],
        y: list[float],
    ) -> "LinearModel":
        self.validate_training_data(x, y)

        if len(x) < 3:
            raise ValueError(
                "linear: se necesitan al menos 3 observaciones."
            )

        n = len(x)
        sx = sum(x)
        sy = sum(y)
        sxx = sum(value * value for value in x)
        sxy = sum(
            a * b
            for a, b in zip(x, y)
        )

        denominator = (
            n * sxx
            - sx * sx
        )

        if abs(denominator) < 1e-12:
            raise ValueError(
                "linear: no se puede ajustar el modelo; "
                "la variable x no tiene variación suficiente."
            )

        self.slope = (
            n * sxy
            - sx * sy
        ) / denominator

        self.intercept = (
            sy
            - self.slope * sx
        ) / n

        self._fitted = True
        return self

    def predict(self, x: float) -> float:
        if not self._fitted:
            raise RuntimeError(
                "linear: el modelo debe ajustarse antes de predecir."
            )

        if not isinstance(x, (int, float)):
            raise TypeError(
                "linear: x debe ser numérico."
            )

        return self.intercept + self.slope * x


if __name__ == "__main__":
    model = LinearModel().fit(
        [1.0, 2.0, 3.0],
        [2.0, 4.0, 6.0],
    )

    print("LinearModel")
    print("  intercept:", model.intercept)
    print("  slope:", model.slope)
    print("  predict(4):", model.predict(4.0))
