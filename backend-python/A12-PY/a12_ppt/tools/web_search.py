from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup


async def web_search(query: str, max_results: int = 5) -> dict:
    if not query.strip():
        return {"query": query, "results": []}

    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {"User-Agent": "Mozilla/5.0 A12-PY/0.1"}
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
    except Exception as exc:
        return {"query": query, "results": [], "error": str(exc)}

    soup = BeautifulSoup(response.text, "html.parser")
    results: list[dict[str, str]] = []
    for item in soup.select(".result")[:max_results]:
        title_node = item.select_one(".result__title a")
        snippet_node = item.select_one(".result__snippet")
        if not title_node:
            continue
        results.append({
            "title": title_node.get_text(" ", strip=True),
            "url": title_node.get("href", ""),
            "snippet": snippet_node.get_text(" ", strip=True) if snippet_node else "",
        })
    return {"query": query, "results": results}
