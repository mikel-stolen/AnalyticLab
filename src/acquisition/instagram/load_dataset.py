import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "instagram"


def load_latest_dataset() -> list:
    """
    Carga el dataset procesado más reciente de Instagram.
    """

    files = sorted(
        PROCESSED_DIR.glob("posts_normalized_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not files:
        raise FileNotFoundError(
            f"No se encontraron datasets procesados en {PROCESSED_DIR}"
        )

    latest_file = files[0]

    with open(latest_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("El dataset procesado no tiene un formato válido.")

    print(f"Dataset cargado: {latest_file}")
    print(f"Registros: {len(data)}")

    return data


if __name__ == "__main__":

    dataset = load_latest_dataset()

    print("\nPrimer registro:")
    print(json.dumps(dataset[0], indent=4, ensure_ascii=False))