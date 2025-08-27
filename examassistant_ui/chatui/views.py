import json, requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

FASTAPI_BASE = getattr(settings, "FASTAPI_BASE", "http://localhost:8000")

def chat_page(request):
    return render(request, "chatui/chat.html")

@require_POST
def api_message(request):
    body = json.loads(request.body.decode("utf-8"))
    content = body.get("content", "")
    payload = [
        {"role": "system", "content": "Du bist ein Klausur-Assistent. Antworte knapp und strukturiert."},
        {"role": "user", "content": content},
    ]
    r = requests.post(f"{FASTAPI_BASE}/sendApiMessage", json={"content": json.dumps(payload)})
    if r.status_code >= 400:
        return JsonResponse({"error": f"FastAPI error {r.status_code}", "details": r.text}, status=502)
    data = r.json()
    return JsonResponse({"reply": data.get("reply") or data.get("content") or data})

@require_POST
def api_attachment(request):
    body = json.loads(request.body.decode("utf-8"))
    r = requests.post(f"{FASTAPI_BASE}/send-attachement", json=body)
    if r.status_code >= 400:
        return JsonResponse({"error": f"FastAPI error {r.status_code}", "details": r.text}, status=502)
    return JsonResponse(r.json())
