import requests

base_url = "http://localhost:8000"

# Test /home
response = requests.get(base_url + "/home")
print("Home:", response.json())

# Test compare-pdfs (hier Dummy-Dateien anhängen)
with open("test1.pdf", "rb") as f1, open("test2.pdf", "rb") as f2:
    files = {
        "file1": ("test1.pdf", f1, "application/pdf"),
        "file2": ("test2.pdf", f2, "application/pdf"),
    }
    r = requests.post(base_url + "/compare-solutions", files=files)
    print("Compare PDFs:", r.json())
