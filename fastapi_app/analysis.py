# fastapi_app/analysis.py
try:
    import textstat
except ImportError:
    textstat = None

def readability(text: str) -> dict:
    if not text:
        return {"flesch": None, "label": "keine Daten"}
    if not textstat:
        # Fallback, falls textstat nicht installiert
        return {"flesch": None, "label": "unbekannt (textstat fehlt)"}
    score = textstat.flesch_reading_ease(text)
    if score >= 60:
        label = "Lesbarkeit ist gut"
    elif score >= 30:
        label = "Lesbarkeit ist mittel"
    else:
        label = "Lesbarkeit ist schwer"
    return {"flesch": round(score, 1), "label": label}
