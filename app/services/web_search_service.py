"""Web search service for chat integration"""
import asyncio
from typing import List, Tuple
from app.services.searchtool.web_search import WebSearch


class WebSearchService:
    """Service to handle web search integration with chat"""
    
    def __init__(self):
        self.web_search = WebSearch(embedding_model="minilm")
    
    async def search_and_get_context(self, query: str, num_results: int = 3) -> Tuple[str, List[str]]:
        """
        Search the web and return relevant context for LLM
        
        Args:
            query: User's search query
            num_results: Number of search results to process (default: 3)
            
        Returns:
            Tuple of (relevant_context, source_urls)
        """
        try:
            # Search and get relevant documents
            relevant_docs, urls = await self.web_search.search_tool(
                query, 
                num_results=num_results, 
                page=1, 
                backend="auto", 
                advanced=True
            )
            
            if not relevant_docs:
                return "No relevant web search results found.", []
            
            # Take the top 2-3 most relevant documents and combine them
            top_docs = relevant_docs[:min(3, len(relevant_docs))]
            combined_content = "\n\n".join(top_docs)
            
            # Limit context length to prevent token overflow
            max_context_length = 3000  # Increased for better context
            if len(combined_content) > max_context_length:
                combined_content = combined_content[:max_context_length] + "..."
            
            # Format context for LLM with stronger emphasis
            search_context = f"""LIVE WEB SEARCH RESULTS (December 2025) for: "{query}"

                Current Information Found:
                {combined_content}

                Sources: {', '.join(urls[:3])}

                This information is from live web search and should be prioritized over training data.
            """
            
            return search_context.strip(), urls[:3]
            
        except Exception as e:
            print(f"Web search error: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Web search encountered an error: {str(e)}", []
    
    def search_and_get_context_sync(self, query: str, num_results: int = 3) -> Tuple[str, List[str]]:
        """
        Synchronous wrapper for web search
        
        Args:
            query: User's search query  
            num_results: Number of search results to process (default: 3)
            
        Returns:
            Tuple of (relevant_context, source_urls)
        """
        try:
            # Run async function in new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self.search_and_get_context(query, num_results)
                )
                return result
            finally:
                loop.close()
        except Exception as e:
            print(f"Web search sync wrapper error: {str(e)}")
            return f"Web search encountered an error: {str(e)}", []


# Singleton instance
web_search_service = WebSearchService()