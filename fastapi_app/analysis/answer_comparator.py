# fastapi_app/analysis/answer_comparator.py
import os, re, json, numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
from analysis.readability_module import analyze_german_readability
from mistral import MistralWrapper

class AnswerComparator:
    def __init__(self, model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", base_dir="analysis"):
        self.model = SentenceTransformer(model_name)
        self.base_dir = Path(base_dir)
        self.wrapper = MistralWrapper()

    # ------------------------------------------------------------
    def quick_compare(self, student_answer: str, model_solution: str) -> float:
        if not student_answer.strip() or not model_solution.strip():
            return 0.0
        emb = self.model.encode([student_answer, model_solution])
        return round(float(util.cos_sim(emb[0], emb[1]).item()), 4)

    # ------------------------------------------------------------
    def detailed_compare(self, student_text: str, model_text: str):
        try:
            def split_tasks(txt):
                parts = re.split(r"(Aufgabe\s+\d+:)", txt)
                tasks = []
                for i in range(1, len(parts), 2):
                    tid = parts[i].strip()
                    content = parts[i + 1].strip() if i + 1 < len(parts) else ""
                    tasks.append((tid, content))
                return tasks or [("Gesamt", txt.strip())]

            model_tasks = split_tasks(model_text)
            student_tasks = split_tasks(student_text)

            emb_stu = self.model.encode([s[1] for s in student_tasks], convert_to_tensor=True)
            emb_mod = self.model.encode([m[1] for m in model_tasks], convert_to_tensor=True)
            sim_matrix = util.cos_sim(emb_stu, emb_mod).cpu().numpy()
            avg_sim = float(np.mean(sim_matrix)) if sim_matrix.size else 0.0

            out_tasks = []
            for i, (tid, s_text) in enumerate(student_tasks):
                m_text = model_tasks[i][1] if i < len(model_tasks) else ""
                sim_score = float(np.mean(sim_matrix[i])) if i < sim_matrix.shape[0] else avg_sim
                feedback = self._generate_feedback(s_text, m_text)

                try:
                    read_metrics = analyze_german_readability(s_text)
                except Exception as e:
                    read_metrics = {"lesbarkeitsgrad": "-", "satzanzahl": "-", "durchschnittliche_satzlänge": "-"}

                out_tasks.append({
                    "task_id": tid,
                    "similarity": round(sim_score, 4),
                    "model_solution": m_text.strip(),
                    "student_answer": s_text.strip(),
                    "feedback": feedback.strip(),
                    "readability": read_metrics.get("lesbarkeitsgrad", "-"),
                    "satzanzahl": read_metrics.get("satzanzahl", "-"),
                    "satzlänge": read_metrics.get("durchschnittliche_satzlänge", "-")
                })

            # Lesbarkeit beider Texte
            read_sl = analyze_german_readability(student_text)
            read_ml = analyze_german_readability(model_text)

            return {
                "similarity_score": round(avg_sim, 4),
                "readability_metrics": read_sl,
                "readability_metrics_model": read_ml,
                "tasks": out_tasks
            }

        except Exception as e:
            return {
                "similarity_score": 0.0,
                "readability_metrics": {"warn": str(e)},
                "tasks": [{"task_id": "Fehler", "feedback": str(e)}]
            }

    # ------------------------------------------------------------
    def _generate_feedback(self, student: str, model: str) -> str:
        if not student.strip():
            return "❌ Keine Studentenantwort vorhanden."
        prompt = (
            "Du bist ein deutschsprachiger Korrekturassistent. "
            "Vergleiche die Studentenantwort mit der Musterlösung und gib ein Feedback mit Bloom-Taxonomie.\n\n"
            f"MUSTERLÖSUNG:\n{model[:2500]}\n\nSTUDENTENANTWORT:\n{student[:2500]}"
        )
        try:
            res = self.wrapper.send_request(prompt)
            return res.strip() if res else "(Kein Feedback verfügbar)"
        except Exception as e:
            return f"(LLM-Fehler: {e})"
