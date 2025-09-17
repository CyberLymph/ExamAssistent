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

    # Nur Text an FastAPI schicken (kein json.dumps von payload)
    r = requests.post(f"{FASTAPI_BASE}/sendApiMessage",
                      json={"content": content})

    if r.status_code >= 400:
        return JsonResponse({"error": f"FastAPI error {r.status_code}", "details": r.text}, status=502)

    data = r.json()
    # FastAPI liefert jetzt {"reply": "..."}
    return JsonResponse({"reply": data.get("reply")})


@require_POST
def api_attachment(request):
    body = json.loads(request.body.decode("utf-8"))
    r = requests.post(f"{FASTAPI_BASE}/send-attachement", json=body)
    if r.status_code >= 400:
        return JsonResponse({"error": f"FastAPI error {r.status_code}", "details": r.text}, status=502)
    return JsonResponse(r.json())
