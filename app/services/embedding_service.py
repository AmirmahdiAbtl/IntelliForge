"""Embedding service for text embeddings"""
from langchain_huggingface import HuggingFaceEmbeddings
from app.config import config


class EmbeddingService:
    """Handle text embedding operations"""
    
    def __init__(self):
        self._embedding_model = None
    
    @property
    def embedding_model(self):
        """Lazy load embedding model"""
        if self._embedding_model is None:
            self._embedding_model = HuggingFaceEmbeddings(
                model_name=config.EMBEDDING_MODEL_NAME
            )
        return self._embedding_model
    
    def generate_embedding(self, text: str) -> list:
        """Generate embedding for text"""
        return self.embedding_model.embed_query(text)
    
    def generate_embeddings(self, texts: list) -> list:
        """Generate embeddings for multiple texts"""
        return self.embedding_model.embed_documents(texts)


# Singleton instance
embedding_service = EmbeddingService()
