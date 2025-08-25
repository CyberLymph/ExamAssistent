import requests

base_url = "http://localhost:8000"

response = requests.get(base_url + "/ping")

print(response.content)