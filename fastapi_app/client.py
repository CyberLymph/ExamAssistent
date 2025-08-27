import requests

base_url = "http://localhost:8000"

response = requests.get(base_url + "/home")

print(response.content)