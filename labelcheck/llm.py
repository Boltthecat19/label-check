"""Optional AI assist. No-op unless LLM_BASE_URL is set. Filled in by the batch task."""

import os


def get_llm():
    if not os.environ.get("LLM_BASE_URL"):
        return None
    return None
