# fastapi_app/mistral.py

import os
from typing import Optional

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None  # optional

class MistralWrapper:
    """
    Robuster Wrapper:
    - Funktioniert auch ohne 'mistralai' Paket und ohne API-Key
    - Wirft KEINE Exceptions in der App (liefert Fallback-Text)
    """
    def __init__(self, model: str = "mistral-small-latest"):
        self.model = model
        self.client = None
        self._init_error: Optional[str] = None

        # .env laden (optional)
        if load_dotenv:
            try:
                load_dotenv()
            except Exception:
                pass

        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            self._init_error = "MISTRAL_API_KEY not set"
            return

        # Client laden (sanft)
        try:
            from mistralai import Mistral  # type: ignore
            self.client = Mistral(api_key=api_key)
        except Exception as e:
            self._init_error = f"mistralai init failed: {e}"
            self.client = None

    def send_request(self, prompt: str) -> str:
        """Nie Exception werfen – immer String zurückgeben."""
        # Fallback, wenn kein Client
        if self.client is None:
            head = "[LLM deaktiviert]" if self._init_error else "[LLM nicht initialisiert]"
            return f"{head}\nGrund: {self._init_error or 'unbekannt'}\n\nEcho:\n{prompt[:1200]}"

        # Regulärer Call
        try:
            resp = self.client.chat.complete(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            # Rückfall: nie crashen
            return f"[LLM Fehler: {e}]\n\nEcho:\n{prompt[:1200]}"
