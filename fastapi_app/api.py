from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import Optional
from pathlib import Path
import base64, os, uuid, re
from pypdf import PdfReader
from datetime import datetime
import json


from analysis import readability
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from mistral import MistralWrapper # from mistral import mistralWrapper




# ----------------- ExamAssistantChat UI --------------------
# Create FastAPI app
app = FastAPI(title="My API Base", version="1.0.0")
wrapper = MistralWrapper()


class OpenApiMessage(BaseModel):
    content: str

class Attachment(BaseModel):
    file_name: str
    content_base64: str
    file_type: str = "pdf"

class MessageRequest(BaseModel):
    chat_id: str                    
    content: str
    attachment: Optional[Attachment] = None


#llm extraction
def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def make_run_id() -> str:
    # z.B. 2025-09-20T16-45-10Z_ab12cd34 (zeitsortierbar + kurz)
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    return f"{ts}_{uuid.uuid4().hex[:8]}"

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def append_jsonl(path: Path, obj: dict) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")    

#uploads extraction
def generate_doc_id(original_name: str) -> str:
    base = os.path.splitext(os.path.basename(original_name))[0][:64] or "upload"
    return f"{base}_{uuid.uuid4().hex[:8]}"    


def ts_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"



def extract_pdf_text(pdf_path: str, max_chars: int = 8000, max_pages: int = 10) -> str:
    """Liest PDF-Text grob, bereinigt Whitespace und kürzt auf max_chars."""
    try:
        reader = PdfReader(pdf_path)
        chunks = []
        for i, page in enumerate(reader.pages):
            if i >= max_pages:
                break
            txt = page.extract_text() or ""
            chunks.append(txt)
        text = "\n".join(chunks)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text[:max_chars]
    except Exception:
        return ""    
    


@app.post("/sendApiMessage")
def sendApiMessage(message: MessageRequest):
    # --- kleine Helfer lokal ---
    def now_iso() -> str:
        return datetime.utcnow().replace(microsecond=0).format('%Y-%m-%dT%H:%M:%SZ') if hasattr(datetime.utcnow(), 'format') \
               else datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def make_run_id() -> str:
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        return f"{ts}_{uuid.uuid4().hex[:8]}"

    def append_jsonl(path: Path, obj: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    saved_path = None
    saved_pdf = None
    saved_extract = None
    pdf_text = ""

    # ========= 1) optional: PDF speichern + extrahieren =========
    if message.attachment is not None:
        attchmnt = message.attachment

        if attchmnt.file_type.lower() != "pdf":
            raise HTTPException(status_code=400, detail="Filetype can only be PDF.")

        try:
            raw_input = base64.b64decode(attchmnt.content_base64, validate=True)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 payload.")

        if not raw_input.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="File is not valid.")

        # Ordner: data/uploads/{chat_id}/{doc_id}/
        doc_id = generate_doc_id(attchmnt.file_name)
        base_dir = Path("data") / "uploads" / message.chat_id / doc_id
        base_dir.mkdir(parents=True, exist_ok=True)

        # source.pdf
        saved_pdf = base_dir / "source.pdf"
        saved_pdf.write_bytes(raw_input)

        # extract.txt
        pdf_text = extract_pdf_text(str(saved_pdf), max_chars=8000, max_pages=10)## Geschützt vor pfad-tricks und begrenzt den dateinamen auf 64 Zeichen und falls dateiname ".pdf" ist.
        saved_extract = base_dir / "extract.txt"
        saved_extract.write_text(pdf_text, encoding="utf-8")

        # upload.json (Metadaten)
        meta = {
            "chat_id": message.chat_id,
            "doc_id": doc_id,
            "file_name": attchmnt.file_name,
            "paths": {
                "pdf": str(saved_pdf),
                "extract": str(saved_extract),
            },
            "preview": {
                "pdf_preview_chars": len(pdf_text),
                "pages_limit": 10,
                "chars_limit": 8000
            },
            "created_at": ts_iso()
        }
        (base_dir / "upload.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        saved_path = str(base_dir)

    #  --- Prompt bauen, damit das LLM die PDF „sieht“ ---
    user_text = (message.content or "").strip()
    if user_text and pdf_text:
        prompt = (
            f"{user_text}\n\n"
            f"Zusätzlicher (gekürzter) Textauszug aus der PDF:\n"
            f"<<<\n{pdf_text}\n>>>"
        )
    elif not user_text and pdf_text:
        prompt = (
            "Analysiere bitte den folgenden (gekürzten) PDF-Auszug:\n"
            f"<<<\n{pdf_text}\n>>>"
        )
    else:
        prompt = user_text or "Keine Eingabe erhalten."

    # --- 3) LLM-Run-Ordner + Prompt persistieren ---
    run_id = make_run_id()
    llm_run_dir = Path("data") / "llm" / message.chat_id / run_id
    llm_run_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = llm_run_dir / "prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")

    # --- 4) LLM aufrufen + Antwort speichern ---
    reply = wrapper.send_request(prompt)

    response_txt = llm_run_dir / "response.txt"
    response_txt.write_text(reply, encoding="utf-8")

    model_name = getattr(wrapper, "model", "mistral-*")
    resp_meta = {
        "chat_id": message.chat_id,
        "run_id": run_id,
        "model": model_name,
        "created_at": now_iso(),
        "inputs": {
            "has_pdf": message.attachment is not None,
            "pdf_preview_chars": len(pdf_text),
        },
        "paths": {
            "prompt": str(prompt_path),
            "response_txt": str(response_txt),
        },
        "usage": {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None
        }
    }
    (llm_run_dir / "response.json").write_text(json.dumps(resp_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # ========= 5) Chat-Verlauf speichern =========
    chat_log_path = Path("data") / "chats" / message.chat_id / "log.jsonl"
    append_jsonl(chat_log_path, {
        "ts": now_iso(),
        "run_id": run_id,
        "user": user_text,
        "pdf_preview_chars": len(pdf_text),
        "reply": reply
    })

    # ========= 6) Antwort an UI =========
    return {
        "reply": reply,
        "saved_dir": saved_path,                              # z.B. data/uploads/{chat_id}/{doc_id}
        "saved_file": str(saved_pdf) if saved_pdf else None,
        "extract_file": str(saved_extract) if saved_extract else None,
        "pdf_preview_chars": len(pdf_text),
        # LLM-Persistenz
        "llm_run_id": run_id,
        "llm_run_dir": str(llm_run_dir),
        "prompt_path": str(prompt_path),
    }



@app.post("/send-attachement")
def sendAttachementToOpenAi(attachment: Attachment):
    if attachment.file_type != "pdf":
        raise HTTPException(
            status_code=400,
            detail="Filetype can only be PDF."
        )
    else:
        return {"ok": True, "filename": attachment.file_name}



if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)


# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to my FastAPI base project!"}

@app.get("/home")
def read_root():
    return {"message": "Welcome to the homepage!"}

# Example GET
@app.get("/ping")
def ping():
    return {"ping": "pong"}



# -------- AufgabenGenerator ---------


class TaskPrompt(BaseModel):
    chat_id: str
    prompt: str
    retry_of: Optional[str] = None   # für "Alternative"

class AcceptBody(BaseModel):
    chat_id: str
    run_id: str
    text: str

class ExportBody(BaseModel):
    chat_id: str
    title: Optional[str] = "Klausur-Entwurf"

def accepted_dir(chat_id: str) -> Path:
    return Path("data") / "exports" / chat_id

def accepted_list_path(chat_id: str) -> Path:
    return accepted_dir(chat_id) / "accepted.json"

def load_accepted(chat_id: str) -> list:
    p = accepted_list_path(chat_id)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_accepted(chat_id: str, items: list) -> None:
    d = accepted_dir(chat_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "accepted.jsonl").open("a", encoding="utf-8").write(
        json.dumps({"ts": now_iso(), "count": len(items)}, ensure_ascii=False) + "\n"
    )
    accepted_list_path(chat_id).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")



@app.post("/task/generate")
def task_generate(body: TaskPrompt):
    # Prompt bauen
    base_prompt = (body.prompt or "").strip() or "Erstelle eine verständliche Prüfungsaufgabe."
    run_id = make_run_id()
    llm_run_dir = Path("data") / "llm" / body.chat_id / run_id
    llm_run_dir.mkdir(parents=True, exist_ok=True)

    # Prompt persistieren
    prompt_path = llm_run_dir / "prompt.txt"
    prompt_path.write_text(base_prompt, encoding="utf-8")

    # LLM call
    text = wrapper.send_request(base_prompt)

    # Antwort speichern
    (llm_run_dir / "response.txt").write_text(text, encoding="utf-8")
    (llm_run_dir / "response.json").write_text(json.dumps({
        "chat_id": body.chat_id,
        "run_id": run_id,
        "model": getattr(wrapper, "model", "mistral-*"),
        "created_at": now_iso(),
        "inputs": {"retry_of": body.retry_of},
        "paths": {"prompt": str(prompt_path)},
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # Lesbarkeit
    rb = readability(text)

    # Chat-Log anreichern
    chat_log_path = Path("data") / "chats" / body.chat_id / "log.jsonl"
    append_jsonl(chat_log_path, {
        "ts": now_iso(), "run_id": run_id, "mode": "generator",
        "prompt": base_prompt, "reply": text, "readability": rb
    })

    return {
        "run_id": run_id,
        "text": text,
        "readability": rb,
        "prompt_path": str(prompt_path),
        "llm_run_dir": str(llm_run_dir),
    }



@app.post("/task/accept")
def task_accept(body: AcceptBody):
    items = load_accepted(body.chat_id)
    items.append({
        "run_id": body.run_id,
        "text": body.text,
        "accepted_at": now_iso()
    })
    save_accepted(body.chat_id, items)
    return {"ok": True, "count": len(items)}



@app.post("/task/export_pdf")
def task_export_pdf(body: ExportBody):
    items = load_accepted(body.chat_id)
    if not items:
        raise HTTPException(status_code=400, detail="Keine angenommenen Aufgaben vorhanden.")

    out_dir = accepted_dir(body.chat_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"

    # sehr einfacher PDF-Export (ReportLab)
    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, body.title or "Klausur-Entwurf")
    y -= 30
    c.setFont("Helvetica", 11)

    idx = 1
    for item in items:
        lines = [f"Aufgabe {idx}:", *item["text"].splitlines(), ""]
        for line in lines:
            if y < 80:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 11)
            c.drawString(40, y, line[:110])  # simple wrap
            y -= 16
        idx += 1

    c.save()
    return {"ok": True, "pdf_path": str(out_path)}
