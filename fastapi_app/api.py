from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import Optional
from pathlib import Path
import base64, os, uuid, re
from pypdf import PdfReader
from datetime import datetime
import json


from mistral import MistralWrapper # from mistral import mistralWrapper



# Create FastAPI app
app = FastAPI(title="My API Base", version="1.0.0")
wrapper = MistralWrapper()

# Example request body
class Item(BaseModel):
    name: str
    description: str
    price: float
    tax: float

class OpenApiMessage(BaseModel):
    content: str

class Attachment(BaseModel):
    file_name: str
    content_base64: str
    file_type: str = "pdf"

class MessageRequest(BaseModel):
    content: str
    attachment: Optional[Attachment] = None



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

    saved_path = None
    pdf_text = ""
    if message.attachment is not None:
        attchmnt = message.attachment

        if attchmnt.file_type.lower() != "pdf":# Nur pdf zulassen
            raise HTTPException(
            status_code=400,
            detail="Filetype can only be PDF."
        )

        try: # base64 decoding
            raw_input = base64.b64decode(attchmnt.content_base64, validate=True)
        except Exception:
             raise HTTPException( status_code=400, detail="Invalid base64 payload.")
        
        if not raw_input.startswith(b"%PDF"): #validation
            raise HTTPException( status_code=400, detail="File is not valid.")
        
        #Dateinamen 
        safe_name = os.path.splitext(os.path.basename(attchmnt.file_name))[0][:64] or "upload"# Geschützt vor pfad-tricks und begrenzt den dateinamen auf 64 Zeichen und falls dateiname ".pdf" ist.
        unique = uuid.uuid4().hex[:8]# zufällige Hex Werte zur Verhinderung der Kollision, wenn gleiche Dateinamen gespeichert werden müssen.
        final_name = f"{safe_name}_{unique}.pdf" # "klausur.pdf" → "klausur_a1b2c3d4.pdf"

        uploads = Path("uploads")
        uploads.mkdir(exist_ok=True)
        (uploads / final_name).write_bytes(raw_input)
        saved_path = str(uploads / final_name)

        # lokale Extraktion (erste Seiten, gekürzt)
        pdf_text = extract_pdf_text(saved_path, max_chars=8000, max_pages=10)

    # --- Prompt bauen, damit das LLM die PDF „sieht“ ---
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

    # --- LLM-Aufruf ---
    reply = wrapper.send_request(prompt)

    return {
        "reply": reply,
        "saved_attachment": saved_path,
        "pdf_preview_chars": len(pdf_text) if pdf_text else 0
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



# Example POST
@app.post("/items/")
def create_item(item: Item):
    total_price = item.price + (item.tax if item.tax else 0)
    return {"name": item.name, "total_price": total_price}

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