import json, requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import files
from django.shortcuts import render


FASTAPI_BASE = getattr(settings, "FASTAPI_BASE", "http://127.0.0.1:8000")

def compare(request):
    """Seite für den Vergleich (compare.html)"""
    return render(request, "chatui/compare.html")





def chat_page(request):
    return render(request, "chatui/chat.html")


# -------------------------------
# Chat messages
# -------------------------------
@csrf_exempt
@require_POST
def api_message(request):
    body = json.loads(request.body.decode("utf-8"))
    payload = {
        "chat_id": body.get("chat_id"),
        "content": body.get("content", ""),
        "attachment": body.get("attachment"),
    }
    try:
        r = requests.post(f"{FASTAPI_BASE}/compare-solutions", files=files, timeout=(10, 300))
    except Exception as e:
        return JsonResponse({"error": f"FastAPI unreachable: {e}"}, status=502)

    if r.status_code >= 400:
        return JsonResponse(
            {"error": f"FastAPI {r.status_code}", "details": r.text}, status=502
        )

    data = r.json()
    return JsonResponse(
        {"reply": data.get("reply"), **{k: v for k, v in data.items() if k != "reply"}}
    )


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

