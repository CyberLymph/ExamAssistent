# fastapi_app/analysis/answer_comparator.py
import os
import json
import numpy as np
import re
import difflib
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
from analysis.readability_module import analyze_german_readability
from mistral import MistralWrapper


class AnswerComparator:
    """
    Vergleicht Studenten-Antworten mit Musterlösungen (deutschsprachig).
    Unterstützt schnelle (Quick) und detaillierte (LLM-basierte) Analysen,
    inkl. Bloom-Taxonomie, Lesbarkeitsbewertung und Feedback.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        base_dir: str = "analysis"
    ):
        self.model = SentenceTransformer(model_name)
        self.base_dir = Path(base_dir)
        self.wrapper = MistralWrapper()

    # ================================================================
    # QUICK: Nur Ähnlichkeitswert (ohne tiefe Analyse)
    # ================================================================
    def quick_compare(self, student_answer: str, model_solution: str) -> float:
        """Berechnet semantische Ähnlichkeit zwischen zwei Texten."""
        if not student_answer.strip() or not model_solution.strip():
            return 0.0
        embeddings = self.model.encode([student_answer, model_solution])
        score = float(util.cos_sim(embeddings[0], embeddings[1]).item())
        return round(score, 4)

    # ================================================================
    # DETAILED: Vollständige Analyse mit LLM-Feedback
    # ================================================================
    def detailed_compare(self, student_text: str, model_text: str):
        """
        Liefert strukturierte Analyse mit Lesbarkeit, Feedback und Ähnlichkeitswerten.
        Garantiert Rückgabe eines gültigen JSON-Objekts.
        """
        try:
            # --- Text in Aufgaben zerlegen ---
            def split_tasks(txt):
                parts = re.split(r"(Aufgabe\s+\d+:)", txt)
                tasks = []
                for i in range(1, len(parts), 2):
                    t_id = parts[i].strip()
                    content = parts[i + 1].strip() if i + 1 < len(parts) else ""
                    tasks.append((t_id, content))
                return tasks or [("Gesamt", txt.strip())]

            model_tasks = split_tasks(model_text)
            student_tasks = split_tasks(student_text)

            # --- Ähnlichkeitsmatrix berechnen ---
            emb_student = self.model.encode([s[1] for s in student_tasks], convert_to_tensor=True)
            emb_model = self.model.encode([m[1] for m in model_tasks], convert_to_tensor=True)
            sim_matrix = util.cos_sim(emb_student, emb_model).cpu().numpy()
            avg_sim = float(np.mean(sim_matrix)) if sim_matrix.size else 0.0

            # --- Aufgabenweise Analyse ---
            out_tasks = []
            for i, (tid, s_text) in enumerate(student_tasks):
                m_text = model_tasks[i][1] if i < len(model_tasks) else ""
                sim_score = float(np.mean(sim_matrix[i])) if i < sim_matrix.shape[0] else avg_sim
                feedback = self._generate_feedback(s_text, m_text)
                out_tasks.append({
                    "task_id": tid,
                    "similarity": round(sim_score, 4),
                    "model_solution": m_text.strip(),
                    "student_answer": s_text.strip(),
                    "feedback": feedback.strip()
                })

            # --- Lesbarkeitsanalyse ---
            try:
                readability = analyze_german_readability(student_text)
            except Exception as e:
                readability = {"warn": f"Lesbarkeitsanalyse fehlgeschlagen: {e}"}

            # --- Strukturierte Zusammenfassung ---
            summary = {
                "similarity_score": round(avg_sim, 4),
                "readability_metrics": readability,
                "tasks": out_tasks
            }
            return summary

        except Exception as e:
            # --- Fallback bei Fehlern ---
            return {
                "similarity_score": 0.0,
                "readability_metrics": {"warn": f"Analysefehler: {e}"},
                "tasks": [
                    {
                        "task_id": "A1",
                        "student_answer": student_text[:200],
                        "model_solution": model_text[:200],
                        "similarity": 0.0,
                        "feedback": f"(Analysefehler: {e})"
                    }
                ]
            }

    # ================================================================
    # HELFER: LLM-Feedback mit Bloom-Taxonomie
    # ================================================================
    def _generate_feedback(self, student: str, model: str) -> str:
        """LLM-Aufruf mit pädagogischer Analyse (Bloom-Taxonomie + Feedback)."""
        if not student.strip():
            return "❌ Keine Studentenantwort vorhanden."

        prompt = (
            "Du bist ein deutschsprachiger Korrekturassistent für pädagogische Analysen.\n"
            "Vergleiche die folgende Studentenantwort mit der Musterlösung und gib ein strukturiertes Feedback:\n\n"
            "1️⃣ Inhaltliches Feedback: Was ist korrekt, teilweise richtig oder falsch?\n"
            "2️⃣ Bloom-Taxonomie: Kognitive Stufe (Erinnern, Verstehen, Anwenden, Analysieren, Bewerten, Erschaffen).\n"
            "3️⃣ Lesbarkeitsbewertung: Kommentiere die sprachliche Verständlichkeit.\n\n"
            "Antwortformat:\n"
            "=== FEEDBACK ===\nTextliche Rückmeldung.\n\n"
            "=== BLOOM-TAXONOMIE ===\nKognitive Stufe + Begründung.\n\n"
            "=== LESBARKEITSBEURTEILUNG ===\nKommentar zur sprachlichen Komplexität.\n\n"
            f"---\nMUSTERLÖSUNG:\n{model[:3000]}\n\n"
            f"---\nSTUDENTENANTWORT:\n{student[:3000]}"
        )

        try:
            result = self.wrapper.send_request(prompt)
            return result.strip() if result else "(kein Feedback verfügbar)"
        except Exception as e:
            return f"(Fehler beim LLM-Aufruf: {e})"

    # ================================================================
    # HELFER: Textsegmentierung
    # ================================================================
    def _split_into_tasks(self, text: str):
        """Segmentiert Text anhand typischer Muster."""
        if not text.strip():
            return []
        parts = re.split(r"(?:Aufgabe|Frage|A)\s*\d+\s*[:\-–]", text, flags=re.IGNORECASE)
        parts = [p.strip() for p in parts if len(p.strip()) > 30]
        return parts or [text.strip()]

    # ================================================================
    # HELFER: ID-Erzeugung
    # ================================================================
    def _make_id(self) -> str:
        import uuid, datetime
        return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S_") + uuid.uuid4().hex[:8]
