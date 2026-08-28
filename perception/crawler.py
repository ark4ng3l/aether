import asyncio
from typing import Dict, Any
from playwright.async_api import async_playwright
from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger

class StealthCrawler(BaseTool):
    """
    An asynchronous crawler using Playwright with stealth configurations
    to mimic human browsing behavior and avoid bot detection.
    """
    def __init__(self):
        super().__init__(name="stealth_crawler", description="Navigates to a URL and extracts page content.")

    async def execute(self, url: str) -> ToolResult:
        logger.info(f"Crawling: {url}")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                # Use a common User-Agent to look like a real browser
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                # Navigate to the URL with a timeout
                await page.goto(url, wait_until="networkidle", timeout=60000)

                # Extract text content and title
                content = await page.content() # Full HTML
                title = await page.title()

                await browser.close()
                return ToolResult(success=True, data={"title": title, "html": content})

        except Exception as e:
            logger.error(f"Crawler failed for {url}: {str(e)}")
            return ToolResult(success=False, data={}, error=str(e))

# Singleton instance to be registered in the registry
crawler = StealthCrawler()
