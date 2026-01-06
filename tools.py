# tools.py
from tavily import TavilyClient
from config import TAVILY_API_KEY

tavily_client = TavilyClient(api_key=TAVILY_API_KEY)


def tavily_search_with_content(query: str, max_results: int = 5):
    """
    Uses Tavily's own crawler & cached page content.
    This avoids direct HTTP requests and bot-blocking issues.
    """
    response = tavily_client.search(
        query=query,
        search_depth="advanced",
        max_results=max_results,
        include_raw_content=True
    )

    results = []
    for item in response.get("results", []):
        raw = item.get("raw_content", "")
        if raw:
            results.append({
                "url": item.get("url"),
                "content": raw[:4000]  # safe token bound
            })

    return results
