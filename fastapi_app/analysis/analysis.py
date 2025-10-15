# fastapi_app/analysis/analysis.py
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
    (1, "Erinnern", [
        "definieren", "vervielfältigen", "auflisten", "auswendig lernen", 
        "wiederholen", "angeben", "nennen", "aufzählen", "remember"
    ]),
    (2, "Verstehen", [
        "klassifizieren", "beschreiben", "diskutieren", "erklären", 
        "identifizieren", "lokalisieren", "erkennen", "berichten", 
        "auswählen", "übersetzen", "erläutern", "interpretieren", "understand"
    ]),
    (3, "Anwenden", [
        "ausführen", "umsetzen", "lösen", "verwenden", "demonstrieren", 
        "interpretieren", "operieren", "planen", "skizzieren", 
        "berechnen", "nutzen", "anwenden", "apply"
    ]),
    (4, "Analysieren", [
        "differenzieren", "organisieren", "in beziehung setzen", "vergleichen", 
        "kontrastieren", "unterscheiden", "untersuchen", "experimentieren", 
        "fragen", "testen", "analysieren", "analyze"
    ]),
    (5, "Bewerten", [
        "einschätzen", "argumentieren", "verteidigen", "beurteilen", 
        "auswählen", "unterstützen", "bewerten", "kritisieren", "abwägen", 
        "diskutieren", "evaluate"
    ]),
    (6, "Kreieren", [
        "entwerfen", "zusammenstellen", "konstruieren", "mutmaßen", 
        "entwickeln", "formulieren", "verfassen", "untersuchen", 
        "create", "erschaffen"
    ])
]
    text_low = text.lower()
    for num, label, keywords in levels:
        if any(k in text_low for k in keywords):
            return {"level": num, "label": label}
    return {"level": 2, "label": "Verstehen"}  # Default
