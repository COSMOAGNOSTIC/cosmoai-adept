from typing import Any


def extract_text(content: Any) -> str:
    """
    Normalize LangGraph message content to a plain string.
    Handles: bare strings, content-block lists (Anthropic API format),
    and anything else by falling back to str().
    All callers use this - never assume content is already a string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


def chunk_for_discord(text: str, limit: int = 1900) -> list[str]:
    """
    Split text into Discord-safe chunks of at most `limit` characters.
    Splits on the last newline before the limit - never mid-word or
    mid-code-block. Discord's hard limit is 2000; 1900 gives headroom
    for any prefix the caller adds.
    """
    if len(text) <= limit:
        return [text]

    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    return chunks
