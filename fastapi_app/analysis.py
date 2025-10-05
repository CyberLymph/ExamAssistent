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


def bloom_level(text: str) -> dict:
    """
    Sehr einfache Heuristik oder LLM-basierte Analyse des kognitiven Niveaus
    nach Bloom (1–6).
    Gibt z. B. zurück: {"level": 3, "label": "Anwenden"}
    """
    levels = [
        (1, "Erinnern", ["definiere", "nennen", "aufzählen"]),
        (2, "Verstehen", ["erkläre", "beschreibe", "interpretiere"]),
        (3, "Anwenden", ["berechne", "nutze", "anwenden"]),
        (4, "Analysieren", ["analysiere", "vergleiche", "untersuche"]),
        (5, "Bewerten", ["bewerte", "diskutiere", "kritisiere"]),
        (6, "Kreieren", ["entwickle", "entwirf", "erstelle"]),
    ]
    text_low = text.lower()
    for num, label, keywords in levels:
        if any(k in text_low for k in keywords):
            return {"level": num, "label": label}
    return {"level": 2, "label": "Verstehen"}  # Default
