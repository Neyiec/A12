from urllib.parse import parse_qs, quote_plus, urljoin, urlsplit

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
    seen_urls = set()
    for item in soup.select(".result"):
        title_node = item.select_one(".result__title a")
        snippet_node = item.select_one(".result__snippet")
        if not title_node:
            continue
        href = urljoin("https://duckduckgo.com", title_node.get("href") or "")
        try:
            target = urlsplit(href)
            if target.hostname in {"duckduckgo.com", "www.duckduckgo.com"}:
                href = (parse_qs(target.query).get("uddg") or [""])[0]
                target = urlsplit(href)
            if target.scheme not in {"http", "https"} or not target.hostname or target.username or target.password:
                continue
        except ValueError:
            continue
        if href in seen_urls:
            continue
        seen_urls.add(href)
        results.append({
            "title": title_node.get_text(" ", strip=True)[:160],
            "url": href,
            "snippet": snippet_node.get_text(" ", strip=True)[:500] if snippet_node else "",
        })
        if len(results) >= max_results:
            break
    return {"query": query, "results": results}
