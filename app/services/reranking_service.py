"""Reranking service for improving retrieval quality"""
import os
from typing import List, Tuple, Dict, Any
from sentence_transformers import CrossEncoder
from langchain_core.documents import Document
from app.config import config


class RerankingService:
    """Handle document reranking operations"""
    
    def __init__(self):
        self._reranker = None
        self.model_name = config.DEFAULT_RERANKER_MODEL
    
    @property
    def reranker(self):
        """Lazy load the reranker model"""
        if self._reranker is None:
            try:
                print(f"Loading reranker model: {self.model_name}")
                self._reranker = CrossEncoder(self.model_name)
                print("Reranker model loaded successfully")
            except Exception as e:
                print(f"Failed to load reranker model: {e}")
                print("Reranking will be disabled")
                self._reranker = None
        return self._reranker
    
    def rerank_documents(self, query: str, documents: List[Document], 
                        top_k: int = None) -> List[Document]:
        """
        Rerank documents based on relevance to query
        
        Args:
            query: The search query
            documents: List of retrieved documents
            top_k: Number of top documents to return (default from config)
            
        Returns:
            List of reranked documents
        """
        if not config.ENABLE_RERANKING or not self.reranker or not documents:
            return documents[:top_k] if top_k else documents
        
        try:
            # Prepare query-document pairs for reranking
            pairs = [[query, doc.page_content] for doc in documents]
            
            # Get relevance scores
            scores = self.reranker.predict(pairs)
            
            # Create document-score pairs and sort by score (descending)
            doc_scores = list(zip(documents, scores))
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Extract reranked documents
            reranked_docs = [doc for doc, score in doc_scores]
            
            # Apply top_k limit
            if top_k:
                reranked_docs = reranked_docs[:top_k]
            
            # Add reranking scores to metadata for debugging
            for i, (doc, score) in enumerate(zip(reranked_docs, [s for _, s in doc_scores[:len(reranked_docs)]])):
                if not hasattr(doc, 'metadata') or doc.metadata is None:
                    doc.metadata = {}
                doc.metadata['rerank_score'] = float(score)
                doc.metadata['rerank_position'] = i + 1
            
            print(f"Reranked {len(documents)} documents, returning top {len(reranked_docs)}")
            return reranked_docs
            
        except Exception as e:
            print(f"Error during reranking: {e}")
            print("Falling back to original document order")
            return documents[:top_k] if top_k else documents
    
    def set_reranker_model(self, model_name: str):
        """Change the reranker model"""
        if model_name != self.model_name:
            self.model_name = model_name
            self._reranker = None  # Force reload on next access
            print(f"Reranker model changed to: {model_name}")


# Singleton instance
reranking_service = RerankingService()
