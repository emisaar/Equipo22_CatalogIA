"""
Servicio de generación de embeddings para productos usando Sentence Transformers.
"""
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import logging
import os

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Servicio singleton para generar embeddings de texto usando Sentence Transformers.

    Utiliza el modelo 'paraphrase-multilingual-MiniLM-L12-v2' que:
    - Soporta múltiples idiomas (incluyendo español)
    - Genera vectores de 384 dimensiones
    - Es 5x más pequeño y 2x más rápido que mpnet-base
    - Optimizado para e-commerce y búsquedas semánticas
    """

    _instance = None
    _model: Optional[SentenceTransformer] = None

    # Modelo más ligero y rápido
    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIMENSION = 384  # Reducido de 768 a 384

    # Directorio para cachear el modelo localmente
    CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models_cache")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # El modelo se cargará solo cuando se necesite por primera vez
        if not os.path.exists(self.CACHE_DIR):
            os.makedirs(self.CACHE_DIR, exist_ok=True)
            logger.info(f"Directorio de caché creado: {self.CACHE_DIR}")

    def _load_model(self):
        """
        Carga el modelo solo cuando se necesita (lazy loading).
        """
        if self._model is None:
            logger.info(f"Cargando modelo de embeddings: {self.MODEL_NAME}")
            logger.info(f"Usando directorio de caché: {self.CACHE_DIR}")

            # Cargar modelo con caché local
            self._model = SentenceTransformer(
                self.MODEL_NAME,
                cache_folder=self.CACHE_DIR
            )
            logger.info("Modelo de embeddings cargado exitosamente")

    def generate_embedding(self, text: str) -> List[float]:
        """
        Genera un embedding para un texto dado.

        Args:
            text: Texto a convertir en embedding

        Returns:
            Lista de floats representando el vector de embedding (384 dimensiones)
        """
        # Lazy loading: cargar modelo solo cuando se necesita
        self._load_model()

        if not text or not text.strip():
            # Retornar vector de ceros si el texto está vacío
            return [0.0] * self.EMBEDDING_DIMENSION

        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

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
            Lista de floats representando el vector de embedding (384 dimensiones)
        """
        # Construir texto combinado ponderando campos importantes
        parts = []

        # Título es el más importante, lo incluimos 2 veces
        if title:
            parts.append(title)
            parts.append(title)

        # Marca (importante para búsqueda)
        if brand:
            parts.append(f"Marca: {brand}")

        # Descripción
        if description:
            parts.append(description)

        # Categoría
        if category:
            parts.append(f"Categoría: {category}")

        # Color
        if color:
            parts.append(f"Color: {color}")

        combined_text = " ".join(parts)
        return self.generate_embedding(combined_text)

    def warmup(self):
        """
        Pre-carga el modelo para evitar latencia en la primera petición.
        Se puede llamar en el startup de la aplicación.
        """
        logger.info("Iniciando warmup del modelo de embeddings...")
        self._load_model()
        # Generar un embedding de prueba para asegurar que todo funciona
        _ = self.generate_embedding("warmup test")
        logger.info("Warmup completado")

    def is_model_loaded(self) -> bool:
        """
        Verifica si el modelo ya está cargado en memoria.
        """
        return self._model is not None


# Instancia global singleton
embedding_service = EmbeddingService()
