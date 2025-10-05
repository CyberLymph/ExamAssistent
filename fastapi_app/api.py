from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator, ConfigDict
import uvicorn
from typing import List, Optional
from pathlib import Path
import base64, os, uuid, re
from pypdf import PdfReader
from datetime import datetime
import json


from analysis import readability, bloom_level
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from reportlab.lib.utils import simpleSplit
from jsonschema import validate, ValidationError


from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

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

# --- Modelle ---


class ChatIdOnly(BaseModel):
    chat_id: str
    exam_id: str


class TopicItem(BaseModel):
    name: str
    weight: Optional[int] = 0

class ExportBody(BaseModel):
    chat_id: str
    exam_id: str
    title: Optional[str] = "Klausur"
    subject: Optional[str] = None
    topics: Optional[List[TopicItem]] = []


class TaskPrompt(BaseModel):
    chat_id: str
    prompt: str
    schema_type: str = "default"
    retry_of: Optional[str] = None
    
class AcceptBody(BaseModel):
    # Ignoriere unerwartete Felder (z. B. falls ein alter Client noch "json" mitsendet)
    model_config = ConfigDict(extra='ignore')

    chat_id: str
    exam_id: str
    run_id: str
    text: str
    payload: Optional[dict] = None
    schema_type: Optional[str] = "default"

    @model_validator(mode="before")
    @classmethod
    def merge_json_to_payload(cls, data):
        # robust gegen None / falsche Typen
        if isinstance(data, dict):
            # wenn nur "json" kommt -> auf payload mappen
            if 'payload' not in data and 'json' in data:
                data['payload'] = data.pop('json')
            # wenn BEIDE kommen -> payload hat Vorrang; "json" ignorieren
            elif 'payload' in data and 'json' in data:
                data.pop('json', None)
        return data





    
def exam_dir(chat_id: str, exam_id: str) -> Path:
    return Path("data") / "exports" / chat_id / exam_id

def accepted_dir(chat_id: str) -> Path:
    return Path("data") / "exports" / chat_id

def accepted_list_path(chat_id: str, exam_id: str) -> Path:
    return exam_dir(chat_id, exam_id) / "accepted.json"

def load_accepted(chat_id: str, exam_id: str) -> list:
    p = accepted_list_path(chat_id, exam_id)
    if not p.exists(): return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    


from pathlib import Path

def load_prompt(path_env: str, fallback: str) -> str:
    p = os.getenv(path_env)
    if p and Path(p).exists():
        return Path(p).read_text(encoding="utf-8")
    return fallback    

def save_accepted(chat_id: str, exam_id: str, items: list) -> None:
    d = exam_dir(chat_id, exam_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "accepted.jsonl").open("a", encoding="utf-8").write(
        json.dumps({"ts": now_iso(), "count": len(items)}, ensure_ascii=False) + "\n"
    )
    accepted_list_path(chat_id, exam_id).write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def extract_json_block(text: str) -> dict:
    fenced = re.search(r"```json(.*?)```", text, re.S|re.I)
    payload = fenced.group(1).strip() if fenced else text.strip()
    start = payload.find("{")
    end   = payload.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM output.")
    raw = payload[start:end+1]
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object, got {type(obj).__name__}")
    return obj

def render_compact_preview(kind: str, obj: dict) -> str:
    """
    Kompakte Mensch-lesbare Vorschau fürs UI & PDF (aus JSON).
    Unterstützt:
      - default:  { title: str, task: str, ... }
      - mc:       { title, question, options[...] }
      - calc:     { title, problem }
    """
    if not isinstance(obj, dict):
        return str(obj)  # Fallback

    if kind == "mc":
        lines = []
        title = obj.get("title", "Multiple-Choice-Aufgabe")
        q     = obj.get("question", "")
        opts  = obj.get("options", []) or []
        lines.append(f"{title}")
        if q:
            lines.append(q)
        for i, opt in enumerate(opts, 1):
            t = (opt or {}).get("text", "")
            lines.append(f"{i}) {t}")
        return "\n".join([ln for ln in lines if ln]).strip()

    if kind == "calc":
        title = obj.get("title", "Rechenaufgabe")
        prob  = obj.get("problem", "")
        return "\n".join([title, prob]).strip()

    # ---- default (Freitext) ----
    title = obj.get("title", "Aufgabe")
    task_field = obj.get("task")

    # task kann String ODER Objekt sein (abwärtskompatibel)
    if isinstance(task_field, str):
        text = task_field.strip()
    elif isinstance(task_field, dict):
        text = (task_field.get("text") or "").strip()
    else:
        text = ""

    # optionales Fallback – falls du altformat task_text noch irgendwo hast
    if not text:
        text = (obj.get("task_text") or "").strip()

    lines = [title]
    if text:
        lines.append(text)
    return "\n".join(lines).strip()



def group_items_by_topic(items: list, topics_from_body: Optional[List[TopicItem]]):
    def item_topic(it):
        j = (it.get("json") or {}) if isinstance(it.get("json"), dict) else {}
        t = (j.get("topic") or "").strip()
        return t if t else "Allgemein"

    grouped = {}
    for it in items:
        t = item_topic(it)
        grouped.setdefault(t, []).append(it)

    order_from_body = [t.name for t in (topics_from_body or [])]
    remaining = [t for t in grouped.keys() if t not in order_from_body]
    topic_order = order_from_body + sorted(remaining)
    return grouped, topic_order

#------ENDPOINTS-------
@app.post("/task/reset_exam")
def task_reset_exam(body: ChatIdOnly):
    d = exam_dir(body.chat_id, body.exam_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "accepted.json").write_text("[]", encoding="utf-8")
    (d / "accepted.jsonl").open("a", encoding="utf-8").write(
        json.dumps({"ts": now_iso(), "event": "reset"}, ensure_ascii=False) + "\n"
    )
    return {"ok": True}


@app.post("/task/generate")
def task_generate(body: TaskPrompt):
    # 1) Schema-Typ bestimmen
    schema_key = (body.schema_type or "default").lower()
    if schema_key not in {"default", "mc", "calc"}:
        schema_key = "default"

    # 2) System-Prompt + Schema-Datei wählen
    if schema_key == "mc":
        system_prompt = load_prompt(
            "SYSTEM_PROMPT_MC_PATH",
            "Du bist ein Aufgaben-Generator für Multiple-Choice-Aufgaben. "
            "Formuliere kurz, klar, prüfungsgeeignet."
        )
        schema_path = Path("schemas/multiple_choice_task.schema.json")
        kind = "mc"
    elif schema_key == "calc":
        system_prompt = load_prompt(
            "SYSTEM_PROMPT_CALC_PATH",
            "Du bist ein Aufgaben-Generator für Rechenaufgaben. "
            "Liefer präzise Aufgabenstellung und Lösungsidee (optional), kompakt."
        )
        schema_path = Path("schemas/calculation_task.schema.json")
        kind = "calc"
    else:
        system_prompt = load_prompt(
            "SYSTEM_PROMPT_DEFAULT_PATH",
            "Du bist ein Aufgaben-Generator für offene Prüfungsaufgaben. "
            "Kompakt, ohne Floskeln, nur die Aufgabe."
        )
        schema_path = Path("schemas/default_task.schema.json")
        kind = "default"

    # 3) Schema laden
    if not schema_path.exists():
        raise HTTPException(status_code=500, detail=f"Schema file not found: {schema_path}")
    schema_json = json.loads(schema_path.read_text(encoding="utf-8"))

    # 4) finalen Prompt bauen
    user_prompt = (body.prompt or "").strip() or "Erstelle eine verständliche Prüfungsaufgabe."
    instructions = (
        "Liefere NUR ein einziges JSON-Objekt, das exakt dem folgenden JSON-Schema entspricht. "
        "Kein Fließtext, keine Erklärungen, KEINE Markdown-Codeblöcke außerhalb des JSONs."
    )
    full_prompt = (
        f"{system_prompt}\n\n"
        f"{instructions}\n\n"
        f"JSON-Schema:\n{json.dumps(schema_json, ensure_ascii=False, indent=2)}\n\n"
        f"Benutzerwunsch:\n{user_prompt}"
    )

    # 5) LLM-Run-Ordner
    run_id = make_run_id()
    llm_run_dir = Path("data") / "llm" / body.chat_id / run_id
    llm_run_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = llm_run_dir / "prompt.txt"
    prompt_path.write_text(full_prompt, encoding="utf-8")

    # 6) LLM call
    raw_text = wrapper.send_request(full_prompt)

    # 7) JSON extrahieren & validieren
    try:
        obj = extract_json_block(raw_text)
        validate(instance=obj, schema=schema_json)
    except (ValueError, ValidationError, json.JSONDecodeError) as e:
        (llm_run_dir / "response_raw.txt").write_text(raw_text, encoding="utf-8")
        raise HTTPException(status_code=400, detail=f"Invalid LLM output: {e}")

    # 8) Kompakte Vorschau + Lesbarkeit
    preview_text = render_compact_preview(kind, obj)
    (llm_run_dir / "response.json").write_text(
        json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (llm_run_dir / "rendered.txt").write_text(preview_text, encoding="utf-8")

    rb = readability(preview_text)
    bloom = bloom_level(preview_text)

    # 9) Log
    chat_log_path = Path("data") / "chats" / body.chat_id / "log.jsonl"
    append_jsonl(chat_log_path, {
        "ts": now_iso(),
        "run_id": run_id,
        "mode": "generator",
        "schema": schema_key,
        "prompt": user_prompt,
        "reply_json": obj,
        "preview": preview_text[:500],
        "readability": rb
    })

    # 10) Antwort an UI
    return {
        "run_id": run_id,
        "schema": schema_key,
        "json": obj,
        "text": preview_text,
        "readability": rb,
        "bloom": bloom,  # NEU
        "prompt_path": str(prompt_path),
        "llm_run_dir": str(llm_run_dir),
        "rendered_path": str(llm_run_dir / "rendered.txt"),
        "response_path": str(llm_run_dir / "response.json"),
    }





@app.post("/task/accept")
def task_accept(body: AcceptBody):
    if not body.exam_id:
        raise HTTPException(status_code=400, detail="exam_id fehlt.")
    items = load_accepted(body.chat_id, body.exam_id)

    payload = body.payload or {}
    if isinstance(payload, dict):
        # Fallback-Topic, wenn keins gesetzt wurde (UI setzt es normalerweise)
        topic = (payload.get("topic") or "").strip()
        if not topic:
            payload["topic"] = "Allgemein"

    items.append({
        "run_id": body.run_id,
        "text": body.text,
        "json": payload,
        "schema_type": (body.schema_type or "default"),
        "accepted_at": now_iso()
    })
    save_accepted(body.chat_id, body.exam_id, items)
    return {"ok": True, "count": len(items)}


@app.post("/task/accepted_list")
def task_accepted_list(body: ChatIdOnly):
    items = load_accepted(body.chat_id, body.exam_id)
    return {"ok": True, "items": items}



@app.post("/task/export_pdf")
def task_export_pdf(body: ExportBody):
    items = load_accepted(body.chat_id, body.exam_id)
    if not items:
        raise HTTPException(status_code=400, detail="Keine angenommenen Aufgaben vorhanden.")

    out_dir = exam_dir(body.chat_id, body.exam_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4

    def draw_wrapped(text, x, y, max_width, leading=16, font="Helvetica", size=11):
        c.setFont(font, size)
        lines = simpleSplit(text, font, size, max_width)
        for line in lines:
            if y < 60:
                c.showPage()
                y = height - 50
                c.setFont(font, size)
            c.drawString(x, y, line)
            y -= leading
        return y

    # -------- Deckblatt --------
    y = height - 80
    c.setFont("Helvetica-Bold", 22)
    title = body.subject or body.title or "Klausur"
    c.drawString(40, y, f"Klausur: {title}")
    y -= 32

    c.setFont("Helvetica", 12)
    y = draw_wrapped("Name: _________________________________", 40, y, width-80, leading=20)
    y = draw_wrapped("Vorname: ______________________________", 40, y, width-80, leading=20)
    y = draw_wrapped("Matrikelnummer: _______________________", 40, y, width-80, leading=20)
    y -= 10

    c.drawString(40, y, f"Erstellt am: {datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC')}")
    y -= 30

    if body.topics:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "Themen & Gewichtungen")
        y -= 20
        c.setFont("Helvetica", 11)
        for t in body.topics:
            line = f"– {t.name}" + (f" ({t.weight} Punkte)" if (t.weight or 0) > 0 else "")
            y = draw_wrapped(line, 40, y, width-80, leading=16)

    c.showPage()  # Aufgaben beginnen auf neuer Seite

    # -------- Items nach Thema gruppieren --------
    # 1) Topic aus Item ziehen (json.topic) – Fallback "Allgemein"
    def item_topic(it):
        j = (it.get("json") or {}) if isinstance(it.get("json"), dict) else {}
        t = (j.get("topic") or "").strip()
        return t if t else "Allgemein"

    grouped = {}
    for it in items:
        t = item_topic(it)
        grouped.setdefault(t, []).append(it)

    # 2) Reihenfolge der Themen:
    #    zuerst wie vom Wizard übergeben (body.topics), danach evtl. übrige
    order_from_body = [t.name for t in (body.topics or [])]
    remaining = [t for t in grouped.keys() if t not in order_from_body]
    topic_order = order_from_body + sorted(remaining)

    # -------- Druck-Layout --------
    margin_x = 40
    max_w = width - 80

    for topic_name in topic_order:
        topic_items = grouped.get(topic_name, [])
        if not topic_items:
            continue

        # Jede Themen-Gruppe auf einer neuen Seite beginnen
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin_x, height - 60, f"Thema: {topic_name}")
        # Gewicht, falls in body.topics enthalten
        tcfg = next((t for t in (body.topics or []) if t.name == topic_name), None)
        if tcfg and (tcfg.weight or 0) > 0:
            c.setFont("Helvetica", 11)
            c.drawString(margin_x, height - 80, f"Gewichtung: {tcfg.weight} Punkte")

        y = height - 110
        task_no = 1  # Nummerierung je Thema neu anfangen

        for it in topic_items:
            # Überschrift der Aufgabe
            c.setFont("Helvetica-Bold", 14)
            c.drawString(margin_x, y, f"Aufgabe {task_no}")
            y -= 22

            # Aufgabe-Text (kompakte Vorschau aus Generator)
            c.setFont("Helvetica", 11)
            text = it.get("text") or ""
            y = draw_wrapped(text, margin_x, y, max_w, leading=16)

            # Antwort-Linien NUR für Freitext & Rechenaufgaben
            schema = (it.get("schema_type") or "default").lower()
            if schema in ("default", "calc"):   # KEINE Linien für "mc"
                y -= 8
                for _ in range(6):
                    if y < 70:
                        c.showPage()
                        # Themenkopf NICHT erneut zeichnen, nur weiterlaufen
                        y = height - 50
                        c.setFont("Helvetica", 11)
                    c.line(margin_x, y, width - 40, y)
                    y -= 16
                y -= 10
            else:
                # MC: etwas Abstand, aber keine Linien
                y -= 16

            # Falls Seite voll, neue Seite
            if y < 100:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 11)

            task_no += 1

        # Nach Thema: immer Seitenumbruch (nächste Themen-Seite sauber starten)
        c.showPage()

    # Wenn am Ende eine leere Seite entstanden ist (z. B. kein weiteres Thema),
    # ist das okay; ReportLab lässt sie einfach stehen. Optional könnte man
    # noch "c._pagesize" o. Ä. prüfen, aber nicht nötig.
    c.save()
    return {"ok": True, "pdf_path": str(out_path)}



@app.post("/task/export_docx")
def task_export_docx(body: ExportBody):
    items = load_accepted(body.chat_id, body.exam_id)
    if not items:
        raise HTTPException(status_code=400, detail="Keine angenommenen Aufgaben vorhanden.")

    out_dir = exam_dir(body.chat_id, body.exam_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.docx"

    doc = Document()

    # ---------- Deckblatt ----------
    title = body.subject or body.title or "Klausur"
    h = doc.add_heading(f"Klausur: {title}", level=1)
    for p in [ "Name: _________________________________",
               "Vorname: ______________________________",
               "Matrikelnummer: _______________________" ]:
        para = doc.add_paragraph(p)
        para.runs[0].font.size = Pt(12)

    doc.add_paragraph(f"Erstellt am: {datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC')}")

    if body.topics:
        doc.add_heading("Themen & Gewichtungen", level=2)
        for t in body.topics:
            line = f"– {t.name}" + (f" ({t.weight} Punkte)" if (t.weight or 0) > 0 else "")
            doc.add_paragraph(line)

    # Seitenumbruch vor den Aufgaben
    doc.add_page_break()

    # ---------- Gruppierung nach Thema ----------
    grouped, topic_order = group_items_by_topic(items, body.topics)

    def add_answer_lines(n=6):
        for _ in range(n):
            # „Zeile“: einfach ein Unterstrich-Run, gut editierbar
            run = doc.add_paragraph().add_run("_" * 100)
            run.font.size = Pt(11)

    # ---------- Themen ausgeben ----------
    for topic_name in topic_order:
        topic_items = grouped.get(topic_name, [])
        if not topic_items:
            continue

        doc.add_heading(f"Thema: {topic_name}", level=2)
        tcfg = next((t for t in (body.topics or []) if t.name == topic_name), None)
        if tcfg and (tcfg.weight or 0) > 0:
            doc.add_paragraph(f"Gewichtung: {tcfg.weight} Punkte")

        task_no = 1
        for it in topic_items:
            # Überschrift
            doc.add_heading(f"Aufgabe {task_no}", level=3)
            # Aufgabe-Text
            p = doc.add_paragraph(it.get("text") or "")
            p.runs[0].font.size = Pt(11)

            # Platz für Antworten NUR für default & calc
            schema = (it.get("schema_type") or "default").lower()
            if schema in ("default", "calc"):
                add_answer_lines(6)
            else:
                # MC: nur etwas Abstand
                doc.add_paragraph("")

            task_no += 1

        # Jede Themen-Gruppe auf neuer Seite
        doc.add_page_break()

    # speichern
    doc.save(str(out_path))
    return {"ok": True, "docx_path": str(out_path)}