import requests

url = "http://127.0.0.1:8000/sendApiMessage"
payload = {"content": "Nenne drei berühmte französische Käsesorten"}

res = requests.post(url, json=payload)
print(res.status_code, res.text)