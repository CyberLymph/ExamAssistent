# fastapi_app/analysis/test_modules.py
import os, json
from analysis.readability_module import ReadabilityAnalyzer
from analysis.answer_comparator import AnswerComparator


class TestModuleRunner:
    """
    Führt Lesbarkeitsanalyse + Vergleichsanalyse kombiniert durch.
    Nutzt direkt die übergebenen Texte (z. B. aus PDF-Uploads).
    """

    def __init__(self, base_dir="analysis"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.readability_analyzer = ReadabilityAnalyzer(base_dir)
        self.answer_comparator = AnswerComparator(base_dir=base_dir)

    def run_analysis(self, student_text: str, model_text: str, chat_id: str, run_id: str):
        """
        Führt beide Analysen aus und speichert Ergebnisse strukturiert.
        """
        out_dir = os.path.join(self.base_dir, chat_id, run_id)
        os.makedirs(out_dir, exist_ok=True)

        # 1️⃣ Lesbarkeitsanalyse
        readability_result = self.readability_analyzer.analyze_and_save(student_text, chat_id, run_id)

        # 2️⃣ Semantischer Vergleich
        sim_result = self.answer_comparator.detailed_compare(student_text, model_text)

        # 3️⃣ Zusammenfassung kombinieren
        summary = {
            "similarity_score": sim_result["similarity_score"],
            "readability_metrics": readability_result["metrics"],
            "tasks": sim_result.get("tasks", []),
            "readability_file": readability_result["readability_json"],
            "test_module": sim_result.get("test_module", "Analyse erfolgreich."),
        }

        summary_path = os.path.join(out_dir, "summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        return summary
