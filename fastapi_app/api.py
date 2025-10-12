# ============================================================
# fastapi_app/api.py – stabile, bereinigte Version (v3.3.0)
# ============================================================
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from pathlib import Path
from datetime import datetime
from analysis.answer_comparator import AnswerComparator
from mistral import MistralWrapper
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader
import uvicorn, os, uuid, re, json, tempfile, traceback
from analysis.readability_module import analyze_german_readability, ReadabilityAnalyzer
from fastapi.middleware.cors import CORSMiddleware

# ============================================================
# Initialisierung
# ============================================================
app = FastAPI(title="ExamAssistant API", version="3.3.0")

wrapper = MistralWrapper()
comparator = AnswerComparator()
readability = ReadabilityAnalyzer()

# ============================================================
# CORS (Frontend-Port 8001)
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8001", "http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Hilfsfunktionen
# ============================================================
def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def generate_doc_id(name: str) -> str:
    base = os.path.splitext(os.path.basename(name))[0][:50] or "upload"
    return f"{base}_{uuid.uuid4().hex[:8]}"


def make_run_id() -> str:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}_{uuid.uuid4().hex[:8]}"


def pdf_to_text(path: str, max_chars=10000) -> str:
    """Extrahiert Text aus einer PDF-Datei."""
    text = ""
    try:
        reader = PdfReader(path)
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
    except Exception:
        pass
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars] if text else ""


def export_solution_as_pdf(text: str, export_path: Path):
    """Speichert generierten Lösungstext als PDF."""
    export_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(export_path), pagesize=A4)
    width, height = A4
    x, y = 50, height - 50
    max_width = width - 100
    for line in text.split("\n"):
        words = line.split(" ")
        current_line = ""
        for w in words:
            test_line = current_line + w + " "
            if c.stringWidth(test_line, "Helvetica", 10) < max_width:
                current_line = test_line
            else:
                c.drawString(x, y, current_line)
                y -= 14
                current_line = w + " "
                if y < 60:
                    c.showPage()
                    y = height - 50
        if current_line:
            c.drawString(x, y, current_line)
            y -= 14
            if y < 60:
                c.showPage()
                y = height - 50
    c.save()


# ============================================================
# API: Lösung generieren
# ============================================================
@app.post("/generate-solution")
async def generate_solution(chat_id: str = Form("default"), pdf: Optional[UploadFile] = File(None)):
    try:
        if not pdf:
            raise HTTPException(status_code=400, detail="Keine PDF-Datei hochgeladen.")
        raw = await pdf.read()
        if not raw.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="Ungültige PDF-Datei.")

        # === Basisverzeichnis vorbereiten ===
        doc_id = generate_doc_id(pdf.filename)
        base_dir = Path("data") / "uploads" / chat_id / doc_id
        ensure_dir(base_dir)
        pdf_path = base_dir / "source.pdf"
        pdf_path.write_bytes(raw)

        # === Text aus PDF extrahieren ===
        text = pdf_to_text(str(pdf_path))
        if not text:
            raise HTTPException(status_code=400, detail="PDF enthält keinen lesbaren Text.")
        # 🔧 Fix 1 – zusätzliche Bereinigung für konsistente Regex-Erkennung
        text = re.sub(r"\s+", " ", text).strip()

        # === Aufgabenblöcke erkennen ===
        aufgaben_raw = re.findall(
            r"(Aufgabe\s*\d+[a-zA-Z]?[.:–-]?\s.*?)(?=(?:Aufgabe\s*\d+[a-zA-Z]?[.:–-]?|Frage\s*\d+[.:–-]?|$))",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        aufgaben = []
        for a in aufgaben_raw:
            clean = re.sub(r"^(?:Aufgabe|Frage)\s*\d+[a-zA-Z]?[.:–-]?\s*", "", a.strip(), flags=re.IGNORECASE)
            aufgaben.append(clean.strip())

        if not aufgaben:
            aufgaben = [text]

        # === Prompt dynamisch aufbauen ===
        prompt_parts = []
        for i, frage in enumerate(aufgaben, start=1):
            prompt_parts.append(f"Aufgabe {i}:\n{frage}\n\nAntwort {i}:")
        structured_prompt = "\n\n".join(prompt_parts)

        prompt = (
            "Beantworte präzise und sachlich nur die folgenden Aufgaben.\n"
            "Formatiere das Ergebnis **genau** in diesem Stil:\n\n"
            "Aufgabe 1:\n[Fragetext]\n\nAntwort 1:\n[Lösung]\n\n"
            "Aufgabe 2:\n[Fragetext]\n\nAntwort 2:\n[Lösung]\n\n"
            "usw.\n\n"
            "Gib **nur** die Fragen und Antworten zurück — keine Einleitung, keine Kommentare.\n\n"
            f"Hier sind die Aufgaben:\n<<<\n{structured_prompt}\n>>>"
        )

        run_id = make_run_id()
        llm_dir = Path("data") / "llm" / chat_id / run_id
        ensure_dir(llm_dir)
        (llm_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

        try:
            reply = wrapper.send_request(prompt)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM Fehler: {str(e)}")

        if "Service tier capacity exceeded" in str(reply):
            reply = "⚠️ Der LLM-Dienst ist derzeit ausgelastet. Bitte versuche es später erneut."

        # === Speichern & PDF-Export ===
        (llm_dir / "response.txt").write_text(reply, encoding="utf-8")
        export_dir = Path("exports") / "solutions" / chat_id
        export_path = export_dir / f"{run_id}.pdf"
        export_solution_as_pdf(reply, export_path)

        return {
            "chat_id": chat_id,
            "doc_id": doc_id,
            "run_id": run_id,
            "solution": reply,
            "export_pdf": str(export_path),
            "aufgaben_gefunden": len(aufgaben),
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Fehler in generate_solution: {e}")


# ============================================================
# API: Vergleichsanalyse
# ============================================================
@app.post("/compare-solutions")
async def compare_solutions(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    mode: str = Form("quick"),
    chat_id: str = Form("default"),
):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t1:
            t1.write(await file1.read())
            path_ml = t1.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t2:
            t2.write(await file2.read())
            path_sl = t2.name

        model_text = pdf_to_text(path_ml)
        student_text = pdf_to_text(path_sl)
        if not model_text or not student_text:
            raise HTTPException(status_code=400, detail="Leere oder unlesbare PDFs.")

        run_id = make_run_id()
        comp = AnswerComparator()

        # === QUICK ===
        if mode == "quick":
            quick_score = comp.quick_compare(student_text, model_text)
            readability_score = analyze_german_readability(student_text)
            return {
                "mode": "quick",
                "quick_similarity": quick_score,
                "readability": readability_score,
                "summary": f"Quick-Vergleich: {round(quick_score*100,2)}% Ähnlichkeit erkannt."
            }

        # === DETAILED ===
        elif mode == "detailed":
            summary = comp.detailed_compare(student_text, model_text)
            if not summary or not isinstance(summary, dict):
                raise ValueError("Keine gültige summary-Daten erhalten.")

            # 🔧 Fix 2 – Lesbarkeitsanalyse der Musterlösung ergänzen
            if "readability_metrics_model" not in summary:
                summary["readability_metrics_model"] = analyze_german_readability(model_text)

            # Struktur-Fallbacks
            if "tasks" not in summary or not summary["tasks"]:
                summary["tasks"] = [{
                    "task_id": "Gesamtanalyse",
                    "similarity": summary.get("similarity_score", 0.0),
                    "model_solution": model_text or "(Keine Musterlösung gefunden)",
                    "student_answer": student_text or "(Keine Studentenlösung gefunden)",
                    "feedback": summary.get("feedback", "(Kein Feedback verfügbar)")
                }]
            else:
                for t in summary["tasks"]:
                    t["task_id"] = t.get("task_id", "Unbekannte Aufgabe")
                    t["model_solution"] = t.get("model_solution") or "(Keine Musterlösung gefunden)"
                    t["student_answer"] = t.get("student_answer") or "(Keine Studentenlösung gefunden)"
                    t["feedback"] = t.get("feedback") or "(Kein Feedback verfügbar)"

            outdir = Path("analysis") / chat_id / run_id
            outdir.mkdir(parents=True, exist_ok=True)
            with open(outdir / "summary.json", "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            return {
                "mode": "detailed",
                "chat_id": chat_id,
                "run_id": run_id,
                "summary": summary,
            }

        raise HTTPException(status_code=400, detail=f"Ungültiger Modus: {mode}")

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Fehler in compare_solutions: {e}")


# ============================================================
# API: Detaillierte Analyse abrufen
# ============================================================
@app.get("/detailed-analysis")
async def detailed_analysis(chat_id: str = Query(...), run_id: str = Query(...)):
    try:
        summary_path = Path("analysis") / chat_id / run_id / "summary.json"
        if not summary_path.exists():
            raise HTTPException(status_code=404, detail="Analyse-Datei nicht gefunden.")

        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)

        # Struktur garantieren (Fallback)
        if "tasks" not in summary or not summary["tasks"]:
            summary["tasks"] = [{
                "task_id": "Gesamtanalyse",
                "similarity": summary.get("similarity_score", 0.0),
                "model_solution": summary.get("model_solution", "(Keine Musterlösung gefunden)"),
                "student_answer": summary.get("student_answer", "(Keine Studentenlösung gefunden)"),
                "feedback": summary.get("feedback", "(Kein Feedback verfügbar)")
            }]
        else:
            for t in summary["tasks"]:
                t["task_id"] = t.get("task_id", "Unbekannte Aufgabe")
                t["model_solution"] = t.get("model_solution") or "(Keine Musterlösung gefunden)"
                t["student_answer"] = t.get("student_answer") or "(Keine Studentenlösung gefunden)"
                t["feedback"] = t.get("feedback") or "(Kein Feedback verfügbar)"

        return {"chat_id": chat_id, "run_id": run_id, "summary": summary}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Fehler beim Laden der Analyse: {e}")


# ============================================================
# Root
# ============================================================
@app.get("/")
def index():
    return {"status": "ExamAssistant API aktiv", "version": "3.3.0"}


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
