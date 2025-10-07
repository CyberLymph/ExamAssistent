# ============================================================
# fastapi_app/api.py  – korrigierte & erweiterte Version
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
import uvicorn, os, uuid, re, json, tempfile, shutil, traceback
from analysis.readability_module import analyze_german_readability, ReadabilityAnalyzer
from analysis.test_modules import TestModuleRunner
from fastapi.middleware.cors import CORSMiddleware

# ============================================================
# Initialisierung
# ============================================================
app = FastAPI(title="ExamAssistant API", version="3.2.2")

wrapper = MistralWrapper()
comparator = AnswerComparator()
readability = ReadabilityAnalyzer()

# ============================================================
# CORS aktivieren (Frontend auf Port 8001 darf API ansprechen)
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8001",
        "http://localhost:8001",
    ],
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
    except Exception as e:
        print(f"⚠️ Fehler beim Lesen von {path}: {e}")
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
        doc_id = generate_doc_id(pdf.filename)
        base_dir = Path("data") / "uploads" / chat_id / doc_id
        ensure_dir(base_dir)
        pdf_path = base_dir / "source.pdf"
        pdf_path.write_bytes(raw)

        text = pdf_to_text(str(pdf_path))
        if not text:
            raise HTTPException(status_code=400, detail="PDF enthält keinen lesbaren Text.")

        prompt = (
            "Analysiere das folgende PDF-Dokument und beantworte ausschließlich die erkannten Aufgaben.\n"
            "Formatiere das Ergebnis exakt so:\n\n"
            "Aufgabe 1:\n[Antwort]\n\nAufgabe 2:\n[Antwort]\n\nusw.\n\n"
            "Keine Einleitung, keine Kommentare.\n\n"
            f"Inhalt:\n<<<\n{text}\n>>>"
        )

        run_id = make_run_id()
        llm_dir = Path("data") / "llm" / chat_id / run_id
        ensure_dir(llm_dir)
        (llm_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        reply = wrapper.send_request(prompt)
        (llm_dir / "response.txt").write_text(reply, encoding="utf-8")

        export_dir = Path("exports") / "solutions" / chat_id
        export_path = export_dir / f"{run_id}.pdf"
        export_solution_as_pdf(reply, export_path)

        return {
            "chat_id": chat_id,
            "doc_id": doc_id,
            "solution": reply,
            "export_pdf": str(export_path),
            "run_id": run_id,
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

        print("📘 MODE:", mode)
        print("📄 Musterlösung Länge:", len(model_text))
        print("📄 Studentenlösung Länge:", len(student_text))
        if not model_text or not student_text:
            raise HTTPException(status_code=400, detail="Leere oder unlesbare PDFs.")

        run_id = make_run_id()

        # === QUICK ===
        if mode == "quick":
            print("⚡ QUICK Vergleich läuft...")
            comp = AnswerComparator()
            quick_score = comp.quick_compare(student_text, model_text)
            readability = analyze_german_readability(student_text)
            print("✅ QUICK erfolgreich:", quick_score)
            return {
                "mode": "quick",
                "quick_similarity": quick_score,
                "readability": readability,
                "summary": f"Quick-Vergleich: {round(quick_score*100,2)}% Ähnlichkeit erkannt."
            }

        # === DETAILED ===
        elif mode == "detailed":
            print("🧠 DETAILED Vergleich gestartet...")
            comp = AnswerComparator()
            summary = comp.detailed_compare(student_text, model_text)
            if not summary or not isinstance(summary, dict):
                raise ValueError("Keine gültige summary-Daten erhalten.")

            # --- Sicherstellen, dass Tasks immer Liste ist ---
            if "tasks" not in summary or not summary["tasks"]:
                summary["tasks"] = [{
                    "task_id": "Gesamtanalyse",
                    "similarity": summary.get("similarity_score"),
                    "model_solution": model_text,
                    "student_answer": student_text,
                    "feedback": summary.get("feedback", "(Kein Feedback verfügbar)")
                }]

            outdir = Path("analysis") / chat_id / run_id
            outdir.mkdir(parents=True, exist_ok=True)
            summary_path = outdir / "summary.json"
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            print(f"💾 Summary gespeichert unter: {summary_path.absolute()}")

            return {
                "mode": "detailed",
                "chat_id": chat_id,
                "run_id": run_id,
                "summary": summary,
            }

        else:
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
            raise HTTPException(status_code=404, detail=f"Analyse-Datei nicht gefunden unter {summary_path}")
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)

        # --- Fallback: falls tasks fehlt, trotzdem anzeigen ---
        if "tasks" not in summary or not summary["tasks"]:
            summary["tasks"] = [{
                "task_id": "Gesamtanalyse",
                "similarity": summary.get("similarity_score"),
                "model_solution": summary.get("model_solution", ""),
                "student_answer": summary.get("student_answer", ""),
                "feedback": summary.get("feedback", "(Kein Feedback verfügbar)")
            }]

        print(f"📂 detailed-analysis geladen: {summary_path.absolute()}")
        return {"chat_id": chat_id, "run_id": run_id, "summary": summary}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Fehler beim Laden der Analyse: {e}")

# ============================================================
# Root
# ============================================================
@app.get("/")
def index():
    return {"status": "ExamAssistant API aktiv", "version": "3.2.2"}

# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
