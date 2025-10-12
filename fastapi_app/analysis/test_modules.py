# ============================================================
# fastapi_app/analysis/test_modules.py
# ============================================================
import os
import json
from analysis.readability_module import ReadabilityAnalyzer
from analysis.answer_comparator import AnswerComparator


class TestModuleRunner:
    """
    Kombinierter Modul-Runner für Lesbarkeitsanalyse und semantischen Vergleich.
    Nutzt übergebene Texte (z. B. aus hochgeladenen PDFs) und speichert strukturierte
    Analyseergebnisse inklusive Aufgabenvergleich, Feedback und Gesamtbewertung.
    """

    def __init__(self, base_dir: str = "analysis"):
        """
        Initialisiert den Runner mit Basisverzeichnis und erforderlichen Modulen.
        """
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.readability_analyzer = ReadabilityAnalyzer(base_dir)
        self.answer_comparator = AnswerComparator(base_dir=base_dir)

    # ============================================================
    # Hauptanalyse
    # ============================================================
    def run_analysis(self, student_text: str, model_text: str, chat_id: str, run_id: str):
        """
        Führt Lesbarkeitsanalyse und Vergleichsanalyse aus und speichert die Ergebnisse.
        Gibt ein vollständiges Summary-Dictionary zurück.
        """
        try:
            # --- Ausgabeordner vorbereiten ---
            out_dir = os.path.join(self.base_dir, chat_id, run_id)
            os.makedirs(out_dir, exist_ok=True)

            # --- 1️⃣ Lesbarkeitsanalyse durchführen ---
            readability_result = self.readability_analyzer.analyze_and_save(student_text, chat_id, run_id)

            # --- 2️⃣ Vergleichsanalyse (Musterlösung vs. Studentenlösung) ---
            sim_result = self.answer_comparator.detailed_compare(student_text, model_text)

            # --- 3️⃣ Kombinierte Zusammenfassung ---
            summary = {
                "similarity_score": sim_result.get("similarity_score", 0.0),
                "readability_metrics": readability_result.get("metrics", {}),
                "tasks": sim_result.get("tasks", []),
                "readability_file": readability_result.get("readability_json", ""),
                "overall_feedback": self._build_overall_feedback(sim_result),
            }

            # --- 4️⃣ Ergebnisse speichern ---
            summary_path = os.path.join(out_dir, "summary.json")
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            return summary

        except Exception as e:
            # Fallback bei Analysefehlern
            error_summary = {
                "similarity_score": 0.0,
                "readability_metrics": {"warn": "Fehler in der Analyse"},
                "tasks": [],
                "overall_feedback": f"Analysefehler: {e}",
            }
            return error_summary

    # ============================================================
    # Hilfsfunktion: Gesamtfazit erzeugen
    # ============================================================
    def _build_overall_feedback(self, sim_result):
        """
        Erzeugt eine Gesamtbewertung basierend auf allen Aufgabenähnlichkeiten.
        Berücksichtigt durchschnittliche semantische Übereinstimmung und gibt
        eine qualitative Einschätzung (hoch/mittel/niedrig) zurück.
        """
        try:
            tasks = sim_result.get("tasks", [])
            if not tasks:
                return "Keine Aufgabenanalyse verfügbar."

            avg_sim = sum(t.get("similarity", 0) for t in tasks) / len(tasks)
            level = (
                "hoch" if avg_sim > 0.8 else
                "mittel" if avg_sim > 0.5 else
                "niedrig"
            )

            return f"Durchschnittliche Ähnlichkeit: {avg_sim * 100:.1f}% → Leistungsniveau: {level.capitalize()}."

        except Exception:
            return "Gesamtfeedback konnte nicht erstellt werden."
