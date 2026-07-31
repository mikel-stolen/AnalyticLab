import json
import math
import statistics
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ANALYTICS_DIR = PROJECT_ROOT / "data" / "processed" / "instagram" / "analytics"


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def latest_state_snapshot() -> Path:
    files = sorted(
        ANALYTICS_DIR.glob("account_engagement_state_*.json"),
        key=lambda p: p.stat().st_mtime,
    )
    if not files:
        raise RuntimeError("No se encontraron account_engagement_state_*.json")
    return files[-1]


def pearson(x, y):
    if len(x) != len(y) or len(x) < 3:
        return None
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    return None if dx == 0 or dy == 0 else num / (dx * dy)


def rank(values):
    items = sorted(enumerate(values), key=lambda z: z[1])
    out = [0.0] * len(values)
    i = 0
    while i < len(items):
        j = i
        while j + 1 < len(items) and items[j + 1][1] == items[i][1]:
            j += 1
        r = (i + j + 2) / 2
        for k in range(i, j + 1):
            out[items[k][0]] = r
        i = j + 1
    return out


def spearman(x, y):
    return pearson(rank(x), rank(y)) if len(x) >= 3 else None


def r2(y, pred):
    if not y:
        return None
    ym = statistics.mean(y)
    sse = sum((a - b) ** 2 for a, b in zip(y, pred))
    sst = sum((a - ym) ** 2 for a in y)
    return None if sst == 0 else 1 - sse / sst


def mae(y, pred):
    return statistics.mean(abs(a - b) for a, b in zip(y, pred)) if y else None


def solve_3x3(a, b):
    m = [list(map(float, row)) + [float(rhs)] for row, rhs in zip(a, b)]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            return None
        m[col], m[pivot] = m[pivot], m[col]
        p = m[col][col]
        for j in range(col, 4):
            m[col][j] /= p
        for r in range(3):
            if r == col:
                continue
            factor = m[r][col]
            for j in range(col, 4):
                m[r][j] -= factor * m[col][j]
    return m[0][3], m[1][3], m[2][3]


def fit_linear(x, y):
    n = len(x)
    if n < 3:
        return None
    sx, sy = sum(x), sum(y)
    sxx = sum(v * v for v in x)
    sxy = sum(a * b for a, b in zip(x, y))
    den = n * sxx - sx * sx
    if abs(den) < 1e-12:
        return None
    b = (n * sxy - sx * sy) / den
    a = (sy - b * sx) / n
    pred = [a + b * v for v in x]
    return {
        "type": "linear",
        "parameters": {"intercept": a, "slope": b},
        "r_squared": r2(y, pred),
        "mae": mae(y, pred),
        "predictions": pred,
    }


def fit_quadratic(x, y):
    if len(x) < 4:
        return None
    n = len(x)
    sx = sum(x)
    sx2 = sum(v * v for v in x)
    sx3 = sum(v ** 3 for v in x)
    sx4 = sum(v ** 4 for v in x)
    sy = sum(y)
    sxy = sum(a * b for a, b in zip(x, y))
    sx2y = sum((a * a) * b for a, b in zip(x, y))
    coeffs = solve_3x3(
        [[n, sx, sx2], [sx, sx2, sx3], [sx2, sx3, sx4]],
        [sy, sxy, sx2y],
    )
    if coeffs is None:
        return None
    a, b, c = coeffs
    pred = [a + b * v + c * v * v for v in x]
    return {
        "type": "quadratic",
        "parameters": {"intercept": a, "linear": b, "quadratic": c},
        "vertex_x": (-b / (2 * c)) if abs(c) > 1e-12 else None,
        "r_squared": r2(y, pred),
        "mae": mae(y, pred),
        "predictions": pred,
    }


def fit_threshold(x, y):
    ux = sorted(set(x))
    if len(ux) < 3:
        return None
    best = None
    for left, right in zip(ux[:-1], ux[1:]):
        t = (left + right) / 2
        ly = [b for a, b in zip(x, y) if a <= t]
        ry = [b for a, b in zip(x, y) if a > t]
        if len(ly) < 2 or len(ry) < 2:
            continue
        lm, rm = statistics.mean(ly), statistics.mean(ry)
        pred = [lm if a <= t else rm for a in x]
        model = {
            "type": "threshold",
            "parameters": {"threshold": t, "left_mean": lm, "right_mean": rm},
            "r_squared": r2(y, pred),
            "mae": mae(y, pred),
            "predictions": pred,
        }
        if best is None or model["mae"] < best["mae"]:
            best = model
    return best


def fit_saturation(x, y):
    if len(x) < 5:
        return None
    x0 = min(x)
    shifted = [max(v - x0, 0.0) for v in x]
    span = max(shifted)
    if span <= 0:
        return None

    best = None
    for exponent in (-4, -3.5, -3, -2.5, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4):
        k = (10 ** exponent) / span
        z = [1 - math.exp(-k * v) for v in shifted]
        lm = fit_linear(z, y)
        if lm is None:
            continue
        a = lm["parameters"]["intercept"]
        b = lm["parameters"]["slope"]
        pred = [a + b * zi for zi in z]
        model = {
            "type": "saturation",
            "parameters": {"intercept": a, "amplitude": b, "k": k, "x_shift": x0},
            "r_squared": r2(y, pred),
            "mae": mae(y, pred),
            "predictions": pred,
        }
        if best is None or model["mae"] < best["mae"]:
            best = model
    return best


def monotonic_diagnostic(x, y):
    pairs = sorted(zip(x, y), key=lambda z: z[0])
    if len(pairs) < 3:
        return {"classification": "insufficient_data"}
    changes = [pairs[i + 1][1] - pairs[i][1] for i in range(len(pairs) - 1)]
    pos = sum(c > 0 for c in changes)
    neg = sum(c < 0 for c in changes)
    total = pos + neg
    if total == 0:
        cls = "flat"
    elif pos / total >= 0.7:
        cls = "mostly_increasing"
    elif neg / total >= 0.7:
        cls = "mostly_decreasing"
    else:
        cls = "non_monotonic"
    return {
        "classification": cls,
        "positive_steps": pos,
        "negative_steps": neg,
        "positive_share": pos / total if total else None,
        "negative_share": neg / total if total else None,
    }


def analyze_pair_group(group, predictor, outcome):
    pairs = group.get("pairs", [])
    x = [p["state_value"] for p in pairs]
    y = [p["initial_value"] for p in pairs]

    models = {
        "linear": fit_linear(x, y),
        "quadratic": fit_quadratic(x, y),
        "threshold": fit_threshold(x, y),
        "saturation": fit_saturation(x, y),
    }
    available = [m for m in models.values() if m is not None]
    best = min(available, key=lambda m: m["mae"]) if available else None

    return {
        "predictor": predictor,
        "outcome": outcome,
        "n": len(x),
        "pearson_r": pearson(x, y),
        "spearman_rho": spearman(x, y),
        "monotonic": monotonic_diagnostic(x, y),
        "models": models,
        "preferred_by_mae": best["type"] if best else None,
    }


def main():
    source = latest_state_snapshot()
    data = load_json(source)
    groups = data.get("hypothesis_pairs", {})

    definitions = {
        "eg_3_vs_initial_ir": ("EG_3", "Initial IR"),
        "eg_5_vs_initial_ir": ("EG_5", "Initial IR"),
        "eg_7d_vs_initial_ir": ("EG_7d", "Initial IR"),
        "eg_5_vs_initial_reach": ("EG_5", "Initial Reach"),
        "eg_5_vs_initial_views": ("EG_5", "Initial Views"),
        "temperature_vs_initial_ir": ("Account Temperature", "Initial IR"),
        "temperature_vs_initial_reach": ("Account Temperature", "Initial Reach"),
    }

    analyses = {}

    print()
    print("=" * 60)
    print("H6 - FORMA DE LA RELACIÓN")
    print("=" * 60)
    print(f"Fuente: {source.name}")

    for name, (predictor, outcome) in definitions.items():
        result = analyze_pair_group(
            groups.get(name, {}),
            predictor,
            outcome,
        )
        analyses[name] = result

        print()
        print(name)
        print(f"  n = {result['n']}")
        print(f"  Pearson = {result['pearson_r']}")
        print(f"  Spearman = {result['spearman_rho']}")
        print(f"  Monotonicidad = {result['monotonic']['classification']}")
        print(f"  Mejor ajuste descriptivo = {result['preferred_by_mae']}")

        for model_name, model in result["models"].items():
            if model is None:
                continue
            print(
                f"    {model_name}: "
                f"R2={model['r_squared']:.4f} "
                f"MAE={model['mae']:.4f}"
            )

    output = {
        "analysis": {
            "created_at": datetime.now().isoformat(),
            "source_snapshot": source.name,
            "tested_forms": {
                "linear": "y = a + b*x",
                "monotonic": "Spearman + ordered-step diagnostic",
                "nonlinear": "quadratic y = a + b*x + c*x^2",
                "threshold": "piecewise two-level threshold model",
                "saturation": "y = a + b*(1-exp(-k*x))",
            },
            "warning": (
                "Exploratorio: con una muestra pequeña, un modelo puede "
                "ajustarse al ruido. No establece causalidad."
            ),
        },
        "analyses": analyses,
    }

    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = ANALYTICS_DIR / f"h6_nonlinear_analysis_{stamp}.json"

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=4, ensure_ascii=False)

    print()
    print("Análisis guardado en:")
    print(output_path)


if __name__ == "__main__":
    main()