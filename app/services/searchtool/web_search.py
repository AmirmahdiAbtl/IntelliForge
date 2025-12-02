import logging
from typing import List, Tuple

import asyncio
from .link_search import LinkSearch
from .scraper import Scraper
from .vector_database import VectorDatabase
import time

logger = logging.getLogger(__name__)

# Constants
CHUNK_SIZE = 1200  # Increased for better context with EmbeddingGemma (max 2048 tokens)
CHUNK_OVERLAP = 200  # More overlap for continuity
SEARCH_TOP_K = 15  # More initial results for reranking
RERANK_TOP_K = 5   # Final results after reranking


class WebSearch:
    """Complete web search service: search -> crawl -> process -> store"""
    
    def __init__(self, enable_rerank: bool = True, chunk_size: int = CHUNK_SIZE, embedding_model : str = "minilm"):
        """Initialize web search components"""
        self.link_search = LinkSearch()
        self.scraper = Scraper()
        # Initialize vector database with better configuration
        # self.vector_db = VectorDatabase(
        #     chunk_size=chunk_size,
        #     chunk_overlap=CHUNK_OVERLAP,
        #     enable_rerank=enable_rerank
        # )
        self.vector_db = VectorDatabase(embedding_model_key=embedding_model)

    async def search_and_crawl(self, 
                               query: str, 
                               num_results: int = 10, 
                               page: int = 1, 
                               before: str = None, 
                               after: str = None, 
                               backend: str = "mullvad_google"):
        """
        Search for URLs and crawl them
        
        Args:
            query: Search query
            num_results: Number of search results to crawl
            
        Returns:
            List of crawl results
            List of searched results
        """
        # Step 1: Search for URLs
        search_results = await self.link_search.search(query = query, 
                                             num_results = num_results, 
                                             page = page, 
                                             before = before, 
                                             after = after, 
                                             backend = backend)
        urls = []
        if search_results:
            urls = [result["href"] for result in search_results]
            print(f"DDGS returned {len(urls)} URLs")
        
        if not urls:
            logger.warning("No URLs found from search")
            return [], []
        
        # Step 2: Crawl the URLs
        results = await self.scraper.crawl(urls, query)
        
        if not results:
            logger.warning("No successful crawls")
            return [], urls
        
        logger.info(f"Successfully crawled {len(results)} pages")
        return results, urls
    
    def process_and_store(self, crawl_results: List) -> int:
        """
        Process crawl results and store in vector database
        
        Args:
            crawl_results: List of CrawlResult objects
            
        Returns:
            Number of documents stored
        """
        # Clear existing data and initialize
        self.vector_db.clear()
        self.vector_db.initialize()
        self.vector_db.load_embedding_model()
        
        all_documents = []
        all_metadata = []
        
        for result in crawl_results:
            if not result.markdown or not result.markdown.fit_markdown:
                continue
            
            try:
                # Extract content directly from markdown - let vector_db handle chunking
                content = result.markdown.strip()
                
                if len(content) > 100:  # Filter out very short content
                    all_documents.append(content)
                    all_metadata.append({
                        "source": result.url,
                        "title": getattr(result, 'title', 'Unknown'),
                        "content_length": len(content),
                        "timestamp": getattr(result, 'timestamp', None)
                    })
                        
            except Exception as e:
                logger.error(f"Error processing {result.url}: {str(e)}")
                continue
        
        if all_documents:
            # Let vector database handle chunking automatically
            self.vector_db.add_documents(
                all_documents, 
                all_metadata,
                auto_chunk=True  # Use vector_db's smart chunking
            )
            
            # Get actual number of chunks stored
            stats = self.vector_db.get_stats()
            num_chunks = stats['total_documents']
            
            logger.info(f"Processed {len(all_documents)} documents into {num_chunks} chunks")
            return num_chunks
        
        return 0
    
    def search_context(self, query: str, k: int = 10) -> Tuple[List[str], List[dict], List[float]]:
        """
        Search for relevant context from stored documents with enhanced results
        
        Args:
            query: Search query
            k: Number of top results to return
            
        Returns:
            Tuple of (documents, metadata, scores)
        """
        documents, metadata, scores = self.vector_db.search(
            query, 
            k=k,
            rerank=True,  # Enable reranking for better results
            initial_k_multiplier=3,  # Get more candidates for reranking
            score_threshold=0.3  # Lower threshold for more results
        )
        
        # Log search quality for debugging
        if scores:
            logger.info(f"Search quality - Top score: {scores[0]:.4f}, Avg score: {sum(scores)/len(scores):.4f}")
        
        return documents, metadata, scores
    
    def clear(self):
        """Clear the vector database"""
        self.vector_db.clear()
    
    def get_database_stats(self) -> dict:
        """Get statistics about the vector database"""
        return self.vector_db.get_stats()
    
    def update_chunk_configuration(self, chunk_size: int, chunk_overlap: int = None):
        """Update chunking configuration"""
        self.vector_db.update_chunk_size(chunk_size, chunk_overlap)
        
    def get_stored_documents_count(self) -> int:
        """Get the number of stored document chunks"""
        stats = self.vector_db.get_stats()
        return stats.get('total_documents', 0)

    async def search_tool(self,
                          query: str, 
                          num_results: int = 10, 
                          page: int = 1, 
                          before: str = None, 
                          after: str = None, 
                          backend: str = "google",
                          advanced: bool = True):
        """
        Complete search tool: search -> crawl -> process -> store
        
        Args:
            query: Search query
            num_results: Number of search results to crawl
            page: Search results page number
            before: Optional date string to filter results before this date (YYYY-MM-DD)
            after: Optional date string to filter results after this date (YYYY-MM-DD)
            backend: Search Engine to use (default: "google")
            advanced: Whether to use advanced processing with vector DB
            
        Returns:
            Tuple of (relevant documents, urls)
        """
        import mlflow
        
        if not advanced:
            search_results = await self.link_search.search(query = query, 
                                             num_results = num_results, 
                                             page = page, 
                                             before = before, 
                                             after = after, 
                                             backend = backend)
            if search_results:
                urls = [result["href"] for result in search_results]
                body = [result["body"] for result in search_results if "body" in result]
                return body, urls
        else:
            # Advanced search without MLflow tracking for simplicity
            relavent_docs = []
            urls = []
            
            try:
                # Step 1 & 2: Search and Crawl
                crawl_results, urls = await self.search_and_crawl(query, num_results, page, before, after, backend)
                
                if not crawl_results:
                    logger.warning("No crawl results to process")
                    return [], []
                
                print(f"Found {len(urls)} URLs to process")
                
                # Step 3: Process and Store
                store_start = time.time()
                num_stored = self.process_and_store(crawl_results)
                store_end = time.time()
                store_time = store_end - store_start
                print(f"Storing {num_stored} documents took {store_time:.2f} seconds")
                
                # Step 4: search_context (retrieval + reranking)
                search_start = time.time()
                relavent_docs, relavent_metadata, scores = self.search_context(query, k=5)
                search_end = time.time()
                search_time = search_end - search_start
                print(f"Searching context took {search_time:.2f} seconds")
                
                print(f"Retrieved {len(relavent_docs)} relevant documents")
                    
            except Exception as e:
                logger.error(f"Error in search tool: {str(e)}")
                import traceback
                traceback.print_exc()
            
            return relavent_docs, urls