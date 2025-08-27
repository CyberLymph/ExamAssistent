from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("OPEN_AI_API_KEY")
print(api_key)

client = OpenAI(api_key=api_key)



response = client.responses.create(
    model="gpt-3.5-turbo",
    input="Write a one-sentence bedtime story about a unicorn.",
    text={
        "verbosity": "medium"
    }
)

print(response.output_text)