"""
Contrato base para los modelos de AnalyticLab.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelMetadata:
    name: str
    version: str = "1.0"
    description: str = ""
    parameter_count: int = 0
    tags: tuple[str, ...] = field(default_factory=tuple)
    capabilities: tuple[str, ...] = field(default_factory=tuple)


class BaseModel(ABC):
    metadata: ModelMetadata

    def __init__(self) -> None:
        self._fitted = False

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def version(self) -> str:
        return self.metadata.version

    def is_fitted(self) -> bool:
        return self._fitted

    def validate_training_data(
        self,
        x: list[float],
        y: list[float],
    ) -> None:
        if len(x) != len(y):
            raise ValueError(
                f"{self.name}: x e y deben tener la misma longitud."
            )

        if not x:
            raise ValueError(
                f"{self.name}: no hay observaciones."
            )

        if not all(
            isinstance(value, (int, float))
            for value in x + y
        ):
            raise TypeError(
                f"{self.name}: x e y deben ser numéricos."
            )

    @abstractmethod
    def fit(
        self,
        x: list[float],
        y: list[float],
    ) -> "BaseModel":
        raise NotImplementedError

    @abstractmethod
    def predict(
        self,
        x: float,
    ) -> float:
        raise NotImplementedError