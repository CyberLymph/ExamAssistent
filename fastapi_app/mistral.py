import os
from dotenv import load_dotenv
from mistralai import Mistral  # ✅ neue Client-Klasse

class MistralWrapper:
    def __init__(self, model: str = "mistral-small-latest"):
        load_dotenv()
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not found in .env")
        self.client = Mistral(api_key=api_key)
        self.model = model  # free-tier freundlich: mistral-small-latest

    def send_request(self, message: str) -> str:
        resp = self.client.chat.complete(
            model=self.model,
            messages=[{"role": "user", "content": message}],
        )
        return resp.choices[0].message.content