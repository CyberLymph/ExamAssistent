import os
import json
import textstat
import spacy

class ReadabilityAnalyzer:
    def __init__(self, base_dir="analysis", lang_model="de_core_news_sm"):
        """
        base_dir: Wurzelordner für Ergebnisse
        lang_model: spaCy Modell (z.B. 'de_core_news_sm' oder 'en_core_web_sm')
        """
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.nlp = spacy.load(lang_model)

    def safe_stat(self, func, text):
        """
        Hilfsfunktion: ruft eine Textstat-Metrik auf,
        fängt Fehler (z.B. fehlendes cmudict) ab.
        """
        try:
            return func(text)
        except Exception as e:
            return f"Error: {str(e)}"

    def analyze_and_save(self, text: str, chat_id: str, run_id: str):
        outdir = os.path.join(self.base_dir, str(chat_id), str(run_id))
        os.makedirs(outdir, exist_ok=True)

        # Metriken mit Fehler-Schutz
        metrics = {
            "flesch_reading_ease": self.safe_stat(textstat.flesch_reading_ease, text),
            "flesch_kincaid_grade": self.safe_stat(textstat.flesch_kincaid_grade, text),
            "smog_index": self.safe_stat(textstat.smog_index, text),
            "automated_readability_index": self.safe_stat(textstat.automated_readability_index, text),
            "dale_chall_readability_score": self.safe_stat(textstat.dale_chall_readability_score, text),
            "difficult_words": self.safe_stat(textstat.difficult_words, text),
            "syllable_count": self.safe_stat(textstat.syllable_count, text),
            "lexicon_count": textstat.lexicon_count(text),
            "sentence_count": textstat.sentence_count(text),
        }

        # NLP mit spaCy
        doc = self.nlp(text)
        metrics["avg_sentence_length"] = metrics["lexicon_count"] / max(1, metrics["sentence_count"])
        metrics["unique_tokens"] = len(set([t.lemma_ for t in doc if t.is_alpha]))

        # Speichern als JSON
        filepath = os.path.join(outdir, "readability.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        return {"readability_json": filepath, "metrics": metrics}
