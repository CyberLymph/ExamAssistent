# fastapi_app/analysis/readability_module.py
import os, json
import textstat
import spacy

# --------------------------------------------------
# Optionales Paket: textdescriptives (für mehr Metriken)
# --------------------------------------------------
try:
    import textdescriptives as td  # noqa: F401
    HAS_TD = True
except Exception:
    HAS_TD = False

# --------------------------------------------------
# SpaCy-Modell laden (deutsch)
# --------------------------------------------------
try:
    nlp = spacy.load("de_core_news_md")
except Exception:
    try:
        nlp = spacy.load("de_core_news_sm")
    except Exception:
        raise RuntimeError("Kein deutsches SpaCy-Modell installiert. Bitte `python -m spacy download de_core_news_sm` ausführen.")

# Pipeline nur erweitern, falls Modul verfügbar
if HAS_TD and "textdescriptives" not in nlp.pipe_names:
    try:
        nlp.add_pipe("textdescriptives/all")
    except Exception:
        HAS_TD = False


# --------------------------------------------------
# Hauptfunktion: Lesbarkeitsanalyse
# --------------------------------------------------
def analyze_german_readability(text: str):
    """
    Führt eine kombinierte Lesbarkeitsanalyse für deutschen Text durch.
    Liefert Kennzahlen zu Wortanzahl, Satzlänge, Flesch, Wiener-Formel, usw.
    """
    if not text or len(text.strip()) < 20:
        return {"error": "Text zu kurz für Analyse."}

    doc = nlp(text)
    metrics = {}

    # Erweiterte Metriken (nur, falls textdescriptives vorhanden)
    if HAS_TD:
        try:
            metrics = doc._.readability or {}
        except Exception:
            metrics = {}

    flesch = textstat.flesch_reading_ease(text)
    wiener = metrics.get("wiener_sachtextformel")
    dew = metrics.get("dew")

    # Bewertung des Schwierigkeitsgrads
    if flesch >= 70:
        grade = "Sehr leicht verständlich"
    elif flesch >= 50:
        grade = "Leicht verständlich"
    elif flesch >= 30:
        grade = "Mittelschwer"
    elif flesch >= 10:
        grade = "Schwierig"
    else:
        grade = "Sehr schwierig"

    # Grundlegende Statistiken
    words = len([t for t in doc if t.is_alpha])
    sents = len(list(doc.sents)) or 1

    return {
        "wortanzahl": words,
        "satzanzahl": sents,
        "durchschnittliche_Satzlänge": round(words / sents, 2),
        "flesch_lesen_leicht": round(float(flesch), 2) if isinstance(flesch, (int, float)) else flesch,
        "wiener_sachtextformel": wiener,
        "dew_index": dew,
        "lesbarkeitsgrad": grade,
        "source": "textdescriptives+textstat" if HAS_TD else "textstat-only",
    }


# --------------------------------------------------
# Klasse für Speicherung und Analyse
# --------------------------------------------------
class ReadabilityAnalyzer:
    """
    Führt Lesbarkeitsanalyse durch und speichert Ergebnisse im Analyse-Verzeichnis.
    """
    def __init__(self, base_dir="analysis"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.nlp = nlp

    def analyze_and_save(self, text: str, chat_id: str, run_id: str):
        outdir = os.path.join(self.base_dir, str(chat_id), str(run_id))
        os.makedirs(outdir, exist_ok=True)

        doc = self.nlp(text)
        basic = analyze_german_readability(text)

        metrics = {
            "flesch_reading_ease": textstat.flesch_reading_ease(text),
            "wiener_sachtextformel": basic.get("wiener_sachtextformel"),
            "dew_index": basic.get("dew_index"),
            "avg_sentence_length": basic.get("durchschnittliche_Satzlänge"),
            "lexicon_count": textstat.lexicon_count(text),
            "sentence_count": textstat.sentence_count(text),
            "unique_tokens": len({t.lemma_ for t in doc if t.is_alpha}),
            "lesbarkeitsgrad": basic.get("lesbarkeitsgrad"),
            "source": basic.get("source"),
        }

        filepath = os.path.join(outdir, "readability.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        return {"readability_json": filepath, "metrics": metrics}
