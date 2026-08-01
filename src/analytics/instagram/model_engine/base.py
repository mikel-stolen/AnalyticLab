"""
base.py

Clase base para todos los modelos del Motor de Modelos.

Todos los modelos deberán implementar la misma interfaz para que
el Engine pueda evaluarlos de forma uniforme.
"""

from abc import ABC, abstractmethod


class BaseModel(ABC):
    """
    Clase abstracta de la que heredarán todos los modelos.
    """

    name = "BaseModel"

    @abstractmethod
    def fit(self, x, y):
        """
        Ajusta el modelo a los datos.
        """
        pass

    @abstractmethod
    def predict(self, x):
        """
        Devuelve las predicciones del modelo.
        """
        pass

    @abstractmethod
    def evaluate(self, x, y):
        """
        Calcula las métricas descriptivas del modelo.

        Debe devolver un diccionario con métricas como:

        {
            "r2": ...,
            "mae": ...,
            "rmse": ...
        }
        """
        pass

    @abstractmethod
    def bootstrap(self, x, y):
        """
        Ejecuta el análisis bootstrap.
        """
        pass

    @abstractmethod
    def loocv(self, x, y):
        """
        Ejecuta Leave-One-Out Cross Validation.
        """
        pass

    @abstractmethod
    def describe(self):
        """
        Devuelve información descriptiva del modelo.
        """
        pass