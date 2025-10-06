from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
from analysis.answer_comparator import AnswerComparator
from mistral import MistralWrapper
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader
import uvicorn, os, uuid, re, json, tempfile, shutil, traceback
from analysis.readability_module import analyze_german_readability, ReadabilityAnalyzer
from analysis.answer_comparator import AnswerComparator
from analysis.test_modules import TestModuleRunner


# ============================================================
# Setup
# ============================================================
app = FastAPI(title="ExamAssistant API", version="3.0.0")
wrapper = MistralWrapper()
comparator = AnswerComparator()

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

def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def pdf_to_text(path: str, max_chars=10000) -> str:
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
    """Speichert den generierten Lösungstext als PDF mit automatischem Zeilenumbruch."""
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
    """
    Extrahiert Aufgaben aus einer PDF und generiert strukturierte Antworten im Format:
    Aufgabe 1:
    Antwort
    Aufgabe 2:
    Antwort
    usw.
    """
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

        # === Prompt: strukturierte Antwortgenerierung ===
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

        # === LLM-Aufruf ===
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
            "saved_dir": str(base_dir),
            "saved_file": str(pdf_path),
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Fehler in generate_solution: {e}")

# ============================================================
# API: Upload löschen
# ============================================================
@app.delete("/delete-upload")
async def delete_upload(chat_id: str = Query("default"), doc_id: str = Query(...)):
    try:
        base_dir = Path("data") / "uploads" / chat_id / doc_id
        if not base_dir.exists():
            return JSONResponse({"ok": False, "message": "Upload nicht gefunden"}, status_code=404)
        shutil.rmtree(base_dir, ignore_errors=True)
        return {"ok": True, "message": f"Upload {doc_id} gelöscht"}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/compare-solutions")
async def compare_solutions(
    file1: UploadFile = File(...),  # Musterlösung (ML)
    file2: UploadFile = File(...),  # Studentenlösung (SL)
    mode: str = Form("quick"),      # "quick" oder "detailed"
    chat_id: str = Form("default"),
):
    import tempfile
    from analysis.test_modules import TestModuleRunner

    try:
        # 🧾 Temporär speichern
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t1:
            t1.write(await file1.read())
            path_ml = t1.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t2:
            t2.write(await file2.read())
            path_sl = t2.name

        # 🧠 Text aus PDFs
        model_text = pdf_to_text(path_ml)
        student_text = pdf_to_text(path_sl)
        if not model_text or not student_text:
            raise HTTPException(status_code=400, detail="Leere oder unlesbare PDFs.")

        # 🆔 IDs
        run_id = make_run_id()
        runner = TestModuleRunner(base_dir="analysis")

        if mode == "quick":
            # Nur Kurzvergleich
            comp = AnswerComparator()
            quick_score = comp.quick_compare(student_text, model_text)
            readability = analyze_german_readability(student_text)
            return {
                "mode": "quick",
                "quick_similarity": quick_score,
                "readability": readability,
                "summary": f"Quick-Vergleich: {round(quick_score*100,2)}% Ähnlichkeit erkannt.",
            }

        # Vollanalyse
        summary = runner.run_analysis(student_text, model_text, chat_id, run_id)
        return {
            "mode": "detailed",
            "run_id": run_id,
            "chat_id": chat_id,
            "summary_path": f"/analysis/{chat_id}/{run_id}/summary.json",
            "summary": summary,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Fehler in compare_solutions: {e}")

# ============================================================
# Root
# ============================================================
@app.get("/")
def index():
    return {"status": "ExamAssistant API aktiv", "version": "3.0.0"}

# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
