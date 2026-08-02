"""
============================================================
AnalyticLab - Prediction Report v1.0
============================================================

Generador de informes humanos a partir del Prediction Engine.

Responsabilidades
-----------------
1. Ejecutar Prediction Engine.
2. Interpretar resultados.
3. Generar reporte legible.

============================================================
"""


from prediction_engine_v2 import run_prediction



def format_percentage(value):

    return f"{value:.2f}"



def generate_report(result):


    relation = result["relation"]

    models = result["models"]

    ensemble = result["ensemble"]

    bayesian = result["bayesian"]

    reasoning = result["reasoning"]


    print("=" * 60)
    print("ANALYTICLAB - PREDICTION REPORT")
    print("=" * 60)

    print()

    print("Relación:")
    print(relation)

    print()

    print("-" * 60)
    print("MODELOS")
    print("-" * 60)


    for model, value in models.items():

        print(
            f"{model:12}: {format_percentage(value)}"
        )


    print()

    print("-" * 60)
    print("ENSEMBLE")
    print("-" * 60)


    print(
        "Predicción final:",
        format_percentage(
            ensemble["prediction"]
        )
    )


    print()

    print("-" * 60)
    print("BAYESIAN")
    print("-" * 60)

    winner = reasoning["bayesian"]["winner"]

    winner_probability = reasoning["bayesian"]["winner_probability"]

    print(
        "Modelo dominante:",
        winner
    )

    print(
        "Probabilidad dominante:",
        format_percentage(
            winner_probability * 100
        ),
        "%"
    )

    print(
        "Confianza:",
        format_percentage(
            bayesian["confidence"] * 100
        ),
        "%"
    )


    print(
        "Estado:",
        bayesian["evidence_state"]
    )


    print()

    print("-" * 60)
    print("REASONING")
    print("-" * 60)


    print()

    print(
        "Diagnóstico:"
    )

    print()

    models_reasoning = reasoning["models"]

    consensus_reasoning = reasoning["consensus"]

    if models_reasoning["agreement"]:

        print(
            "- Los modelos presentan buena concordancia."
        )

    else:

        print(
            "- Los modelos presentan divergencia alta."
        )

    print(
        "- Dispersión entre modelos:",
        models_reasoning["spread"]
    )

    print(
        "- Estrategia:",
        consensus_reasoning["strategy"]
    )

    print(
        "- Motivo:",
        consensus_reasoning["reason"]
    )


    print()

    print("=" * 60)



def main():


    result = run_prediction()

    generate_report(result)



if __name__ == "__main__":

    main()