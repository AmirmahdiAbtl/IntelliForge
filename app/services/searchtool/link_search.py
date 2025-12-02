import logging
from typing import List, Dict, Set, Tuple

from ddgs import DDGS

logger = logging.getLogger(__name__)


class LinkSearch:
    """Search engine for finding relevant URLs"""
    
    def __init__(self, excluded_sites: List[str] = None):
        """
        Initialize link search
        
        Args:
            excluded_sites: List of domains to exclude from search results
        """
        self.excluded_sites = excluded_sites or [
            "youtube.com", 
            "britannica.com", 
            "vimeo.com", 
            "pinterest.com", 
            "github.com", 
            "github.blog"
        ]

    async def search(self, 
                     query: str, 
                     num_results: int = 30, 
                     page: int = 1, 
                     before: str = None, 
                     after: str = None,
                     backend: str = "mullvad_google"):
        """
        Search web and return URLs
        
        Args:
            query: Search query
            num_results: Maximum number of results to return
            page: Page number to retrieve (1-based)
            before: Optional date string to filter results before this date (YYYY-MM-DD)
            after: Optional date string to filter results after this date (YYYY-MM-DD)
            backend: Search Engine to use (default: "google")

        Returns:
            List of URLs
        """
        try:
            search_query = query
            if before:
                search_query += f" before:{before}"
            if after:
                search_query += f" after:{after}"
            # Build search query with exclusions
            
            # for site in self.excluded_sites:
            #     search_query += f" -site:{site}"
            

            print(f"DDGS search: '{search_query}' (max_results={num_results}, page={page}) - (before: {before}, after: {after})")
            results = DDGS().text(search_query, 
                                  max_results=num_results, 
                                  page=page, 
                                  backend=backend)

            if results:
                # urls = [result["href"] for result in results]
                # print(f"DDGS returned {len(urls)} URLs")
                return results
            
            print("No search results found")
            return []
            
        except Exception as e:
            print(f"Web search failed: {str(e)}")
            return []
    
    async def search_unique_urls(self, query: str, target_count: int, session_urls: Set[str], 
                                db, max_attempts: int = 6) -> Tuple[List[str], Dict]:
        """
        Optimized search for URLs using pagination to get more results with duplicate detection
        
        Args:
            query: Search query
            target_count: Number of unique URLs to find
            session_urls: Set of URLs already found in current session
            db: Database manager instance for duplicate checking
            max_attempts: Maximum search attempts/pages to try
            
        Returns:
            Tuple of (unique_urls_list, search_info_dict)
        """
        unique_urls = []
        attempt = 0
        total_urls_found = 0
        duplicates_skipped = 0
        results_per_page = 50  # DuckDuckGo returns max 50 results per page
        
        while len(unique_urls) < target_count and attempt < max_attempts:
            attempt += 1
            page = attempt  # Use attempt number as page number
            
            print(f"Attempt {attempt}: Searching DuckDuckGo page {page} (up to {results_per_page} results)...")
            
            try:
                results = await self.search(query, num_results=results_per_page, page=page)
                urls = [result["href"] for result in results] if results else []
                total_urls_found = len(urls)
                
                print(f"DuckDuckGo page {page} returned {len(urls)} links")
                
                # If no results on this page, stop searching
                if len(urls) == 0:
                    print(f"No more results found on page {page}")
                    break
                
                # Check for duplicates in both database and current session
                url_check_results = db.check_existing_urls(urls)
                
                # Filter duplicates
                seen_in_batch = set()
                batch_duplicates = 0
                new_unique_urls = []
                
                for url in urls:
                    # Check if URL exists in database, current session, or current batch
                    if (url_check_results.get(url, False) or 
                        url in session_urls or 
                        url in seen_in_batch or 
                        url in unique_urls):
                        duplicates_skipped += 1
                        batch_duplicates += 1
                        continue
                        
                    new_unique_urls.append(url)
                    seen_in_batch.add(url)
                    
                    if len(unique_urls) + len(new_unique_urls) >= target_count:
                        break

                print(f"Found {len(new_unique_urls)} unique URLs, {batch_duplicates} duplicates")

                unique_urls.extend(new_unique_urls)
                
                # Add to session URLs to avoid duplicates in later queries
                session_urls.update(new_unique_urls)
                
                # If we have enough unique URLs, stop
                if len(unique_urls) >= target_count:
                    break
                    
            except Exception as e:
                print(f"Search failed on page {page}: {str(e)}")
                break
        
        search_info = {
            "attempts": attempt,
            "total_found": total_urls_found,
            "duplicates_skipped": duplicates_skipped,
            "unique_found": len(unique_urls),
            "pages_searched": attempt
        }
        
        return unique_urls[:target_count], search_info
    
    async def search_urls_quick_mode(self, query: str, target_count: int, session_urls: Set[str], 
                                    db) -> Tuple[List[str], Dict]:
        """
        Quick search mode: Single page search only with duplicate detection
        
        Args:
            query: Search query
            target_count: Number of unique URLs to find
            session_urls: Set of URLs already found in current session
            db: Database manager instance for duplicate checking
            
        Returns:
            Tuple of (unique_urls_list, search_info_dict)
        """
        unique_urls = []
        duplicates_skipped = 0
        page = 1  # Only search first page in quick mode
        
        try:
            results = await self.search(query, num_results=50, page=page)  # Max 50 results from page 1
            urls = [result["href"] for result in results] if results else []
            total_urls_found = len(urls)
            print(f"DuckDuckGo page {page} returned {len(urls)} links")

            # Check for duplicates in both database and current session
            url_check_results = db.check_existing_urls(urls)
            
            # Filter duplicates
            seen_in_batch = set()
            
            for url in urls:
                # Check if URL exists in database, current session, or current batch
                if (url_check_results.get(url, False) or 
                    url in session_urls or 
                    url in seen_in_batch):
                    duplicates_skipped += 1
                    continue
                    
                unique_urls.append(url)
                seen_in_batch.add(url)
                
                if len(unique_urls) >= target_count:
                    break
            
            # Add to session URLs to avoid duplicates in later queries
            session_urls.update(unique_urls)

            print(f"Found {len(unique_urls)} unique URLs, {duplicates_skipped} duplicates")

        except Exception as e:
            print(f"Search failed: {str(e)}")
            total_urls_found = 0
        
        search_info = {
            "attempts": 1,
            "total_found": total_urls_found,
            "duplicates_skipped": duplicates_skipped,
            "unique_found": len(unique_urls),
            "pages_searched": 1
        }
        
        return unique_urls[:target_count], search_info