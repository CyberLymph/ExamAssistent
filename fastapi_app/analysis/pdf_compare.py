from fastapi import FastAPI, UploadFile, File
from answer_comparator import AnswerComparator
import fitz  # PyMuPDF zum PDF-Text-Extrahieren

app = FastAPI()
comparator = AnswerComparator()

def extract_text_from_pdf(file: UploadFile) -> str:
    doc = fitz.open(stream=file.file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text("text")
    return text.strip()

@app.post("/compare-pdfs")
async def compare_pdfs(file1: UploadFile = File(...), file2: UploadFile = File(...)):
    text1 = extract_text_from_pdf(file1)
    file1.file.seek(0)
    text2 = extract_text_from_pdf(file2)

    result = comparator.analyze_and_save(text1, text2, chat_id="ui", run_id="pdf_compare")
    return result
