# fastapi_app/analysis/answer_comparator.py
import os
import json
import numpy as np
import re
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
from analysis.readability_module import analyze_german_readability
from mistral import MistralWrapper


class AnswerComparator:
    """
    Vergleicht Studenten-Antworten mit Musterlösungen (deutschsprachig).
    Unterstützt schnelle (Quick) und detaillierte (LLM) Analysen,
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
    def detailed_compare(self, student_answer: str, model_solution: str):
        """Führt eine vollumfängliche Analyse und Rückgabe aller Details durch."""
        run_id = "detailed_" + self._make_id()
        outdir = self.base_dir / "runs" / run_id
        outdir.mkdir(parents=True, exist_ok=True)

        # === 1. Aufgaben segmentieren ===
        student_tasks = self._split_into_tasks(student_answer)
        model_tasks = self._split_into_tasks(model_solution)

        if not student_tasks:
            student_tasks = [student_answer]
        if not model_tasks:
            model_tasks = [model_solution]

        # === 2. Embedding-Matrix berechnen ===
        emb_student = self.model.encode(student_tasks, convert_to_tensor=True)
        emb_model = self.model.encode(model_tasks, convert_to_tensor=True)
        sim_matrix = util.cos_sim(emb_student, emb_model).cpu().numpy()
        avg_score = float(np.mean(sim_matrix)) if sim_matrix.size else 0.0

        # === 3. Detaillierte Rückmeldung pro Aufgabe ===
        tasks_output = []
        for i, s_text in enumerate(student_tasks):
            ref = model_tasks[i] if i < len(model_tasks) else ""
            feedback = self._generate_feedback(s_text, ref)
            score = float(np.mean(sim_matrix[i])) if i < sim_matrix.shape[0] else avg_score
            tasks_output.append({
                "task_id": f"A{i+1}",
                "student_answer": s_text.strip(),
                "feedback": feedback.strip(),
                "similarity": round(score, 4),
            })

        # === 4. Lesbarkeitsanalyse ===
        try:
            readability = analyze_german_readability(student_answer)
        except Exception:
            readability = {"warn": "Lesbarkeitsanalyse nicht verfügbar"}

        # === 5. Speichern ===
        sim_file = outdir / "similarity.json"
        with sim_file.open("w", encoding="utf-8") as f:
            json.dump({
                "similarity_score": avg_score,
                "tasks": tasks_output,
                "matrix": sim_matrix.tolist(),
            }, f, indent=2, ensure_ascii=False)

        np.save(outdir / "embeddings.npy", sim_matrix)

        # === 6. Rückgabe ===
        return {
            "similarity_score": round(avg_score, 4),
            "tasks": tasks_output,
            "readability": readability,
            "test_module": "Detaillierte Analyse inkl. Bloom-Taxonomie erfolgreich durchgeführt.",
        }

    # ================================================================
    # HELFER: LLM-Feedback inkl. Bloom-Taxonomie
    # ================================================================
    def _generate_feedback(self, student: str, model: str) -> str:
        """LLM-Aufruf mit pädagogischer Bloom-Taxonomie-Analyse und Feedback."""
        if not student.strip():
            return "❌ Keine Studentenantwort gefunden."

        prompt = (
            "Du bist ein deutschsprachiger Korrekturassistent für pädagogische Analysen.\n"
            "Vergleiche die folgende Studentenantwort mit der Musterlösung und gib eine umfassende Bewertung:\n\n"
            "1️⃣ **Inhaltliches Feedback:** Erkläre präzise, was korrekt, teilweise korrekt oder fehlerhaft ist.\n"
            "2️⃣ **Bloom-Taxonomie:** Ordne die Aufgabe nach der kognitiven Stufe (Erinnern, Verstehen, Anwenden, Analysieren, Bewerten, Erschaffen) ein "
            "und begründe deine Einschätzung didaktisch.\n"
            "3️⃣ **Lesbarkeitsbewertung:** Kommentiere die sprachliche Komplexität und Verständlichkeit der Studentenantwort.\n\n"
            "Antwortformat:\n"
            "=== FEEDBACK ===\n"
            "Hier dein Feedback in Absätzen.\n\n"
            "=== BLOOM-TAXONOMIE ===\n"
            "Kognitive Stufe: [eine der 6 Stufen]\n"
            "Begründung: [kurze didaktische Begründung]\n\n"
            "=== LESBARKEITSBEURTEILUNG ===\n"
            "Kommentar zur sprachlichen Verständlichkeit.\n\n"
            f"---\nMUSTERLÖSUNG:\n{model[:3000]}\n\n"
            f"---\nSTUDENTENANTWORT:\n{student[:3000]}"
        )

        try:
            result = self.wrapper.send_request(prompt)
            return result.strip() if result else "(kein Feedback verfügbar)"
        except Exception as e:
            return f"(Fehler beim LLM-Aufruf: {e})"

    # ================================================================
    # HELFER: Textsegmentierung in Aufgaben
    # ================================================================
    def _split_into_tasks(self, text: str):
        """Teilt Text anhand von 'Aufgabe', 'Frage' oder 'A1:' etc. in Segmente."""
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
