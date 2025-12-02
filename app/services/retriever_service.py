"""Custom retriever with reranking capabilities"""
from typing import List, Dict, Any, Optional
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from pydantic import Field
from app.services.reranking_service import reranking_service
from app.config import config


class RerankingRetriever(BaseRetriever):
    """Custom retriever that implements reranking for better results"""
    
    base_retriever: Any = Field(...)
    top_k_retrieval: int = Field(default_factory=lambda: config.DEFAULT_TOP_K_RETRIEVAL)
    top_k_reranked: int = Field(default_factory=lambda: config.DEFAULT_TOP_K_RERANKED)
    enable_reranking: bool = Field(default_factory=lambda: config.ENABLE_RERANKING)
    
    def __init__(self, base_retriever, top_k_retrieval: int = None, 
                 top_k_reranked: int = None, enable_reranking: bool = True, **kwargs):
        """
        Initialize the reranking retriever
        
        Args:
            base_retriever: The base vector store retriever
            top_k_retrieval: Number of documents to retrieve initially
            top_k_reranked: Number of documents to return after reranking
            enable_reranking: Whether to enable reranking
        """
        super().__init__(
            base_retriever=base_retriever,
            top_k_retrieval=top_k_retrieval or config.DEFAULT_TOP_K_RETRIEVAL,
            top_k_reranked=top_k_reranked or config.DEFAULT_TOP_K_RERANKED,
            enable_reranking=enable_reranking and config.ENABLE_RERANKING,
            **kwargs
        )
        
        # Configure base retriever
        if hasattr(self.base_retriever, 'search_kwargs'):
            self.base_retriever.search_kwargs['k'] = self.top_k_retrieval
        elif hasattr(self.base_retriever, 'k'):
            self.base_retriever.k = self.top_k_retrieval
    
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        """Get relevant documents with reranking"""
        # Step 1: Retrieve initial set of documents
        try:
            # Try the new method first
            initial_docs = self.base_retriever._get_relevant_documents(
                query, run_manager=run_manager
            )
        except AttributeError:
            # Fall back to the old method if available
            try:
                initial_docs = self.base_retriever.get_relevant_documents(query)
            except AttributeError:
                # Last resort: use invoke method
                initial_docs = self.base_retriever.invoke(query)
        
        if not initial_docs:
            return []
        
        print(f"Initial retrieval: {len(initial_docs)} documents")
        
        # Step 2: Apply reranking if enabled
        if self.enable_reranking:
            reranked_docs = reranking_service.rerank_documents(
                query, initial_docs, self.top_k_reranked
            )
            print(f"After reranking: {len(reranked_docs)} documents")
            return reranked_docs
        else:
            # Just apply top_k limit without reranking
            return initial_docs[:self.top_k_reranked]
    
    def configure_retrieval(self, top_k_retrieval: int = None, 
                          top_k_reranked: int = None):
        """Update retrieval configuration"""
        if top_k_retrieval:
            self.top_k_retrieval = top_k_retrieval
            if hasattr(self.base_retriever, 'search_kwargs'):
                self.base_retriever.search_kwargs['k'] = top_k_retrieval
            elif hasattr(self.base_retriever, 'k'):
                self.base_retriever.k = top_k_retrieval
        
        if top_k_reranked:
            self.top_k_reranked = top_k_reranked


def create_reranking_retriever(vectorstore, top_k_retrieval: int = None,
                              top_k_reranked: int = None, 
                              enable_reranking: bool = True) -> RerankingRetriever:
    """Create a reranking retriever from a vector store"""
    base_retriever = vectorstore.as_retriever()
    return RerankingRetriever(
        base_retriever=base_retriever,
        top_k_retrieval=top_k_retrieval,
        top_k_reranked=top_k_reranked,
        enable_reranking=enable_reranking
    )
