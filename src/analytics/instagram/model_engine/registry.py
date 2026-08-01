"""
registry.py

Registro central de modelos.

El Registry es el encargado de descubrir y proporcionar todos los
modelos disponibles para el Motor de Modelos.
"""

from typing import List, Type

from .base import BaseModel

# Modelos disponibles
from .models.linear import LinearModel
from .models.quadratic import QuadraticModel
from .models.threshold import ThresholdModel
from .models.saturation import SaturationModel


class ModelRegistry:
    """
    Registro central de modelos.
    """

    _models: List[Type[BaseModel]] = [
        LinearModel,
        QuadraticModel,
        ThresholdModel,
        SaturationModel,
    ]

    @classmethod
    def get_models(cls) -> List[BaseModel]:
        """
        Devuelve una instancia de todos los modelos registrados.
        """
        return [model() for model in cls._models]

    @classmethod
    def get_model_names(cls) -> List[str]:
        """
        Devuelve únicamente los nombres.
        """
        return [model.name for model in cls._models]

    @classmethod
    def register(cls, model: Type[BaseModel]):
        """
        Permite registrar modelos dinámicamente.
        """
        if model not in cls._models:
            cls._models.append(model)