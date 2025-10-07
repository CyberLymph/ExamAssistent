# analysis/analyse.py
from typing import Dict, Any
from analysis.readability_module import ReadabilityAnalyzer
from analysis.answer_comparator import AnswerComparator

def run_detailed_analysis(student_text: str, model_text: str, chat_id: str, run_id: str, base_dir: str = "analysis") -> Dict[str, Any]:
    """
    Führt die kombinierte Detailanalyse aus (Semantik + Lesbarkeit) und liefert ein Summary-Objekt,
    das pro Aufgabe sowohl SL (Student) als auch ML (Musterlösung) enthält.
    """
    readability = ReadabilityAnalyzer(base_dir=base_dir).analyze_and_save(student_text, chat_id, run_id)
    comp = AnswerComparator(base_dir=base_dir)
    detailed = comp.detailed_compare(student_text, model_text)

    # Ensure tasks carry model solution (falls alte comparator-Version ohne 'model_solution' im Einsatz)
    tasks = []
    for t in detailed.get("tasks", []):
        tasks.append({
            "task_id": t.get("task_id"),
            "student_answer": t.get("student_answer", ""),
            "model_solution": t.get("model_solution", ""),  # kann leer sein bei älteren Versionen
            "feedback": t.get("feedback", ""),
            "similarity": t.get("similarity", 0.0),
        })

    return {
        "similarity_score": detailed.get("similarity_score", 0.0),
        "readability_metrics": readability["metrics"],
        "tasks": tasks,
        "readability_file": readability["readability_json"],
        "test_module": "Detaillierte Analyse erfolgreich (analyse.py).",
    }
