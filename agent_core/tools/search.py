from datetime import datetime
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from tavily import TavilyClient
from agent_core.config import TAVILY_API_KEY


class SearchInput(BaseModel):
    query: str = Field(description="Search query. Do not hardcode years - the current year is appended automatically.")


@tool(args_schema=SearchInput)
def web_search(query: str) -> str:
    """Search the web for current information using Tavily. Current year is appended automatically - never hardcode a year in your query."""
    client = TavilyClient(api_key=TAVILY_API_KEY)
    year = datetime.now().year
    full_query = f"{query} {year}"
    try:
        results = client.search(full_query, max_results=5)
        if not results.get("results"):
            return "No results found."
        return "\n\n".join(
            f"{r['title']}\n{r['url']}\n{r['content']}"
            for r in results["results"]
        )
    except Exception as e:
        return f"Search failed: {e}"
