import math


def log2_relative_ratio(
    value: float,
    baseline: float,
) -> float | None:
    """
    Calcula log2(value / baseline).

    0  -> igual al baseline
    +1 -> el doble
    -1 -> la mitad
    """

    if value <= 0 or baseline <= 0:
        return None

    return math.log2(
        value / baseline
    )