from readability_module import ReadabilityAnalyzer
from answer_comparator import AnswerComparator


# IDs für Analyse
chat_id = "chat001"
run_id = "run001"

# Texte laden
with open("response.txt", "r", encoding="utf-8") as f:
    student_text = f.read()

with open("extract.txt", "r", encoding="utf-8") as f:
    solution_text = f.read()

# --- 1. Lesbarkeitsanalyse ---
ra = ReadabilityAnalyzer()
readability_result = ra.analyze_and_save(student_text, chat_id, run_id)
print("Readability gespeichert in:", readability_result["readability_json"])
print("Metriken:", readability_result["metrics"])

# --- 2. Similarity Analyse ---
comp = AnswerComparator()
sim_result = comp.analyze_and_save(student_text, solution_text, chat_id, run_id)
print("Similarity Score:", sim_result["similarity_score"])
print("Similarity gespeichert in:", sim_result["similarity_json"])
