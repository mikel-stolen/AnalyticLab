"""
evaluator.py

Ejecuta todos los modelos registrados sobre un mismo conjunto de datos.

Su única responsabilidad es obtener resultados homogéneos para que
el resto del Motor pueda trabajar con ellos.
"""

from .registry import ModelRegistry


class ModelEvaluator:
    """
    Evalúa todos los modelos registrados.
    """

    def __init__(self):
        self.models = ModelRegistry.get_models()

    def evaluate_all(self, x, y):
        """
        Ejecuta todos los modelos y devuelve sus resultados.
        """

        results = []

        for model in self.models:

            model.fit(x, y)

            metrics = model.evaluate(x, y)

            results.append({
                "name": model.name,
                "model": model,
                "metrics": metrics
            })

        return results