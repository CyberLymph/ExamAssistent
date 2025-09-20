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
    payload = {"content": body.get("content", "")}

    
    if "attachment" in body:# falls attachment im Request enthalten ist
        payload["attachment"] = body["attachment"]

    r = requests.post(f"{FASTAPI_BASE}/sendApiMessage", json=payload)
    if r.status_code >= 400:
        return JsonResponse({"error": f"FastAPI error {r.status_code}", "details": r.text}, status=502)

    data = r.json()
    return JsonResponse({"reply": data.get("reply")})



@require_POST
def api_attachment(request):
    body = json.loads(request.body.decode("utf-8"))
    r = requests.post(f"{FASTAPI_BASE}/send-attachement", json=body)
    if r.status_code >= 400:
        return JsonResponse({"error": f"FastAPI error {r.status_code}", "details": r.text}, status=502)
    try:
        data = r.json()
    except ValueError:
        return JsonResponse({"error": "Invalid JSON from FastAPI"}, status=502)
    return JsonResponse(data, safe=isinstance(data, dict))

