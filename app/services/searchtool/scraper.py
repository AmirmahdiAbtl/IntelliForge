import logging
from typing import List

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.content_filter_strategy import BM25ContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.models import CrawlResult
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def extract_urls(text):
    """Extract and clean URLs from text input"""
    if not text:
        return []
    
    # Split by common separators and clean
    lines = re.split(r'[,\n\r;]+', text)
    urls = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Extract URLs using regex
        pattern = re.compile(
            r'\b((?:https?://|http://|www\.)[^\s,;()<>"]+|(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,6}(?:/[^\s,;()<>"]*)?)'
        )
        matches = pattern.findall(line)
        
        for match in matches:
            url = match.strip().strip('\'"<>(),.;:')
            if url.startswith("www."):
                url = "https://" + url
            
            try:
                parsed = urlparse(url)
                if parsed.scheme and parsed.netloc:
                    clean_url = parsed.geturl() if hasattr(parsed, "geturl") else url
                    if clean_url not in urls:  # Avoid duplicates
                        urls.append(clean_url)
            except Exception:
                continue  # Skip invalid URLs
                
    return urls

class Scraper:
    """Web scraper for extracting content from URLs"""
    
    def __init__(self):
        """Initialize scraper with optimized browser config"""
        self.custom_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
    
    async def crawl(self, urls: List[str], query: str = None) -> List[CrawlResult]:
        """
        Crawl web pages with optimized settings
        
        Args:
            urls: List of URLs to crawl
            query: Optional query for content filtering
            
        Returns:
            List of successful crawl results
        """
        if not urls:
            logger.warning("No URLs to crawl")
            return []
        
        # Setup content filter if query provided
        bm25_filter = None
        if query:
            bm25_filter = BM25ContentFilter(user_query=query, bm25_threshold=1.0)
        
        md_generator = DefaultMarkdownGenerator(content_filter=bm25_filter)
        
        # Browser configuration
        browser_config = BrowserConfig(
            headless=True,
            text_mode=True,
            light_mode=True,
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            headers=self.custom_headers
        )
        
        # Crawler configuration
        crawler_config = CrawlerRunConfig(
            markdown_generator=md_generator,
            excluded_tags=["nav", "footer", "header", "form", "img", "a"],
            only_text=True,
            exclude_social_media_links=True,
            keep_data_attributes=False,
            cache_mode=CacheMode.BYPASS,
            remove_overlay_elements=True,
            page_timeout=20000,  # 5 seconds timeout in milliseconds
        )
        
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                results = await crawler.arun_many(urls, config=crawler_config)
                successful = [r for r in results if r.success and r.markdown]
                logger.info(f"Successfully crawled {len(successful)}/{len(urls)} pages")
                return successful
                
        except Exception as e:
            logger.error(f"Crawling failed: {str(e)}")
            return []
