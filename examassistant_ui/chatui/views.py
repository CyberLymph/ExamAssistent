# --- Standardbibliotheken ---
import json
import requests

# --- Django Framework ---
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

# --- Eigene Module ---
import files


FASTAPI_BASE = getattr(settings, "FASTAPI_BASE", "http://localhost:8000")

# ----------------- Compare UI --------------------
def compare(request):
    """Seite für den Vergleich (compare.html)"""
    return render(request, "chatui/compare.html")

# -------------------------------
# Lösung generieren (1 PDF hochladen)
# -------------------------------
@csrf_exempt
@require_POST
def api_generate_solution(request):
    pdf = request.FILES.get("pdf")
    if not pdf:
        return JsonResponse({"error": "Bitte eine PDF-Datei hochladen"}, status=400)

    files = {"pdf": (pdf.name, pdf, "application/pdf")}

    try:
        r = requests.post(f"{FASTAPI_BASE}/generate-solution", files=files, timeout=(10, 120))
    except Exception as e:
        return JsonResponse({"error": f"FastAPI unreachable: {e}"}, status=502)

    if r.status_code >= 400:
        return JsonResponse(
            {"error": f"FastAPI {r.status_code}", "details": r.text}, status=502
        )

    return JsonResponse(r.json())
# -------------------------------
# PDF-Upload löschen
# -------------------------------
@csrf_exempt
@require_POST  # <--- optional, falls du DELETE in fetch nutzt, kann auch @require_http_methods(["DELETE"]) sein
def api_delete_upload(request):
    chat_id = request.POST.get("chat_id", "default")
    doc_id = request.POST.get("doc_id")

    if not doc_id:
        return JsonResponse({"error": "doc_id fehlt"}, status=400)

    try:
        r = requests.delete(
            f"{FASTAPI_BASE}/delete-upload",
            data={"chat_id": chat_id, "doc_id": doc_id},
            timeout=(10, 30),
        )
    except Exception as e:
        return JsonResponse({"error": f"FastAPI unreachable: {e}"}, status=502)

    if r.status_code >= 400:
        return JsonResponse(
            {"error": f"FastAPI {r.status_code}", "details": r.text}, status=502
        )

    return JsonResponse(r.json())



# -------------------------------
# Musterlösung vergleichen (2 PDFs)
# -------------------------------
@csrf_exempt
@require_POST
def api_compare_solutions(request):
    file1 = request.FILES.get("file1")
    file2 = request.FILES.get("file2")

    if not file1 or not file2:
        return JsonResponse({"error": "Bitte genau 2 Dateien hochladen"}, status=400)

    files = {
        "file1": (file1.name, file1, "application/pdf"),
        "file2": (file2.name, file2, "application/pdf"),
    }

    try:
        r = requests.post(f"{FASTAPI_BASE}/compare-solutions", files=files, timeout=(10, 120))
    except Exception as e:
        return JsonResponse({"error": f"FastAPI unreachable: {e}"}, status=502)

    if r.status_code >= 400:
        return JsonResponse(
            {"error": f"FastAPI {r.status_code}", "details": r.text}, status=502
        )

    return JsonResponse(r.json())


@csrf_exempt
def api_detailed_analysis(request):
    chat_id = request.GET.get("chat_id")
    run_id = request.GET.get("run_id")

    if not chat_id or not run_id:
        return JsonResponse({"error": "chat_id oder run_id fehlt"}, status=400)

    try:
        r = requests.get(
            f"{FASTAPI_BASE}/detailed-analysis",
            params={"chat_id": chat_id, "run_id": run_id},
            timeout=(10, 120)
        )
    except Exception as e:
        return JsonResponse({"error": f"FastAPI unreachable: {e}"}, status=502)

    if r.status_code >= 400:
        return JsonResponse(
            {"error": f"FastAPI {r.status_code}", "details": r.text},
            status=502
        )

    return JsonResponse(r.json())



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
def api_task_export_docx(request):
    body = json.loads(request.body.decode("utf-8"))
    r = requests.post(f"{FASTAPI_BASE}/task/export_docx", json=body, timeout=60)
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