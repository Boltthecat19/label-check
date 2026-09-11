"""Optional AI second opinion on REVIEW results.

Off unless LLM_BASE_URL is set. Talks to any OpenAI compatible chat endpoint: LM Studio on
a workstation, Azure OpenAI inside an agency boundary, or nothing at all. It never
changes a status, only adds one sentence to the note, and it fails silent on any error so
a blocked endpoint (Marcus's firewall) costs at most the 3 second timeout.
"""

import os

import httpx

from labelcheck.models import FieldResult

_SYSTEM = "You help a compliance agent compare an alcohol label to its application. Answer in one plain sentence."


class LlmAssist:
    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: float = 3.0, transport=None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.client = httpx.Client(timeout=timeout, transport=transport)

    def opinion(self, result: FieldResult, ocr_text: str) -> str | None:
        prompt = (
            f"Field: {result.field}. Application says: {result.expected!r}. Label text nearby: {result.found!r}. "
            f"Tool note: {result.note} Full label text (may contain OCR errors):\n{ocr_text[:1500]}\n"
            "Is the label value the same as the application value? One sentence."
        )
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            r = self.client.post(
                f"{self.base_url}/chat/completions", headers=headers,
                json={"model": self.model, "temperature": 0,
                      "messages": [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": prompt}]},
            )
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"].strip()
            return text.splitlines()[0][:300] if text else None
        except Exception:
            return None


def get_llm() -> LlmAssist | None:
    url = os.environ.get("LLM_BASE_URL", "").strip()
    if not url:
        return None
    return LlmAssist(url, os.environ.get("LLM_MODEL", "local-model"), os.environ.get("LLM_API_KEY", ""))
