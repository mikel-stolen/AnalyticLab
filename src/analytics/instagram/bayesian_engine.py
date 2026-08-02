    """
    AnalyticLab - Bayesian Engine v0.2
    
    Motor probabilístico para actualizar la confianza
    entre modelos candidatos.
    
    No sustituye al ensemble.
    
    Recibe:
        model_ensemble_*.json
    
    Genera:
        bayesian_engine_*.json
    
    
    Evolución:
    
    v0.1
    ----
    MAE directo
    
    
    v0.2
    ----
    - Likelihood normalizada
    - RMSE
    - Bootstrap
    - Priors adaptativos
    - Estado de evidencia
    
    
    Preparado para:
    
    - Bayesian regression
    - Online updating
    - MCMC
    - modelos probabilísticos avanzados
    
    """


    from __future__ import annotations

    import json
    import math
    import statistics

    from datetime import datetime
    from pathlib import Path
    from typing import Any



    # ============================================================
    # Localización
    # ============================================================


    def find_project_root() -> Path:

        current = Path(__file__).resolve()


        for parent in [
            current.parent,
            *current.parents
        ]:

            candidate = (
                parent
                /
                "data"
                /
                "processed"
                /
                "instagram"
            )

            if candidate.exists():

                return parent


        raise RuntimeError(
            "No se encontró AnalyticLab"
        )



    PROJECT_ROOT = find_project_root()



    ANALYTICS_DIR = (
        PROJECT_ROOT
        /
        "data"
        /
        "processed"
        /
        "instagram"
        /
        "analytics"
    )



    # ============================================================
    # Configuración bayesiana
    # ============================================================


    MODELS = (
        "linear",
        "quadratic",
        "threshold",
        "saturation",
    )



    # Prior suave

    # No decide el resultado.
    # Solo evita sobreajuste extremo
    # con pocos datos.


    PRIOR = {

        "linear":0.30,

        "quadratic":0.20,

        "threshold":0.25,

        "saturation":0.25,

    }



    COMPLEXITY = {

        "linear":1.00,

        "quadratic":0.90,

        "threshold":0.95,

        "saturation":0.90,

    }



    # Pesos evidencia

    WEIGHTS = {

        "mae":0.50,

        "rmse":0.20,

        "bootstrap":0.20,

        "complexity":0.10,

    }



    # ============================================================
    # Utilidades
    # ============================================================


    def load_json(path:Path):

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)



    def latest_ensemble_file():

        files = sorted(

            ANALYTICS_DIR.glob(
                "model_ensemble_*.json"
            ),

            key=lambda p:p.stat().st_mtime

        )


        if not files:

            raise RuntimeError(
                "No existe model_ensemble"
            )


        return files[-1]



    # ============================================================
    # Bayesian Core
    # ============================================================


    def normalize_error(
        error:float | None,
        scale:float
    ):

        if error is None:

            return 0


        if scale <= 0:

            scale=1



        return math.exp(
            -(error / scale)
        )



    def data_scale(
        values:list[float]
    ):

        if len(values)<2:

            return 1


        deviation = statistics.pstdev(
            values
        )


        return max(
            deviation,
            1
        )



    def evidence_score(
        model:str,
        metrics:dict[str,Any],
        scale:float
    ):


        mae_score = normalize_error(
            metrics.get("mae"),
            scale
        )


        rmse_score = normalize_error(
            metrics.get("rmse"),
            scale
        )


        bootstrap = (
            metrics.get(
                "winner_share",
                0
            )
            or 0
        )



        complexity = COMPLEXITY[model]



        score=(

            WEIGHTS["mae"]
            *
            mae_score

            +

            WEIGHTS["rmse"]
            *
            rmse_score

            +

            WEIGHTS["bootstrap"]
            *
            bootstrap

            +

            WEIGHTS["complexity"]
            *
            complexity

        )


        return score



    def posterior_distribution(
        metrics:dict[str,Any],
        scale:float
    ):


        evidence={}


        for model in MODELS:


            score=evidence_score(
                model,
                metrics.get(
                    model,
                    {}
                ),
                scale
            )


            evidence[model]=(
                PRIOR[model]
                *
                score
            )



        total=sum(
            evidence.values()
        )



        if total==0:

            return PRIOR.copy()



        return {

            model:
                round(
                    value/total,
                    4
                )

            for model,value
            in evidence.items()

        }



    # ============================================================
    # Interpretación
    # ============================================================


    def evidence_state(
        confidence:float
    ):


        if confidence >=0.70:

            return "strong"



        if confidence >=0.50:

            return "moderate"



        if confidence >=0.30:

            return "weak"



        return "undetermined"





    # ============================================================
    # Analizar relación
    # ============================================================


    def analyze_pair(
        pair_name:str,
        pair_data:dict[str,Any]
    ):


        metrics = (
            pair_data
            .get(
                "loocv_models",
                {}
            )
        )


        # escala aproximada

        predictions=[]


        for model in MODELS:

            predictions.extend(
                metrics
                .get(
                    model,
                    {}
                )
                .get(
                    "predictions",
                    []
                )
            )



        scale=data_scale(
            predictions
        )



        posterior=posterior_distribution(
            metrics,
            scale
        )



        winner=max(
            posterior,
            key=posterior.get
        )


        confidence=posterior[winner]



        return {

            "pair_name":
                pair_name,


            "posterior_probabilities":
                posterior,


            "winner":
                winner,


            "posterior_confidence":
                confidence,


            "evidence_state":
                evidence_state(
                    confidence
                ),


            "evidence_sources":
                [
                    "LOOCV_MAE",
                    "LOOCV_RMSE",
                    "BOOTSTRAP",
                    "COMPLEXITY_PRIOR"
                ]

        }



    # ============================================================
    # MAIN
    # ============================================================


    def main():


        source=latest_ensemble_file()


        data=load_json(
            source
        )



        results={}



        for pair_name,pair_data in (

            data
            .get(
                "results",
                {}
            )
            .items()

        ):


            results[pair_name]=analyze_pair(
                pair_name,
                pair_data
            )



        output={


            "analysis":{

                "created_at":
                    datetime.now()
                    .isoformat(),


                "engine":
                    "bayesian_engine_v0.2",


                "source":
                    source.name,


                "method":

                    {

                    "prior":
                        PRIOR,


                    "weights":
                        WEIGHTS

                    }

            },


            "results":
                results

        }



        output_path=(

            ANALYTICS_DIR

            /

            (

            "bayesian_engine_"

            +

            datetime.now()
            .strftime(
                "%Y%m%d_%H%M%S"
            )

            +

            ".json"

            )

        )



        with open(
            output_path,
            "w",
            encoding="utf-8"
        ) as file:


            json.dump(

                output,

                file,

                indent=4,

                ensure_ascii=False

            )



        print()

        print("="*60)

        print(
            "BAYESIAN ENGINE v0.2"
        )

        print("="*60)

        print()



        for name,result in results.items():


            print(name)


            print(
                "Posterior:",
                result[
                    "posterior_probabilities"
                ]
            )


            print(
                "Winner:",
                result["winner"]
            )


            print(
                "Confidence:",
                result[
                    "posterior_confidence"
                ]
            )


            print(
                "State:",
                result[
                    "evidence_state"
                ]
            )


            print()



        print(
            "Guardado:",
            output_path
        )




    if __name__=="__main__":

        main()