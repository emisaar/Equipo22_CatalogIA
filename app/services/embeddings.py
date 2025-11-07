"""
Servicio de generación de embeddings para productos usando Ollama + Gemma Embeddings.
"""
from typing import List, Optional
import logging
import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Servicio singleton para generar embeddings de texto usando Ollama + Gemma Embeddings.

    Utiliza el modelo 'embeddinggemma' a través de Ollama que:
    - Soporta múltiples idiomas (incluyendo español)
    - Genera vectores de 768 dimensiones
    - Alta calidad para búsquedas semánticas
    - Ejecuta localmente con Ollama
    """

    _instance = None
    _ollama_available: Optional[bool] = None

    # Configuración de Ollama
    MODEL_NAME = "embeddinggemma"
    EMBEDDING_DIMENSION = 768

    @property
    def OLLAMA_HOST(self) -> str:
        """Get Ollama host from settings."""
        return settings.OLLAMA_HOST

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        pass

    def _check_ollama(self) -> bool:
        """
        Verifica si Ollama está disponible y el modelo está instalado.
        """
        if self._ollama_available is not None:
            return self._ollama_available

        try:
            response = requests.get(f"{self.OLLAMA_HOST}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]

                if any(self.MODEL_NAME in name for name in model_names):
                    self._ollama_available = True
                    logger.info(f"Ollama disponible con modelo '{self.MODEL_NAME}'")
                    return True
                else:
                    logger.error(f"Modelo '{self.MODEL_NAME}' no encontrado en Ollama")
                    self._ollama_available = False
                    return False
            else:
                logger.error(f"Ollama no responde correctamente (status: {response.status_code})")
                self._ollama_available = False
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"No se puede conectar con Ollama: {e}")
            self._ollama_available = False
            return False

    def generate_embedding(self, text: str, is_query: bool = True) -> List[float]:
        """
        Genera un embedding para un texto dado usando Ollama + Gemma.
        - Para queries: "retrieval_query: [texto]"
        - Para documentos: "retrieval_document: [texto]"

        Args:
            text: Texto a convertir en embedding
            is_query: True si es una query de búsqueda, False si es un documento

        Returns:
            Lista de floats representando el vector de embedding (768 dimensiones)

        Raises:
            RuntimeError: Si Ollama no está disponible o falla la generación
        """
        if not text or not text.strip():
            # Retornar vector de ceros si el texto está vacío
            return [0.0] * self.EMBEDDING_DIMENSION

        # Verificar que Ollama esté disponible
        if not self._check_ollama():
            raise RuntimeError(
                f"Ollama no está disponible o el modelo '{self.MODEL_NAME}' no está instalado. "
                f"Instala con: ollama pull {self.MODEL_NAME}"
            )

        # Agregar prefijo correcto según tipo (query o documento)
        prefix = "retrieval_query: " if is_query else "retrieval_document: "
        prefixed_text = f"{prefix}{text}"

        try:
            # Llamar a la API de Ollama para generar el embedding
            response = requests.post(
                f"{self.OLLAMA_HOST}/api/embed",
                json={
                    "model": self.MODEL_NAME,
                    "input": prefixed_text
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                embedding = data["embeddings"][0]

                # Validar dimensión
                if len(embedding) != self.EMBEDDING_DIMENSION:
                    logger.warning(
                        f"Dimensión inesperada: {len(embedding)} (esperado: {self.EMBEDDING_DIMENSION})"
                    )

                return embedding
            else:
                raise RuntimeError(
                    f"Error al generar embedding: {response.status_code} - {response.text}"
                )

        except requests.exceptions.Timeout:
            raise RuntimeError("Timeout al generar embedding con Ollama")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error de conexión con Ollama: {e}")

    def generate_product_embedding(
        self,
        title: str,
        description: str = None,
        category: str = None,
        brand: str = None,
        color: str = None
    ) -> List[float]:
        """
        Genera un embedding combinado para un producto.

        Combina diferentes campos del producto en un texto único y genera su embedding.

        Args:
            title: Título del producto
            description: Descripción del producto (opcional)
            category: Categoría del producto (opcional)
            brand: Marca del producto (opcional)
            color: Color del producto (opcional)

        Returns:
            Lista de floats representando el vector de embedding (768 dimensiones)
        """
        parts = []

        # Título completo (contiene tipo de producto)
        if title:
            parts.append(title)

        # Atributos clave sin etiquetas
        if brand:
            parts.append(brand)

        if color:
            parts.append(color)

        if category:
            parts.append(category)

        # Descripción breve
        if description:
            desc_short = description[:80].strip()
            if desc_short:
                parts.append(desc_short)

        # Unir con puntos para mejor separación semántica
        combined_text = ". ".join(parts)
        # Los productos son documentos (prefijo: "retrieval_document:")
        return self.generate_embedding(combined_text, is_query=False)

    def warmup(self):
        """
        Verifica disponibilidad de Ollama y hace un test de embedding.
        Se puede llamar en el startup de la aplicación.
        """
        logger.info("Verificando disponibilidad de Ollama...")
        if not self._check_ollama():
            logger.error(
                f"⚠ Ollama no está disponible. Asegúrate de que esté corriendo: "
                f"'ollama serve' y que el modelo esté instalado: 'ollama pull {self.MODEL_NAME}'"
            )
            return

        # Generar un embedding de prueba (como query)
        try:
            _ = self.generate_embedding("warmup test", is_query=True)
            logger.info("✓ Ollama configurado correctamente")
        except Exception as e:
            logger.error(f"✗ Error en warmup: {e}")

    def is_model_loaded(self) -> bool:
        """
        Verifica si Ollama está disponible.
        """
        return self._check_ollama()


# Instancia global singleton
embedding_service = EmbeddingService()
