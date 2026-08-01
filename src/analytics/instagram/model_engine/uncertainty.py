"""
uncertainty.py

Sistema de estimación de incertidumbre del Motor de Modelos.
"""

import numpy as np


class UncertaintyEstimator:

    @staticmethod
    def estimate(results):

        scores = np.array(
            [r["score"] for r in results]
        )

        score_std = np.std(scores)

        score_mean = np.mean(scores)

        for result in results:

            overall = abs(
                result["score"] - score_mean
            ) + score_std

            result["uncertainty"] = {

                "bootstrap": None,

                "loocv": None,

                "disagreement": None,

                "sample_size": None,

                "overall": float(overall)

            }

        return results