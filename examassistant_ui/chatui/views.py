import json, requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie

FASTAPI_BASE = getattr(settings, "FASTAPI_BASE", "http://localhost:8000")



# ----------------- ExamAssistantChat UI --------------------
def chat_page(request):
    return render(request, "chatui/chat.html")


@require_POST
def api_message(request):
    body = json.loads(request.body.decode("utf-8"))
    payload = {
        "chat_id": body.get("chat_id"),            
        "content": body.get("content", ""),
        "attachment": body.get("attachment")
    }
    try:
        r = requests.post(
            f"{FASTAPI_BASE}/sendApiMessage",
            json=payload,
            timeout=30
        )
    except Exception as e:
        return JsonResponse({"error": f"FastAPI unreachable: {e}"}, status=502)

    if r.status_code >= 400:
        return JsonResponse({"error": f"FastAPI {r.status_code}", "details": r.text}, status=502)

    data = r.json()
    return JsonResponse({"reply": data.get("reply"), **{k: v for k, v in data.items() if k != "reply"}})




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






# -------- AufgabenGenerator ---------
@ensure_csrf_cookie
def wizard_page(request):
    return render(request, "chatui/wizard.html")

@ensure_csrf_cookie
def generator_page(request):
    return render(request, "chatui/generator.html")

@require_POST
def api_task_generate(request):
    body = json.loads(request.body.decode("utf-8"))
    r = requests.post(f"{FASTAPI_BASE}/task/generate", json=body, timeout=45)
    try:
        data = r.json()
    except ValueError:
        return JsonResponse({"error": "Invalid JSON from FastAPI", "raw": r.text}, status=502)
    if r.status_code >= 400:
        # echten Statuscode + Detail weitergeben
        return JsonResponse(data, status=r.status_code, safe=isinstance(data, dict))
    return JsonResponse(data)

@require_POST
def api_task_accept(request):
    body = json.loads(request.body.decode("utf-8"))
    r = requests.post(f"{FASTAPI_BASE}/task/accept", json=body, timeout=30)
    try:
        data = r.json()
    except ValueError:
        return JsonResponse({"error": "Invalid JSON from FastAPI", "raw": r.text}, status=502)
    if r.status_code >= 400:
        return JsonResponse(data, status=r.status_code, safe=isinstance(data, dict))
    return JsonResponse(data)

@require_POST
def api_task_export(request):
    body = json.loads(request.body.decode("utf-8"))
    r = requests.post(f"{FASTAPI_BASE}/task/export_pdf", json=body, timeout=60)
    try:
        data = r.json()
    except ValueError:
        return JsonResponse({"error": "Invalid JSON from FastAPI", "raw": r.text}, status=502)
    if r.status_code >= 400:
        return JsonResponse(data, status=r.status_code, safe=isinstance(data, dict))
    return JsonResponse(data)

@require_POST
def api_task_accepted_list(request):
    body = json.loads(request.body.decode("utf-8"))
    r = requests.post(f"{FASTAPI_BASE}/task/accepted_list", json=body, timeout=15)
    try:
        data = r.json()
    except ValueError:
        return JsonResponse({"error": "Invalid JSON from FastAPI", "raw": r.text}, status=502)
    if r.status_code >= 400:
        return JsonResponse(data, status=r.status_code, safe=isinstance(data, dict))
    return JsonResponse(data)


@require_POST
def api_task_reset_exam(request):
    body = json.loads(request.body.decode("utf-8"))
    r = requests.post(f"{FASTAPI_BASE}/task/reset_exam", json=body, timeout=15)
    if r.status_code >= 400:
        return JsonResponse({"error": f"FastAPI {r.status_code}", "details": r.text}, status=502)
    return JsonResponse(r.json())