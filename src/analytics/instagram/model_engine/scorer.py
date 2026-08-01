"""
scorer.py

Sistema de puntuación del Motor de Modelos.

Convierte las métricas de cada modelo en una puntuación común para
poder compararlos.
"""

import numpy as np


class ModelScorer:

    @staticmethod
    def score(results):
        """
        Calcula una puntuación para todos los modelos.

        Parameters
        ----------
        results : list
            Salida de ModelEvaluator.

        Returns
        -------
        list
            Resultados con score añadido.
        """

        r2_values = np.array([
            r["metrics"]["r2"]
            for r in results
        ])

        mae_values = np.array([
            r["metrics"]["mae"]
            for r in results
        ])

        rmse_values = np.array([
            r["metrics"]["rmse"]
            for r in results
        ])

        # Normalización

        r2_norm = (
            r2_values - r2_values.min()
        ) / (
            r2_values.max() - r2_values.min() + 1e-9
        )

        mae_norm = 1 - (
            (mae_values - mae_values.min())
            /
            (mae_values.max() - mae_values.min() + 1e-9)
        )

        rmse_norm = 1 - (
            (rmse_values - rmse_values.min())
            /
            (rmse_values.max() - rmse_values.min() + 1e-9)
        )

        for i, result in enumerate(results):

            score = (
                0.40 * r2_norm[i]
                +
                0.30 * mae_norm[i]
                +
                0.30 * rmse_norm[i]
            )

            result["score"] = float(score)

        return results