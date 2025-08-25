# Please install OpenAI SDK first: `pip3 install openai`
from openai import OpenAI
from dotenv import load_dotenv
import os

class DeepSeekWrapper:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("DEEPSEEK_API_KEY")

        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    def send_request(self, message):
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=message,
            stream=False
        )
        print(response.choices[0].message.content)
        return response.choices[0].message.content
