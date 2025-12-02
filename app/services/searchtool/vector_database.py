import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Union

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer, CrossEncoder

logger = logging.getLogger(__name__)

# Constants
# Available embedding models with their configurations
EMBEDDING_MODELS = {
    "gemma": {
        "model_name": "google/embeddinggemma-300m",
        "dimension": 768,
        "chunk_size": 1200,  # Optimized for EmbeddingGemma (max 2048 tokens)
        "description": "High-quality Gemma embedding model"
    },
    "minilm": {
        "model_name": "sentence-transformers/all-MiniLM-L6-v2", 
        "dimension": 384,
        "chunk_size": 512,  # Optimized for MiniLM-L6
        "description": "Fast and efficient MiniLM-L6-v2 model"
    },
    "bge": {
        "model_name": "BAAI/bge-base-en-v1.5",
        "dimension": 768,
        "chunk_size": 512,  # Optimized for BGE small
        "description": "BGE Small English embedding model"
    }
}

DEFAULT_EMBEDDING_MODEL_KEY = "gemma"  # Default to Gemma
DEFAULT_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_TOP_K = 10
DEFAULT_CHUNK_OVERLAP = 50


class VectorDatabase:
    """Manages FAISS vector store with reranking and configurable chunking"""
    
    def __init__(
        self, 
        embedding_model_key: str = DEFAULT_EMBEDDING_MODEL_KEY,
        dimension: int = None,
        chunk_size: int = None,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        enable_rerank: bool = True,
        rerank_model_name: str = DEFAULT_RERANK_MODEL
    ):
        # Validate and set embedding model configuration
        if embedding_model_key not in EMBEDDING_MODELS:
            raise ValueError(f"Invalid embedding model key: {embedding_model_key}. "
                           f"Available models: {list(EMBEDDING_MODELS.keys())}")
        
        self.embedding_model_key = embedding_model_key
        self.model_config = EMBEDDING_MODELS[embedding_model_key]
        
        # Set dimensions and chunk size from model config if not provided
        self.dimension = dimension or self.model_config["dimension"]
        self.chunk_size = chunk_size or self.model_config["chunk_size"]
        self.chunk_overlap = chunk_overlap
        self.enable_rerank = enable_rerank
        self.rerank_model_name = rerank_model_name
        
        self.index: Optional[faiss.Index] = None
        self.documents: List[str] = []
        self.metadata: List[Dict] = []
        self.embedding_model: Optional[SentenceTransformer] = None
        self.rerank_model: Optional[CrossEncoder] = None
        self.is_embedding_gemma: bool = False
        
    def initialize(self):
        """Initialize or reset the FAISS index"""
        print("Initializing FAISS index")
        # self.index = faiss.IndexFlatIP(self.dimension)
        self.index = faiss.IndexHNSWFlat(self.dimension, 32, faiss.METRIC_INNER_PRODUCT)
        self.documents = []
        self.metadata = []
        
    def load_embedding_model(self, model_name: str = None):
        """Load embedding model with caching"""
        if self.embedding_model is None:
            # Use configured model if no model_name provided
            model_to_load = model_name or self.model_config["model_name"]
            print(f"Loading embedding model: {model_to_load} ({self.model_config['description']})")
            self.embedding_model = SentenceTransformer(model_to_load, trust_remote_code=True)
            # Check if this is EmbeddingGemma which has special methods
            self.is_embedding_gemma = "embeddinggemma" in model_to_load.lower()
            print(f"EmbeddingGemma model detected: {self.is_embedding_gemma}")
        return self.embedding_model
    
    def load_rerank_model(self):
        """Load reranking model (CrossEncoder)"""
        if self.rerank_model is None and self.enable_rerank:
            print(f"Loading rerank model: {self.rerank_model_name}")
            self.rerank_model = CrossEncoder(self.rerank_model_name)
        return self.rerank_model
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings near the chunk boundary
                chunk_text = text[start:end]
                last_period = chunk_text.rfind('.')
                last_newline = chunk_text.rfind('\n')
                last_boundary = max(last_period, last_newline)
                
                if last_boundary > self.chunk_size * 0.5:  # Don't break too early
                    end = start + last_boundary + 1
            
            chunks.append(text[start:end].strip())
            start = end - self.chunk_overlap
        
        return chunks
    
    def add_documents(
        self, 
        documents: List[str], 
        metadatas: List[Dict],
        auto_chunk: bool = True
    ):
        """
        Add documents to the vector store
        
        Args:
            documents: List of documents to add
            metadatas: List of metadata dictionaries
            auto_chunk: If True, automatically chunk documents based on chunk_size
        """
        if not documents:
            logger.warning("No documents to add")
            return
            
        if self.embedding_model is None:
            self.load_embedding_model()
            
        if self.index is None:
            self.initialize()
        
        # Chunk documents if enabled
        chunked_docs = []
        chunked_metadata = []
        
        if auto_chunk:
            for doc, meta in zip(documents, metadatas):
                chunks = self.chunk_text(doc)
                chunked_docs.extend(chunks)
                
                # Add chunk information to metadata
                for i, chunk in enumerate(chunks):
                    chunk_meta = meta.copy()
                    chunk_meta.update({
                        'chunk_id': i,
                        'total_chunks': len(chunks),
                        'original_doc': doc[:100] + '...' if len(doc) > 100 else doc
                    })
                    chunked_metadata.append(chunk_meta)
        else:
            chunked_docs = documents
            chunked_metadata = metadatas
        
        # Batch encode for better performance
        print(f"Encoding {len(chunked_docs)} documents/chunks")
        
        if self.is_embedding_gemma:
            # Use EmbeddingGemma's specialized document encoding
            try:
                embeddings = self.embedding_model.encode_document(
                    chunked_docs,
                    batch_size=16,  # Smaller batch for larger model
                    show_progress_bar=False,
                    convert_to_tensor=False,
                    normalize_embeddings=True
                )
            except Exception as e:
                logger.warning(f"EmbeddingGemma encode_document failed: {e}, falling back to standard encode")
                embeddings = self.embedding_model.encode(
                    chunked_docs,
                    batch_size=16,
                    show_progress_bar=False,
                    convert_to_tensor=False,
                    normalize_embeddings=True
                )
        else:
            # Standard sentence transformers encoding
            embeddings = self.embedding_model.encode(
                chunked_docs,
                batch_size=32,
                show_progress_bar=False,
                convert_to_tensor=False,
                normalize_embeddings=True
            )
        embeddings = np.array(embeddings).astype('float32')
        
        # Add to index
        self.index.add(embeddings)
        self.documents.extend(chunked_docs)
        self.metadata.extend(chunked_metadata)
        
        print(f"Added {len(chunked_docs)} documents. Total: {len(self.documents)}")
    
    def rerank_results(
        self, 
        query: str, 
        documents: List[str], 
        metadatas: List[Dict],
        top_k: int
    ) -> Tuple[List[str], List[Dict], List[float]]:
        """
        Rerank search results using CrossEncoder
        
        Args:
            query: Search query
            documents: List of candidate documents
            metadatas: List of metadata for documents
            top_k: Number of top results to return
            
        Returns:
            Tuple of (reranked_docs, reranked_metadata, rerank_scores)
        """
        if not documents:
            return [], [], []
        
        # Load rerank model if needed
        if self.rerank_model is None:
            self.load_rerank_model()
        
        # Create query-document pairs
        pairs = [[query, doc] for doc in documents]
        
        # Get rerank scores
        print(f"Reranking {len(documents)} documents")
        scores = self.rerank_model.predict(pairs)
        
        # Sort by score
        sorted_indices = np.argsort(scores)[::-1][:top_k]
        
        reranked_docs = [documents[i] for i in sorted_indices]
        reranked_metadata = [metadatas[i] for i in sorted_indices]
        rerank_scores = [float(scores[i]) for i in sorted_indices]
        
        print(f"Reranking complete. Top score: {rerank_scores[0]:.4f}")
        return reranked_docs, reranked_metadata, rerank_scores
    
    def search(
        self, 
        query: str, 
        k: int = DEFAULT_TOP_K,
        rerank: Optional[bool] = None,
        initial_k_multiplier: int = 3,
        score_threshold: float = 0.3
    ) -> Tuple[List[str], List[Dict], Optional[List[float]]]:
        """
        Search for similar documents with optional reranking
        
        Args:
            query: Search query
            k: Number of results to return
            rerank: Whether to rerank results (None = use default)
            initial_k_multiplier: Multiplier for initial retrieval before reranking
            score_threshold: Minimum similarity score threshold
            
        Returns:
            Tuple of (documents, metadata, scores)
        """
        try:
            import mlflow
            use_mlflow = True
        except ImportError:
            use_mlflow = False
        
        if self.index is None or not self.documents:
            logger.warning("Index is empty")
            return [], [], []
            
        if self.embedding_model is None:
            self.load_embedding_model()
        
        # Determine if reranking should be used
        use_rerank = rerank if rerank is not None else self.enable_rerank
        
        # Use context manager properly for MLflow span
        if use_mlflow:
            span_context = mlflow.start_span("vector_db_search")
        else:
            span_context = None
        
        # If using MLflow, enter the context
        if span_context:
            span = span_context.__enter__()
            span.set_inputs({
                "query": query,
                "k": k,
                "use_rerank": use_rerank,
                "embedding_model": self.embedding_model_key
            })
        
        try:
            # Encode query
            if self.is_embedding_gemma:
                # Use EmbeddingGemma's specialized query encoding
                try:
                    query_embedding = self.embedding_model.encode_query(
                        query,
                        convert_to_tensor=False,
                        normalize_embeddings=True
                    )
                    # EmbeddingGemma returns single vector, not list
                    if len(query_embedding.shape) == 1:
                        query_embedding = query_embedding[None, :]  # Add batch dimension
                except Exception as e:
                    logger.warning(f"EmbeddingGemma encode_query failed: {e}, falling back to standard encode")
                    query_embedding = self.embedding_model.encode(
                        [query],
                        convert_to_tensor=False,
                        normalize_embeddings=True
                    )
            else:
                # Standard sentence transformers encoding
                query_embedding = self.embedding_model.encode(
                    [query],
                    convert_to_tensor=False,
                    normalize_embeddings=True
                )
            query_embedding = np.array(query_embedding).astype('float32')
            
            # Retrieve more candidates if reranking
            retrieval_k = k * initial_k_multiplier if use_rerank else k
            retrieval_k = min(retrieval_k, len(self.documents))
            
            # Search
            scores, indices = self.index.search(query_embedding, retrieval_k)
            
            # Filter results by relevance score
            results = []
            result_metadata = []
            initial_scores = []
            
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.documents) and score > score_threshold:
                    results.append(self.documents[idx])
                    result_metadata.append(self.metadata[idx])
                    initial_scores.append(float(score))
            
            print(f"Initial retrieval found {len(results)} relevant documents")
            
            # Log initial retrieval results
            if use_mlflow and span_context:
                span.set_attribute("initial_retrieval_count", len(results))
                span.set_attribute("initial_retrieval_avg_score", 
                                 sum(initial_scores) / len(initial_scores) if initial_scores else 0)
                # Log top initial results
                for i, (doc, meta, score) in enumerate(zip(results[:5], result_metadata[:5], initial_scores[:5])):
                    span.set_attribute(f"initial_doc_{i}_score", score)
                    span.set_attribute(f"initial_doc_{i}_source", meta.get("source", "unknown"))
            
            # Rerank if enabled
            if use_rerank and results:
                results, result_metadata, rerank_scores = self.rerank_results(
                    query, results, result_metadata, k
                )
                
                # Log reranking results
                if use_mlflow and span_context:
                    span.set_attribute("reranking_applied", True)
                    span.set_attribute("reranked_count", len(results))
                    span.set_attribute("reranked_avg_score", 
                                     sum(rerank_scores) / len(rerank_scores) if rerank_scores else 0)
                    # Log top reranked results
                    for i, (doc, meta, score) in enumerate(zip(results, result_metadata, rerank_scores)):
                        span.set_attribute(f"reranked_doc_{i}_score", score)
                        span.set_attribute(f"reranked_doc_{i}_source", meta.get("source", "unknown"))
                        span.set_attribute(f"reranked_doc_{i}_preview", doc[:150] + "...")
                    
                    span.set_outputs({
                        "documents": results,
                        "metadata": result_metadata,
                        "scores": rerank_scores,
                        "reranking_applied": True
                    })
                
                return results, result_metadata, rerank_scores
            else:
                # Return top k without reranking
                results = results[:k]
                result_metadata = result_metadata[:k]
                initial_scores = initial_scores[:k]
                
                if use_mlflow and span_context:
                    span.set_attribute("reranking_applied", False)
                    span.set_outputs({
                        "documents": results,
                        "metadata": result_metadata,
                        "scores": initial_scores,
                        "reranking_applied": False
                    })
                
                return results, result_metadata, initial_scores
        finally:
            # Clean up span context if it exists
            if span_context:
                span_context.__exit__(None, None, None)
    
    def update_chunk_size(self, chunk_size: int, chunk_overlap: int = None):
        """
        Update chunk size configuration
        
        Args:
            chunk_size: New chunk size
            chunk_overlap: New chunk overlap (optional)
        """
        self.chunk_size = chunk_size
        if chunk_overlap is not None:
            self.chunk_overlap = chunk_overlap
        print(f"Updated chunk size to {chunk_size} with overlap {self.chunk_overlap}")
    
    def get_stats(self) -> Dict:
        """Get statistics about the vector database"""
        return {
            'total_documents': len(self.documents),
            'embedding_model_key': self.embedding_model_key,
            'embedding_model_name': self.model_config["model_name"],
            'embedding_model_description': self.model_config["description"],
            'dimension': self.dimension,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'rerank_enabled': self.enable_rerank,
            'rerank_model': self.rerank_model_name if self.enable_rerank else None,
            'embedding_model_loaded': self.embedding_model is not None,
            'rerank_model_loaded': self.rerank_model is not None
        }
    
    @staticmethod
    def get_available_models() -> Dict:
        """Get information about available embedding models"""
        return EMBEDDING_MODELS.copy()
    
    def switch_embedding_model(self, new_model_key: str):
        """
        Switch to a different embedding model
        
        Args:
            new_model_key: Key of the new embedding model to use
            
        Note: This will clear the current index since dimensions may differ
        """
        if new_model_key not in EMBEDDING_MODELS:
            raise ValueError(f"Invalid embedding model key: {new_model_key}. "
                           f"Available models: {list(EMBEDDING_MODELS.keys())}")
        
        if new_model_key != self.embedding_model_key:
            print(f"Switching from {self.embedding_model_key} to {new_model_key}")
            
            # Clear current state
            self.clear()
            
            # Update configuration
            self.embedding_model_key = new_model_key
            self.model_config = EMBEDDING_MODELS[new_model_key]
            self.dimension = self.model_config["dimension"]
            self.chunk_size = self.model_config["chunk_size"]
            
            # Clear loaded models to force reload
            self.embedding_model = None
            self.is_embedding_gemma = False
            
            print(f"Switched to {new_model_key}: {self.model_config['description']}")
    
    def clear(self):
        """Clear the vector store"""
        self.index = None
        self.documents = []
        self.metadata = []
        print("Cleared vector store")