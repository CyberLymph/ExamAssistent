import os
import json
import textstat
import spacy

class ReadabilityAnalyzer:
    def __init__(self, base_dir="analysis"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.nlp = spacy.load("en_core_web_sm")  # oder "de_core_news_sm" für Deutsch

    def analyze_and_save(self, text: str, chat_id: str, run_id: str):
        outdir = os.path.join(self.base_dir, str(chat_id), str(run_id))
        os.makedirs(outdir, exist_ok=True)

        # Metriken mit textstat
        metrics = {
            "flesch_reading_ease": textstat.flesch_reading_ease(text),
            "flesch_kincaid_grade": textstat.flesch_kincaid_grade(text),
            "smog_index": textstat.smog_index(text),
            "automated_readability_index": textstat.automated_readability_index(text),
            "dale_chall_readability_score": textstat.dale_chall_readability_score(text),
            "difficult_words": textstat.difficult_words(text),
            "syllable_count": textstat.syllable_count(text),
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
