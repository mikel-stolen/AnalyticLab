"""
Cliente para la Instagram Graph API.
"""

from typing import Any

import requests

from src.acquisition.instagram.config import ACCESS_TOKEN, GRAPH_URL


class InstagramClient:
    """
    Cliente encargado de comunicarse con la Instagram Graph API.
    """

    def __init__(self) -> None:
        self.base_url = GRAPH_URL
        self.session = requests.Session()

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict:
        """
        Realiza una petición GET a la API.
        """

        if params is None:
            params = {}

        params["access_token"] = ACCESS_TOKEN

        url = f"{self.base_url}/{endpoint}"

        try:

            response = self.session.get(
                url=url,
                params=params,
                timeout=30
            )

            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as e:
            print("❌ Error HTTP")
            print(response.text)
            raise e

        except requests.exceptions.Timeout as e:
            print("❌ Tiempo de espera agotado.")
            raise e

        except requests.exceptions.RequestException as e:
            print("❌ Error de conexión.")
            raise e