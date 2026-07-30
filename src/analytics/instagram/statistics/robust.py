from statistics import median
import random


def iqr(values: list[float]) -> float | None:
    """
    Rango intercuartílico: Q3 - Q1.
    """

    if len(values) < 2:
        return None

    ordered = sorted(values)
    n = len(ordered)

    midpoint = n // 2

    if n % 2 == 0:
        lower = ordered[:midpoint]
        upper = ordered[midpoint:]
    else:
        lower = ordered[:midpoint]
        upper = ordered[midpoint + 1:]

    q1 = median(lower)
    q3 = median(upper)

    return q3 - q1


def mad(values: list[float]) -> float | None:
    """
    Desviación absoluta mediana.

    MAD = mediana(|x - mediana(x)|)
    """

    if not values:
        return None

    center = median(values)

    deviations = [
        abs(value - center)
        for value in values
    ]

    return median(deviations)


def bootstrap_median(
    values: list[float],
    iterations: int = 10000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float] | None:
    """
    Intervalo bootstrap aproximado para la mediana.
    """

    if len(values) < 2:
        return None

    if not 0 < confidence < 1:
        raise ValueError(
            "confidence debe estar entre 0 y 1."
        )

    if iterations <= 0:
        raise ValueError(
            "iterations debe ser mayor que 0."
        )

    rng = random.Random(seed)

    bootstrap_medians = []

    for _ in range(iterations):

        sample = [
            rng.choice(values)
            for _ in range(len(values))
        ]

        bootstrap_medians.append(
            median(sample)
        )

    bootstrap_medians.sort()

    alpha = 1 - confidence

    lower_index = int(
        (alpha / 2) * iterations
    )

    upper_index = int(
        (1 - alpha / 2) * iterations
    )

    upper_index = min(
        upper_index,
        iterations - 1,
    )

    return (
        bootstrap_medians[lower_index],
        bootstrap_medians[upper_index],
    )